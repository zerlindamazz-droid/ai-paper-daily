"""Fetch trending papers from HuggingFace daily papers, ranked by upvotes."""
import requests
from datetime import datetime, timezone, timedelta

HF_PAPERS_API = 'https://huggingface.co/api/papers'


def fetch_hf_hot(min_upvotes=5, top_n=12, lookback_days=2):
    """
    Fetch HuggingFace daily papers sorted by community upvotes.

    Looks back `lookback_days` days (skipping today, which has no upvotes yet).
    Returns up to top_n papers with upvotes >= min_upvotes, sorted by upvotes desc.
    Each paper dict matches the standard pipeline format.
    """
    la_tz = timezone(timedelta(hours=-7))
    today = datetime.now(la_tz).date()

    seen: dict = {}  # id -> paper dict

    for days_ago in range(1, lookback_days + 1):
        date = today - timedelta(days=days_ago)
        date_str = date.strftime('%Y-%m-%d')
        try:
            resp = requests.get(HF_PAPERS_API, params={'date': date_str}, timeout=15)
            if resp.status_code != 200:
                print(f'  HF {date_str} → HTTP {resp.status_code}')
                continue

            count = 0
            for p in resp.json():
                pid = p.get('id', '').strip()
                if not pid or pid in seen:
                    continue
                upvotes = p.get('upvotes', 0)
                if upvotes < min_upvotes:
                    continue
                abstract = (p.get('summary') or p.get('ai_summary') or '').replace('\n', ' ').strip()
                seen[pid] = {
                    'id': pid,
                    'title': p.get('title', '').replace('\n', ' ').strip(),
                    'authors': [a.get('name', '') for a in p.get('authors', [])[:6]],
                    'abstract': abstract,
                    'arxiv_url': f'https://arxiv.org/abs/{pid}',
                    'pdf_url': f'https://arxiv.org/pdf/{pid}',
                    'published': p.get('publishedAt', date_str + 'T00:00:00.000Z'),
                    'categories': [],
                    'code_url': p.get('githubRepo') or None,
                    'hf_upvotes': upvotes,
                }
                count += 1
            print(f'  HF {date_str}: {count} papers with ≥{min_upvotes} upvotes')

        except Exception as e:
            print(f'  HF fetch error ({date_str}): {e}')

    sorted_papers = sorted(seen.values(), key=lambda x: x['hf_upvotes'], reverse=True)
    result = sorted_papers[:top_n]
    print(f'  HF total: {len(result)} qualifying papers (top {top_n}, upvotes ≥{min_upvotes})')
    return result
