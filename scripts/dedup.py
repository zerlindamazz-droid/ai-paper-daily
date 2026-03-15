"""Track and deduplicate sent papers across daily runs."""
import json
from pathlib import Path

SENT_FILE = Path('docs/sent_papers.json')


def load_sent_ids():
    """Load set of previously sent paper IDs."""
    if SENT_FILE.exists():
        data = json.loads(SENT_FILE.read_text(encoding='utf-8'))
        return set(data.get('sent', []))
    return set()


def save_sent_ids(ids: set):
    """Persist sent paper IDs. Keeps last 90 days worth (max 2000 entries)."""
    existing = load_sent_ids()
    merged = list(existing | ids)
    # Trim to last 2000 to avoid unbounded growth
    merged = merged[-2000:]
    SENT_FILE.write_text(
        json.dumps({'sent': merged}, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f'  Saved {len(merged)} total sent IDs ({len(ids)} new)')


def filter_unsent(papers, sent_ids):
    """Remove papers that have already been sent."""
    unsent = [p for p in papers if p['id'] not in sent_ids]
    skipped = len(papers) - len(unsent)
    if skipped:
        print(f'  Filtered out {skipped} already-sent papers, {len(unsent)} remain')
    return unsent
