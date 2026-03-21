"""
AI Paper Daily - Main Orchestrator
Runs daily via GitHub Actions to fetch, analyze, and render AI training papers.
Featured papers: alphaXiv HOT top 4 (with arXiv fallback).
Brief papers: Claude selects 5 ML/RL/Robotics focused from arXiv pool.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add scripts/ to path when running from repo root
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_papers
from alphaxiv_fetcher import fetch_alphaxiv_hot
from summarizer import select_and_rank, select_brief, analyze_featured, analyze_brief_batch
from extractor import extract_figures
from renderer import save_report
from pdf_generator import generate_pdf
from send_email import send_email
from dedup import load_sent_ids, save_sent_ids, filter_unsent


def get_la_date():
    """Get current date in Los Angeles time."""
    la_tz = timezone(timedelta(hours=-7))  # PDT (UTC-7)
    now = datetime.now(la_tz)
    return now.strftime('%Y-%m-%d')


def _empty_analysis(paper):
    return {
        'importance_score': 7,
        'topic_tags_en': [], 'topic_tags_zh': [],
        'title_zh': paper['title'],
        'one_liner_zh': '暂无中文摘要', 'one_liner_en': 'Analysis unavailable',
        'problem_zh': '', 'problem_en': '',
        'highlights_zh': '', 'highlights_en': '',
        'method_zh': '', 'method_en': '',
        'experiment_zh': '', 'experiment_en': '',
        'results_zh': '', 'results_en': '',
        'conclusion_zh': '', 'conclusion_en': '',
        'why_it_matters_zh': '', 'why_it_matters_en': '',
        'key_formulas': [],
    }


def main():
    date_str = get_la_date()
    print(f'\n{"="*60}')
    print(f'AI Paper Daily - {date_str}')
    print(f'{"="*60}\n')

    # ── Step 1: Load dedup history ─────────────────────────────
    sent_ids = load_sent_ids()
    print(f'📋 {len(sent_ids)} papers previously sent (will deduplicate)\n')

    # ── Step 2: Fetch alphaXiv HOT for featured papers ─────────
    print('🔥 Fetching alphaXiv HOT papers...')
    alphaxiv_papers = fetch_alphaxiv_hot(top_n=10)  # fetch 10 for dedup buffer
    alphaxiv_papers = filter_unsent(alphaxiv_papers, sent_ids)
    featured_papers_raw = alphaxiv_papers[:4]        # take top 4 unsent
    print(f'   alphaXiv: {len(featured_papers_raw)} unsent featured papers\n')

    # ── Step 3: Fetch arXiv pool for brief + featured fallback ─
    print('📥 Fetching papers from arXiv (last 30 days)...')
    arxiv_papers = fetch_papers(days=30, max_per_cat=40)
    featured_ids = {p['id'] for p in featured_papers_raw}
    arxiv_papers = filter_unsent(arxiv_papers, sent_ids | featured_ids)
    print(f'   arXiv: {len(arxiv_papers)} unsent candidates\n')

    # ── Step 4: Fill featured if alphaXiv gave < 4 papers ─────
    if len(featured_papers_raw) < 4:
        needed = 4 - len(featured_papers_raw)
        print(f'⚠️  alphaXiv only provided {len(featured_papers_raw)} papers. '
              f'Filling {needed} from arXiv via Claude...')
        candidates_for_fill = arxiv_papers[:40]
        try:
            ranking = select_and_rank(candidates_for_fill)
            for meta in ranking['featured'][:needed]:
                idx = meta['paper_index'] - 1
                if idx < len(candidates_for_fill):
                    p = candidates_for_fill[idx].copy()
                    p['importance_score'] = meta.get('importance_score', 8)
                    p['topic_tags_en'] = meta.get('topic_tags_en', [])
                    p['topic_tags_zh'] = meta.get('topic_tags_zh', [])
                    featured_papers_raw.append(p)
                    featured_ids.add(p['id'])
        except Exception as e:
            print(f'   Fallback ranking failed: {e}')

        # Re-filter arXiv pool after filling
        arxiv_papers = [p for p in arxiv_papers if p['id'] not in featured_ids]

    if not featured_papers_raw:
        print('⚠️  No featured papers found. Exiting.')
        sys.exit(1)

    # ── Step 5: Select 5 brief papers (ML/RL/Robotics focus) ──
    print('🧠 Selecting 5 brief papers (ML / RL / Robotics priority)...')
    brief_candidates = arxiv_papers[:60]
    try:
        brief_selection = select_brief(brief_candidates)
        brief_papers_raw = []
        for meta in brief_selection:
            idx = meta['paper_index'] - 1
            if idx < len(brief_candidates):
                p = brief_candidates[idx].copy()
                p['topic_tags_en'] = meta.get('topic_tags_en', [])
                p['topic_tags_zh'] = meta.get('topic_tags_zh', [])
                brief_papers_raw.append(p)
    except Exception as e:
        print(f'   Brief selection failed: {e}. Using first 5 candidates.')
        brief_papers_raw = []
        for p in brief_candidates[:5]:
            pc = p.copy()
            pc['topic_tags_en'] = []
            pc['topic_tags_zh'] = []
            brief_papers_raw.append(pc)

    print(f'   Selected {len(brief_papers_raw)} brief papers\n')

    # ── Step 6: Deep analysis for featured papers ──────────────
    print(f'📝 Deep bilingual analysis for {len(featured_papers_raw)} featured papers...')
    featured_results = []
    for i, paper in enumerate(featured_papers_raw):
        print(f'   [{i+1}/{len(featured_papers_raw)}] {paper["title"][:70]}')
        try:
            analysis = analyze_featured(paper)
            # analyze_featured now returns importance_score and topic_tags —
            # override whatever was set by alphaXiv/select_and_rank
            paper['importance_score'] = analysis.get('importance_score', paper.get('importance_score', 8))
            paper['topic_tags_en'] = analysis.get('topic_tags_en', paper.get('topic_tags_en', []))
            paper['topic_tags_zh'] = analysis.get('topic_tags_zh', paper.get('topic_tags_zh', []))
        except Exception as e:
            print(f'   Analysis failed: {e}')
            analysis = _empty_analysis(paper)
        featured_results.append({'paper': paper, 'analysis': analysis, 'figures': []})

    # ── Step 7: Extract figures from PDFs ─────────────────────
    print('\n🖼️  Extracting figures from PDFs...')
    tmp_dir = Path('tmp_figures')
    for i, result in enumerate(featured_results):
        paper = result['paper']
        print(f'   [{i+1}/{len(featured_results)}] {paper["id"]}')
        figures = extract_figures(
            paper_id=paper['id'],
            pdf_url=paper['pdf_url'],
            output_dir=tmp_dir,
            max_figures=2
        )
        result['figures'] = figures

    # ── Step 8: Brief summaries ────────────────────────────────
    print('\n📋 Generating brief summaries with conclusions...')
    try:
        brief_summaries = analyze_brief_batch(brief_papers_raw)
    except Exception as e:
        print(f'   Brief analysis failed: {e}')
        brief_summaries = [
            {'index': i+1, 'title_zh': p['title'],
             'summary_zh': '', 'summary_en': '',
             'conclusion_zh': '', 'conclusion_en': ''}
            for i, p in enumerate(brief_papers_raw)
        ]

    brief_results = []
    for paper, summary_data in zip(brief_papers_raw, brief_summaries):
        if not isinstance(summary_data, dict):
            summary_data = {'title_zh': paper['title'],
                            'summary_zh': '', 'summary_en': '',
                            'conclusion_zh': '', 'conclusion_en': ''}
        brief_results.append({'paper': paper, 'summary': summary_data})

    # ── Step 9: Render HTML ────────────────────────────────────
    print('\n🎨 Rendering HTML report...')
    try:
        save_report(date_str, featured_results, brief_results, docs_dir='docs')
        print(f'\n✅ Report saved — {len(featured_results)} featured + {len(brief_results)} brief')
    except Exception as e:
        print(f'   Render failed: {e}')
        raise

    # Save sent IDs
    newly_sent = {r['paper']['id'] for r in featured_results + brief_results}
    save_sent_ids(newly_sent)

    # Clean up temp figures
    if tmp_dir.exists():
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f'\n🌐 Live at: https://zerlindamazz-droid.github.io/ai-paper-daily/')

    # ── Step 10: Generate PDF ──────────────────────────────────
    print('\n📄 Generating PDF...')
    pdf_path = None
    try:
        html_path = Path('docs/index.html').resolve()
        pdf_path = Path(f'tmp_{date_str}.pdf')
        generate_pdf(html_path, pdf_path)
    except Exception as e:
        print(f'  PDF generation failed: {e}')

    # ── Step 11: Send email ────────────────────────────────────
    print('\n📧 Sending email...')
    send_email(date_str, featured_results, brief_results, pdf_path=pdf_path)

    if pdf_path and pdf_path.exists():
        pdf_path.unlink()

    print('Done! ✨\n')


if __name__ == '__main__':
    main()
