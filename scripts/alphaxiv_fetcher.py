"""Fetch top HOT papers from alphaXiv rankings."""
import re
import time
import requests
import feedparser

ARXIV_API = 'http://export.arxiv.org/api/query'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/122.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def _fetch_arxiv_details(paper_ids):
    """Fetch full paper metadata from arXiv API given a list of IDs."""
    if not paper_ids:
        return []
    id_list = ','.join(paper_ids)
    try:
        resp = requests.get(
            ARXIV_API,
            params={'id_list': id_list, 'max_results': len(paper_ids)},
            timeout=30,
        )
        feed = feedparser.parse(resp.text)
        papers = []
        for entry in feed.entries:
            paper_id = entry.id.split('abs/')[-1]
            code_url = None
            for link in getattr(entry, 'links', []):
                href = getattr(link, 'href', '')
                if 'github.com' in href:
                    code_url = href
                    break
            papers.append({
                'id': paper_id,
                'title': entry.title.replace('\n', ' ').strip(),
                'authors': [a.name for a in entry.authors[:6]],
                'abstract': entry.summary.replace('\n', ' ').strip(),
                'arxiv_url': f'https://arxiv.org/abs/{paper_id}',
                'pdf_url': f'https://arxiv.org/pdf/{paper_id}',
                'published': entry.get('published', ''),
                'categories': [t.term for t in entry.tags],
                'code_url': code_url,
            })
        return papers
    except Exception as e:
        print(f'  arXiv detail fetch error: {e}')
        return []


def fetch_alphaxiv_hot(top_n=8):
    """
    Scrape alphaXiv to get the top hot/trending arXiv paper IDs,
    then fetch full metadata from arXiv API.
    Returns list of paper dicts (may be empty if scraping fails).
    top_n=8 to allow deduplication buffer — caller takes first 4 unsent.
    """
    # arXiv IDs in URLs: /abs/2501.12345 or /abs/2501.12345v2
    url_id_pattern = re.compile(r'/abs/(\d{4}\.\d{4,5}(?:v\d+)?)')
    # Standalone arXiv IDs in page text
    raw_id_pattern = re.compile(r'\b(2[0-9]{3}\.\d{4,5})(?:v\d+)?\b')

    seen = set()
    candidate_ids = []

    for url in [
        'https://alphaxiv.org/',
        'https://alphaxiv.org/explore',
        'https://alphaxiv.org/trending',
    ]:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f'  alphaXiv {url} → HTTP {r.status_code}')
                continue

            html = r.text
            # Prefer URL-embedded IDs (more reliable than free text)
            ids = url_id_pattern.findall(html)
            if not ids:
                ids = raw_id_pattern.findall(html)

            for raw_id in ids:
                base = re.sub(r'v\d+$', '', raw_id)
                if base not in seen:
                    seen.add(base)
                    candidate_ids.append(base)

            print(f'  alphaXiv {url} → {len(candidate_ids)} IDs so far')
            if len(candidate_ids) >= top_n:
                break
            time.sleep(1)

        except Exception as e:
            print(f'  alphaXiv scrape error ({url}): {e}')

    if not candidate_ids:
        print('  ⚠️  alphaXiv returned 0 IDs — caller should use arXiv fallback')
        return []

    top_ids = candidate_ids[:top_n]
    print(f'  alphaXiv HOT candidate IDs: {top_ids}')
    papers = _fetch_arxiv_details(top_ids)
    print(f'  Fetched {len(papers)} papers from arXiv')
    return papers
