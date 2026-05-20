"""Enrich papers with quality signals: GitHub stars + paperswithcode lookup.

These signals let the daily-digest selector bias toward well-known, popular
work (high GitHub stars, repo present on Papers With Code) rather than just
the newest arXiv submissions.
"""
import os
import re
import time
import requests

GITHUB_API = 'https://api.github.com'
PWC_API = 'https://paperswithcode.com/api/v1/papers/'

# In-process caches so the same repo / arxiv ID isn't fetched twice per run.
_STAR_CACHE: dict[str, int | None] = {}
_PWC_CACHE: dict[str, str | None] = {}

_GITHUB_URL_RE = re.compile(
    r'https?://github\.com/([A-Za-z0-9_.\-]+)/([A-Za-z0-9_.\-]+)',
    re.IGNORECASE,
)


def _github_headers() -> dict:
    headers = {'Accept': 'application/vnd.github+json'}
    token = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _normalize_repo(url: str) -> str | None:
    """Extract 'owner/repo' from any github.com URL. Strips .git, /tree/..., etc."""
    if not url:
        return None
    m = _GITHUB_URL_RE.search(url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = re.sub(r'\.git$', '', repo)
    # Skip obvious non-repo paths (e.g. github.com/orgs, github.com/about)
    if owner.lower() in {'orgs', 'about', 'features', 'topics', 'sponsors', 'collections'}:
        return None
    return f'{owner}/{repo}'


def extract_github_url(paper: dict) -> str | None:
    """Find a GitHub repo URL for a paper.

    Checks (in order): the arXiv feed link (paper['code_url']) and the
    abstract text. Returns the canonical 'https://github.com/owner/repo' form.
    """
    candidates = []
    if paper.get('code_url'):
        candidates.append(paper['code_url'])
    abstract = paper.get('abstract') or ''
    candidates.extend(m.group(0) for m in _GITHUB_URL_RE.finditer(abstract))

    for url in candidates:
        repo = _normalize_repo(url)
        if repo:
            return f'https://github.com/{repo}'
    return None


def lookup_paperswithcode(arxiv_id: str) -> str | None:
    """Ask Papers With Code for the official repository, if any.

    Returns a github.com URL or None. Result is cached per-run.
    """
    if arxiv_id in _PWC_CACHE:
        return _PWC_CACHE[arxiv_id]

    base_id = re.sub(r'v\d+$', '', arxiv_id)
    try:
        resp = requests.get(
            PWC_API,
            params={'arxiv_id': base_id},
            timeout=10,
        )
        if resp.status_code != 200:
            _PWC_CACHE[arxiv_id] = None
            return None
        data = resp.json()
        results = data.get('results') or []
        if not results:
            _PWC_CACHE[arxiv_id] = None
            return None
        paper_pwc_id = results[0].get('id')
        if not paper_pwc_id:
            _PWC_CACHE[arxiv_id] = None
            return None

        repos_resp = requests.get(
            f'{PWC_API}{paper_pwc_id}/repositories/',
            timeout=10,
        )
        if repos_resp.status_code != 200:
            _PWC_CACHE[arxiv_id] = None
            return None
        repos = repos_resp.json().get('results') or []
        # Prefer the official repo, fall back to most-starred.
        official = [r for r in repos if r.get('is_official')]
        chosen = (official or sorted(repos, key=lambda r: r.get('stars') or 0, reverse=True))
        if not chosen:
            _PWC_CACHE[arxiv_id] = None
            return None
        url = chosen[0].get('url')
        repo = _normalize_repo(url or '')
        result = f'https://github.com/{repo}' if repo else None
        _PWC_CACHE[arxiv_id] = result
        return result
    except Exception:
        _PWC_CACHE[arxiv_id] = None
        return None


def get_github_stars(repo_url: str) -> int | None:
    """Fetch stargazers count for a github.com URL. Cached per-run."""
    repo = _normalize_repo(repo_url)
    if not repo:
        return None
    if repo in _STAR_CACHE:
        return _STAR_CACHE[repo]
    try:
        resp = requests.get(
            f'{GITHUB_API}/repos/{repo}',
            headers=_github_headers(),
            timeout=10,
        )
        # 403 with rate-limit body means we're throttled; back off briefly.
        if resp.status_code == 403 and 'rate limit' in resp.text.lower():
            _STAR_CACHE[repo] = None
            return None
        if resp.status_code != 200:
            _STAR_CACHE[repo] = None
            return None
        stars = resp.json().get('stargazers_count')
        _STAR_CACHE[repo] = stars
        return stars
    except Exception:
        _STAR_CACHE[repo] = None
        return None


def _quality_score(stars: int | None, has_code: bool) -> float:
    """Map signals to a 0..10 score used to rank candidates.

    Star count contributes logarithmically (a 100k-star repo doesn't dominate
    a 10k-star repo). Papers with no code at all get a small floor so the
    pool isn't entirely starved of code-less work.
    """
    if stars is None:
        return 1.0 if has_code else 0.0
    if stars <= 0:
        return 1.0 if has_code else 0.0
    import math
    # log10(1)=0, log10(10)=1, log10(100)=2, log10(10000)=4 → cap at 10.
    return min(10.0, 2.0 * math.log10(stars + 1))


def enrich_papers(
    papers: list[dict],
    max_lookups: int = 80,
    use_paperswithcode: bool = True,
) -> list[dict]:
    """Add `code_url`, `stars`, `quality_score` to each paper (in place).

    Only the first `max_lookups` papers (already roughly ranked by recency)
    hit the network; the rest get score 0 so they sort last but still appear
    if the pool is small.
    """
    print(f'  Enriching quality signals (up to {max_lookups} lookups)...')
    enriched_with_repo = 0
    for i, paper in enumerate(papers):
        if i >= max_lookups:
            paper.setdefault('stars', None)
            paper.setdefault('quality_score', 0.0)
            continue

        repo_url = extract_github_url(paper)
        if not repo_url and use_paperswithcode:
            repo_url = lookup_paperswithcode(paper['id'])
            # Be polite to PWC's API.
            time.sleep(0.3)
        if repo_url:
            paper['code_url'] = repo_url

        stars = get_github_stars(repo_url) if repo_url else None
        paper['stars'] = stars
        paper['quality_score'] = _quality_score(stars, has_code=bool(repo_url))
        if repo_url:
            enriched_with_repo += 1

    with_stars = sum(1 for p in papers if (p.get('stars') or 0) > 0)
    top = sorted(papers, key=lambda p: p.get('stars') or 0, reverse=True)[:5]
    print(f'  Found code repos for {enriched_with_repo}/{min(max_lookups, len(papers))} papers '
          f'({with_stars} with stars).')
    if top and (top[0].get('stars') or 0) > 0:
        print('  Top-starred candidates:')
        for p in top:
            if (p.get('stars') or 0) > 0:
                print(f'    ★{p["stars"]:>6}  {p["id"]}  {p["title"][:70]}')
    return papers
