"""
AI Paper Daily - Main Orchestrator
Runs daily via GitHub Actions to fetch, analyze, and render AI training papers.
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add scripts/ to path when running from repo root
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import fetch_papers
from summarizer import select_and_rank, analyze_featured, analyze_brief_batch
from extractor import extract_figures
from renderer import save_report
from pdf_generator import generate_pdf
from send_email import send_email


def get_la_date():
    """Get current date in Los Angeles time."""
    la_tz = timezone(timedelta(hours=-7))  # PDT (UTC-7); GitHub Actions will handle DST via env
    now = datetime.now(la_tz)
    return now.strftime('%Y-%m-%d')


def main():
    date_str = get_la_date()
    print(f'\n{"="*60}')
    print(f'AI Paper Daily - {date_str}')
    print(f'{"="*60}\n')

    # Step 1: Fetch papers
    print('📥 Fetching papers from arXiv...')
    papers = fetch_papers(max_per_cat=12)
    print(f'   Found {len(papers)} candidate papers\n')

    if len(papers) < 5:
        print('⚠️  Too few papers found (weekend/holiday?). Exiting.')
        sys.exit(0)

    # Step 2: Select and rank
    print('🧠 Ranking papers with Claude AI...')
    try:
        ranking = select_and_rank(papers)
    except Exception as e:
        print(f'   Ranking failed: {e}')
        sys.exit(1)

    # Map ranked indices back to papers (1-based)
    featured_indices = [r['paper_index'] - 1 for r in ranking['featured']]
    brief_indices = [r['paper_index'] - 1 for r in ranking['brief']]

    featured_meta = ranking['featured']  # [{rank, paper_index, importance_score, topic_tags_*}]
    brief_meta = ranking['brief']

    print(f'   Selected {len(featured_indices)} featured + {len(brief_indices)} brief papers\n')

    # Attach ranking metadata to papers
    featured_papers_raw = []
    for i, (idx, meta) in enumerate(zip(featured_indices, featured_meta)):
        if idx < len(papers):
            p = papers[idx].copy()
            p['importance_score'] = meta.get('importance_score', 8)
            p['topic_tags_en'] = meta.get('topic_tags_en', [])
            p['topic_tags_zh'] = meta.get('topic_tags_zh', [])
            featured_papers_raw.append(p)

    brief_papers_raw = []
    for idx, meta in zip(brief_indices, brief_meta):
        if idx < len(papers):
            p = papers[idx].copy()
            p['topic_tags_en'] = meta.get('topic_tags_en', [])
            p['topic_tags_zh'] = meta.get('topic_tags_zh', [])
            brief_papers_raw.append(p)

    # Step 3: Deep analysis for featured papers
    print('📝 Generating deep bilingual analysis for featured papers...')
    featured_results = []
    for i, paper in enumerate(featured_papers_raw):
        print(f'   [{i+1}/{len(featured_papers_raw)}] {paper["title"][:70]}...')
        try:
            analysis = analyze_featured(paper)
        except Exception as e:
            print(f'   Analysis failed: {e}')
            analysis = {
                'title_zh': paper['title'],
                'one_liner_zh': '暂无中文摘要',
                'one_liner_en': 'Analysis unavailable',
                'problem_zh': '', 'problem_en': '',
                'method_zh': '', 'method_en': '',
                'results_zh': '', 'results_en': '',
                'key_formulas': [],
                'why_it_matters_zh': '', 'why_it_matters_en': '',
            }
        featured_results.append({'paper': paper, 'analysis': analysis, 'figures': []})

    # Step 4: Extract figures from PDFs
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

    # Step 5: Brief analysis for remaining papers
    print('\n📋 Generating brief summaries...')
    try:
        brief_summaries = analyze_brief_batch(brief_papers_raw)
    except Exception as e:
        print(f'   Brief analysis failed: {e}')
        brief_summaries = [
            {'index': i+1, 'title_zh': p['title'], 'summary_zh': '', 'summary_en': ''}
            for i, p in enumerate(brief_papers_raw)
        ]

    brief_results = []
    for paper, summary_data in zip(brief_papers_raw, brief_summaries):
        brief_results.append({'paper': paper, 'summary': summary_data})

    # Step 6: Generate HTML
    print('\n🎨 Rendering HTML report...')
    try:
        save_report(date_str, featured_results, brief_results, docs_dir='docs')
        print(f'\n✅ Report saved for {date_str}')
        print(f'   Featured: {len(featured_results)} papers')
        print(f'   Brief:    {len(brief_results)} papers')
    except Exception as e:
        print(f'   Render failed: {e}')
        raise

    # Clean up temp dir
    if tmp_dir.exists():
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f'\n🌐 Report will be live at: https://zerlindamazz-droid.github.io/ai-paper-daily/')

    # Step 7: Generate PDF
    print('\n📄 Generating PDF...')
    pdf_path = None
    try:
        html_path = Path('docs/index.html').resolve()
        pdf_path = Path(f'tmp_{date_str}.pdf')
        generate_pdf(html_path, pdf_path)
    except Exception as e:
        print(f'  PDF generation failed: {e}')

    # Step 8: Send email
    print('\n📧 Sending email...')
    send_email(date_str, featured_results, brief_results, pdf_path=pdf_path)

    # Clean up PDF
    if pdf_path and pdf_path.exists():
        pdf_path.unlink()

    print('Done! ✨\n')


if __name__ == '__main__':
    main()
