"""Fetch recent AI/ML papers from arXiv (last 30 days)."""
import feedparser
import requests
import time
from datetime import datetime, timezone, timedelta

CATEGORIES = ['cs.LG', 'cs.AI', 'cs.CL', 'stat.ML', 'cs.RO']


def fetch_papers(days=30, max_per_cat=40):
    """
    Fetch papers submitted in the last `days` days across AI/ML categories.
    Returns a deduplicated list sorted by submission date (newest first).
    """
    all_papers = []
    seen_ids = set()

    # Build date range filter for arXiv
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days)).strftime('%Y%m%d%H%M%S')
    end_date = now.strftime('%Y%m%d%H%M%S')
    date_filter = f'submittedDate:[{start_date}+TO+{end_date}]'

    for cat in CATEGORIES:
        url = (
            f'http://export.arxiv.org/api/query'
            f'?search_query=cat:{cat}+AND+{date_filter}'
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

                code_url = None
                for link in getattr(entry, 'links', []):
                    href = getattr(link, 'href', '')
                    if 'github.com' in href:
                        code_url = href
                        break

                all_papers.append({
                    'id': paper_id,
                    'title': entry.title.replace('\n', ' ').strip(),
                    'authors': [a.name for a in entry.authors[:6]],
                    'abstract': entry.summary.replace('\n', ' ').strip(),
                    'arxiv_url': f'https://arxiv.org/abs/{paper_id}',
                    'pdf_url': f'https://arxiv.org/pdf/{paper_id}',
                    'published': entry.published,
                    'categories': [t.term for t in entry.tags],
                    'code_url': code_url,
                })

            print(f'  {cat}: {len(feed.entries)} papers fetched')
            time.sleep(3)

        except Exception as e:
            print(f'  Error fetching {cat}: {e}')

    all_papers.sort(key=lambda x: x['published'], reverse=True)
    print(f'  Total unique: {len(all_papers)} papers from last {days} days')
    return all_papers
