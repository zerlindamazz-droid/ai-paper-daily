"""Fetch recent AI/ML papers from arXiv."""
import feedparser
import requests
import time

CATEGORIES = ['cs.LG', 'cs.AI', 'cs.CL', 'stat.ML', 'cs.RO']


def fetch_papers(days=30, max_per_cat=40):
    """
    Fetch the most recent papers across AI/ML categories.
    Deduplication against previously-sent papers is handled by dedup.py.
    Returns a deduplicated list sorted by submission date (newest first).
    """
    all_papers = []
    seen_ids = set()

    for cat in CATEGORIES:
        # Use params dict so requests handles URL encoding correctly
        params = {
            'search_query': f'cat:{cat}',
            'start': 0,
            'max_results': max_per_cat,
            'sortBy': 'submittedDate',
            'sortOrder': 'descending',
        }
        try:
            resp = requests.get(
                'http://export.arxiv.org/api/query',
                params=params,
                timeout=30,
            )
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
    print(f'  Total unique candidates: {len(all_papers)} papers')
    return all_papers
