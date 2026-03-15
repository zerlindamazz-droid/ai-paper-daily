"""Fetch recent AI/ML papers from arXiv."""
import feedparser
import requests
import time
from datetime import datetime, timezone, timedelta

# Cover all major AI training directions
CATEGORIES = ['cs.LG', 'cs.AI', 'cs.CL', 'stat.ML', 'cs.RO']

def fetch_papers(max_per_cat=12):
    """Fetch recent papers from arXiv across AI/ML categories."""
    all_papers = []
    seen_ids = set()

    for cat in CATEGORIES:
        url = (
            f'http://export.arxiv.org/api/query'
            f'?search_query=cat:{cat}'
            f'&start=0&max_results={max_per_cat}'
            f'&sortBy=submittedDate&sortOrder=descending'
        )
        try:
            resp = requests.get(url, timeout=30)
            feed = feedparser.parse(resp.text)

            for entry in feed.entries:
                paper_id = entry.id.split('abs/')[-1]
                if paper_id in seen_ids:
                    continue
                seen_ids.add(paper_id)

                # Try to find code link in links
                code_url = None
                for link in getattr(entry, 'links', []):
                    href = getattr(link, 'href', '')
                    if 'github.com' in href or 'code' in href.lower():
                        code_url = href
                        break

                all_papers.append({
                    'id': paper_id,
                    'title': entry.title.replace('\n', ' ').strip(),
                    'authors': [a.name for a in entry.authors[:6]],
                    'abstract': entry.summary.replace('\n', ' ').strip(),
                    'arxiv_url': f'https://arxiv.org/abs/{paper_id}',
                    'pdf_url': f'https://arxiv.org/pdf/{paper_id}',
                    'html_url': f'https://arxiv.org/html/{paper_id}',
                    'published': entry.published,
                    'categories': [t.term for t in entry.tags],
                    'code_url': code_url,
                })

            print(f'  Fetched {len(feed.entries)} papers from {cat}')
            time.sleep(3)  # Respect arXiv rate limits

        except Exception as e:
            print(f'  Error fetching {cat}: {e}')

    # Sort by publication date (most recent first)
    all_papers.sort(key=lambda x: x['published'], reverse=True)
    return all_papers[:40]  # Keep top 40 candidates
