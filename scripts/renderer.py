"""Generate beautiful bilingual HTML report from processed paper data."""
import json
from datetime import datetime
from pathlib import Path

# Tag color mapping
TAG_COLORS = {
    'LLM': '#818cf8', 'Large Language Model': '#818cf8', 'Language Model': '#818cf8',
    'Fine-tuning': '#f472b6', 'PEFT': '#f472b6', 'LoRA': '#f472b6',
    'Training': '#34d399', 'Pretraining': '#34d399', 'Pre-training': '#34d399',
    'RLHF': '#fb923c', 'Reinforcement Learning': '#fb923c', 'RL': '#fb923c',
    'Alignment': '#fbbf24', 'Safety': '#fbbf24',
    'Multimodal': '#a78bfa', 'Vision-Language': '#a78bfa',
    'Diffusion': '#38bdf8', 'Diffusion Model': '#38bdf8',
    'Optimization': '#4ade80', 'Gradient': '#4ade80',
    'Architecture': '#60a5fa', 'Transformer': '#60a5fa', 'Attention': '#60a5fa',
    'Efficiency': '#f97316', 'Compression': '#f97316', 'Quantization': '#f97316',
    'Distributed': '#e879f9', 'Parallel': '#e879f9',
    'Reasoning': '#fde047', 'Chain-of-Thought': '#fde047',
}

def tag_color(tag):
    for k, v in TAG_COLORS.items():
        if k.lower() in tag.lower():
            return v
    return '#94a3b8'


SHARED_CSS = """
:root {
  --bg: #0a0a12;
  --bg2: #12121e;
  --bg3: #1a1a2e;
  --bg4: #22223a;
  --accent: #818cf8;
  --accent2: #c084fc;
  --text: #e2e8f0;
  --text2: #94a3b8;
  --text3: #64748b;
  --border: rgba(255,255,255,0.07);
  --card-shadow: 0 4px 24px rgba(0,0,0,0.4);
  --radius: 16px;
  --radius-sm: 8px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  font-size: 16px;
  line-height: 1.7;
  min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* NAV */
nav {
  position: sticky; top: 0; z-index: 100;
  background: rgba(10,10,18,0.85);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  display: flex; align-items: center; gap: 16px;
  height: 56px;
}
nav .logo {
  font-weight: 700; font-size: 15px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-right: auto;
}
nav a { color: var(--text2); font-size: 14px; transition: color 0.2s; }
nav a:hover { color: var(--text); text-decoration: none; }
.nav-date { color: var(--text3); font-size: 13px; }

/* HERO */
.hero {
  text-align: center;
  padding: 64px 24px 48px;
  background: radial-gradient(ellipse at top, rgba(129,140,248,0.12) 0%, transparent 60%);
}
.hero-badge {
  display: inline-block;
  background: rgba(129,140,248,0.15);
  border: 1px solid rgba(129,140,248,0.3);
  color: var(--accent);
  font-size: 12px; font-weight: 600; letter-spacing: 0.08em;
  padding: 4px 12px; border-radius: 100px;
  margin-bottom: 20px;
  text-transform: uppercase;
}
.hero h1 {
  font-size: clamp(28px, 5vw, 48px);
  font-weight: 800; letter-spacing: -0.03em;
  background: linear-gradient(135deg, #fff 30%, rgba(255,255,255,0.6));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 8px;
}
.hero h2 {
  font-size: clamp(14px, 2.5vw, 18px);
  font-weight: 400; color: var(--text2);
  margin-bottom: 24px;
}
.hero-meta {
  display: flex; justify-content: center; gap: 24px; flex-wrap: wrap;
  font-size: 13px; color: var(--text3);
}
.hero-meta span { display: flex; align-items: center; gap: 6px; }

/* SECTION HEADERS */
.section-header {
  display: flex; align-items: center; gap: 12px;
  padding: 0 24px; margin: 48px 0 24px;
  max-width: 1100px; margin-left: auto; margin-right: auto;
}
.section-header h2 {
  font-size: 20px; font-weight: 700;
}
.section-header .sub { color: var(--text2); font-size: 14px; font-weight: 400; margin-left: 4px; }
.section-divider {
  flex: 1; height: 1px;
  background: linear-gradient(to right, var(--border), transparent);
}

/* MAIN LAYOUT */
.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }

/* FEATURED PAPERS GRID */
.featured-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 340px), 1fr));
  gap: 20px;
  padding: 0 24px;
  max-width: 1100px; margin: 0 auto;
}

/* PAPER CARD */
.paper-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
  display: flex; flex-direction: column;
}
.paper-card:hover {
  transform: translateY(-2px);
  border-color: rgba(129,140,248,0.25);
  box-shadow: var(--card-shadow);
}

/* RANK BADGE */
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 16px 0;
  gap: 8px;
}
.rank-badge {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 50%;
  font-size: 12px; font-weight: 800;
  flex-shrink: 0;
}
.rank-1 { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #000; }
.rank-2 { background: linear-gradient(135deg, #94a3b8, #64748b); color: #fff; }
.rank-3 { background: linear-gradient(135deg, #fb923c, #ea580c); color: #fff; }
.importance-bar {
  flex: 1;
  height: 4px; background: var(--bg4); border-radius: 2px;
  overflow: hidden;
}
.importance-fill {
  height: 100%;
  background: linear-gradient(to right, var(--accent), var(--accent2));
  border-radius: 2px;
  transition: width 1s ease;
}
.importance-score {
  font-size: 12px; color: var(--text2); font-weight: 600; white-space: nowrap;
}

/* TAGS */
.tags {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 10px 16px 0;
}
.tag {
  font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
  padding: 2px 8px; border-radius: 100px;
  background: rgba(148,163,184,0.1);
  border: 1px solid rgba(148,163,184,0.15);
  white-space: nowrap;
}

/* PAPER TITLE */
.paper-title { padding: 12px 16px 4px; }
.paper-title .title-en {
  font-size: 15px; font-weight: 700; line-height: 1.4;
  color: var(--text); display: block; margin-bottom: 4px;
}
.paper-title .title-zh {
  font-size: 13px; color: var(--text2); display: block;
  font-weight: 500;
}
.paper-authors {
  font-size: 12px; color: var(--text3);
  padding: 2px 16px 8px;
}

/* FIGURE */
.paper-figure {
  margin: 8px 16px 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg3);
  position: relative;
}
.paper-figure img {
  width: 100%; max-height: 200px;
  object-fit: contain;
  display: block;
}
.figure-caption {
  font-size: 11px; color: var(--text3);
  padding: 4px 8px;
  text-align: center;
  background: var(--bg3);
}

/* ONE-LINER */
.one-liner {
  margin: 12px 16px 0;
  padding: 10px 14px;
  background: rgba(129,140,248,0.08);
  border-left: 3px solid var(--accent);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 13px;
}
.one-liner .zh { color: var(--text); font-weight: 600; }
.one-liner .en { color: var(--text2); font-size: 12px; margin-top: 2px; }

/* CONTENT SECTIONS */
.content-sections { padding: 12px 16px 0; flex: 1; }
.content-section { margin-bottom: 14px; }
.content-section h4 {
  font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  color: var(--text3); text-transform: uppercase;
  margin-bottom: 6px;
}
.bilingual { display: flex; flex-direction: column; gap: 6px; }
.bilingual .zh { font-size: 14px; color: var(--text); line-height: 1.6; }
.bilingual .en { font-size: 13px; color: var(--text2); line-height: 1.5; }

/* FORMULAS */
.formulas-section { margin-bottom: 14px; }
.formulas-section h4 {
  font-size: 12px; font-weight: 700; letter-spacing: 0.06em;
  color: var(--text3); text-transform: uppercase; margin-bottom: 8px;
}
.formula-block {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
  margin-bottom: 8px;
}
.formula-math {
  font-size: 14px; overflow-x: auto;
  padding: 4px 0; margin-bottom: 8px;
  color: #e2e8f0;
}
.formula-explain { display: flex; flex-direction: column; gap: 4px; }
.formula-explain .zh { font-size: 13px; color: var(--text); }
.formula-explain .en { font-size: 12px; color: var(--text2); }

/* CARD FOOTER */
.card-footer {
  padding: 12px 16px 14px;
  display: flex; gap: 8px; flex-wrap: wrap;
  border-top: 1px solid var(--border);
  margin-top: 12px;
}
.btn {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 600;
  padding: 5px 12px; border-radius: 6px;
  border: 1px solid var(--border);
  color: var(--text2);
  transition: all 0.2s;
  background: var(--bg3);
}
.btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  text-decoration: none;
  background: rgba(129,140,248,0.08);
}
.btn-primary {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-color: transparent; color: #fff;
}
.btn-primary:hover { opacity: 0.9; color: #fff; }

/* QUICK READS */
.quick-reads-list {
  max-width: 1100px; margin: 0 auto;
  padding: 0 24px;
  display: flex; flex-direction: column; gap: 12px;
}
.quick-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 12px;
  align-items: start;
  transition: border-color 0.2s;
}
.quick-card:hover { border-color: rgba(129,140,248,0.25); }
.quick-title-en { font-size: 14px; font-weight: 700; margin-bottom: 2px; }
.quick-title-zh { font-size: 13px; color: var(--text2); margin-bottom: 8px; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.quick-summary { font-size: 13px; color: var(--text2); line-height: 1.5; }
.quick-summary .zh { margin-bottom: 4px; }
.quick-summary .en { color: var(--text3); }
.quick-links {
  display: flex; flex-direction: column; gap: 6px; flex-shrink: 0;
}

/* FOOTER */
footer {
  margin-top: 80px;
  padding: 32px 24px;
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--text3);
  font-size: 13px;
}
footer a { color: var(--text2); }

/* ARCHIVE PAGE */
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  max-width: 1100px; margin: 0 auto; padding: 0 24px;
}
.archive-item {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  transition: all 0.2s;
}
.archive-item:hover {
  border-color: rgba(129,140,248,0.3);
  transform: translateY(-1px);
}
.archive-item a { color: var(--text); display: block; }
.archive-item a:hover { text-decoration: none; }
.archive-date { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
.archive-count { font-size: 12px; color: var(--text3); }

/* RESPONSIVE */
@media (max-width: 600px) {
  .featured-grid { padding: 0 12px; gap: 14px; }
  .quick-reads-list { padding: 0 12px; }
  .quick-card { grid-template-columns: 1fr; }
  nav { padding: 0 12px; }
}

/* SCROLLBAR */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--bg4); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }
"""


def build_nav(date_str, is_archive=False):
    home = 'index.html' if is_archive else '#'
    archive = 'archive/index.html' if not is_archive else '../archive/index.html'
    back = '../' if is_archive else ''
    return f"""<nav>
  <span class="logo">⚡ AI Papers Daily</span>
  <a href="{back}index.html">今日 Today</a>
  <a href="{back}archive/index.html">历史 Archive</a>
  <span class="nav-date">{date_str}</span>
</nav>"""


def build_featured_card(rank, paper, analysis, figures):
    safe_id = paper['id'].replace('/', '_').replace('.', '_')
    tags_en = paper.get('topic_tags_en', [])
    tags_zh = paper.get('topic_tags_zh', [])

    # Tags HTML
    tags_html = ''
    for t_en, t_zh in zip(tags_en[:4], tags_zh[:4]):
        color = tag_color(t_en)
        tags_html += f'<span class="tag" style="border-color:{color}33;color:{color}">{t_en} · {t_zh}</span>'

    # Figure HTML
    fig_html = ''
    if figures:
        fig = figures[0]
        fig_html = f"""<div class="paper-figure">
      <img src="{fig['data_uri']}" alt="Paper figure from page {fig['page']}" loading="lazy">
      <p class="figure-caption">图 Figure · Page {fig['page']} of paper</p>
    </div>"""

    # Formulas HTML
    formulas_html = ''
    key_formulas = analysis.get('key_formulas', [])
    if key_formulas:
        formula_items = ''
        for f in key_formulas[:2]:  # Max 2 formulas
            latex = f.get('latex', '').strip()
            if not latex:
                continue
            ez = f.get('explanation_zh', '')
            ee = f.get('explanation_en', '')
            formula_items += f"""<div class="formula-block">
        <div class="formula-math">\\[{latex}\\]</div>
        <div class="formula-explain">
          <span class="zh">💡 {ez}</span>
          <span class="en">{ee}</span>
        </div>
      </div>"""
        if formula_items:
            formulas_html = f"""<div class="formulas-section">
      <h4>📐 Key Formulas · 关键公式</h4>
      {formula_items}
    </div>"""

    importance = paper.get('importance_score', 8)
    authors_str = ', '.join(paper['authors'][:4])
    if len(paper['authors']) > 4:
        authors_str += ' et al.'

    code_btn = ''
    if paper.get('code_url'):
        code_btn = f'<a href="{paper["code_url"]}" target="_blank" class="btn">💻 Code</a>'

    return f"""<article class="paper-card" id="paper-{safe_id}">
  <div class="card-header">
    <span class="rank-badge rank-{rank}">#{rank}</span>
    <div class="importance-bar">
      <div class="importance-fill" style="width:{importance*10}%"></div>
    </div>
    <span class="importance-score">★ {importance}/10</span>
  </div>

  <div class="tags">{tags_html}</div>

  <div class="paper-title">
    <span class="title-en">{paper['title']}</span>
    <span class="title-zh">{analysis.get('title_zh', '')}</span>
  </div>
  <p class="paper-authors">🧑‍🔬 {authors_str}</p>

  {fig_html}

  <div class="one-liner">
    <div class="zh">🎯 {analysis.get('one_liner_zh', '')}</div>
    <div class="en">{analysis.get('one_liner_en', '')}</div>
  </div>

  <div class="content-sections">
    <div class="content-section">
      <h4>❓ Problem · 解决什么问题</h4>
      <div class="bilingual">
        <span class="zh">{analysis.get('problem_zh', '')}</span>
        <span class="en">{analysis.get('problem_en', '')}</span>
      </div>
    </div>

    <div class="content-section">
      <h4>⚙️ Method · 方法</h4>
      <div class="bilingual">
        <span class="zh">{analysis.get('method_zh', '')}</span>
        <span class="en">{analysis.get('method_en', '')}</span>
      </div>
    </div>

    {formulas_html}

    <div class="content-section">
      <h4>📊 Results · 结果</h4>
      <div class="bilingual">
        <span class="zh">{analysis.get('results_zh', '')}</span>
        <span class="en">{analysis.get('results_en', '')}</span>
      </div>
    </div>

    <div class="content-section">
      <h4>🌟 Why It Matters · 为什么重要</h4>
      <div class="bilingual">
        <span class="zh">{analysis.get('why_it_matters_zh', '')}</span>
        <span class="en">{analysis.get('why_it_matters_en', '')}</span>
      </div>
    </div>
  </div>

  <div class="card-footer">
    <a href="{paper['arxiv_url']}" target="_blank" class="btn btn-primary">📄 arXiv</a>
    <a href="{paper['pdf_url']}" target="_blank" class="btn">📥 PDF</a>
    {code_btn}
  </div>
</article>"""


def build_quick_card(paper, summary):
    tags_en = paper.get('topic_tags_en', [])
    tags_zh = paper.get('topic_tags_zh', [])
    tags_html = ''
    for t_en, t_zh in zip(tags_en[:3], tags_zh[:3]):
        color = tag_color(t_en)
        tags_html += f'<span class="tag" style="border-color:{color}33;color:{color}">{t_en} · {t_zh}</span>'

    authors_str = ', '.join(paper['authors'][:3])
    if len(paper['authors']) > 3:
        authors_str += ' et al.'

    code_btn = ''
    if paper.get('code_url'):
        code_btn = f'<a href="{paper["code_url"]}" target="_blank" class="btn" style="font-size:11px">💻 Code</a>'

    return f"""<div class="quick-card">
  <div>
    <div class="quick-title-en">{paper['title']}</div>
    <div class="quick-title-zh">{summary.get('title_zh', '')}</div>
    <div class="quick-tags">{tags_html}</div>
    <div class="quick-summary">
      <div class="zh">{summary.get('summary_zh', '')}</div>
      <div class="en">{summary.get('summary_en', '')}</div>
    </div>
    <p style="font-size:11px;color:var(--text3);margin-top:6px">🧑‍🔬 {authors_str}</p>
  </div>
  <div class="quick-links">
    <a href="{paper['arxiv_url']}" target="_blank" class="btn btn-primary" style="font-size:11px">📄 arXiv</a>
    <a href="{paper['pdf_url']}" target="_blank" class="btn" style="font-size:11px">📥 PDF</a>
    {code_btn}
  </div>
</div>"""


def build_full_page(date_str, featured_papers, brief_papers, is_archive_copy=False):
    """Build complete HTML report page."""
    back = '../' if is_archive_copy else ''

    featured_html = '\n'.join([
        build_featured_card(i+1, p['paper'], p['analysis'], p['figures'])
        for i, p in enumerate(featured_papers)
    ])

    brief_html = '\n'.join([
        build_quick_card(p['paper'], p['summary'])
        for p in brief_papers
    ])

    total = len(featured_papers) + len(brief_papers)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 论文日报 · {date_str}</title>
  <meta name="description" content="AI Model Training Papers Daily Digest - {date_str}">
  <script>
    MathJax = {{
      tex: {{
        inlineMath: [['\\\\(','\\\\)']],
        displayMath: [['\\\\[','\\\\]'], ['$$','$$']],
        packages: {{'[+]': ['ams']}}
      }},
      options: {{ skipHtmlTags: ['script','noscript','style','textarea'] }}
    }};
  </script>
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
  <style>{SHARED_CSS}</style>
</head>
<body>

{build_nav(date_str)}

<div class="hero">
  <div class="hero-badge">AI Model Training · Daily Digest</div>
  <h1>AI 模型训练论文日报</h1>
  <h2>AI Training Papers Daily</h2>
  <div class="hero-meta">
    <span>📅 {date_str}</span>
    <span>📄 {total} papers selected from arXiv</span>
    <span>🔬 cs.LG · cs.AI · cs.CL · stat.ML</span>
  </div>
</div>

<div class="section-header">
  <h2>🔥 Today's Highlights <span class="sub">今日精选论文</span></h2>
  <div class="section-divider"></div>
</div>

<div class="featured-grid">
{featured_html}
</div>

<div class="section-header" style="margin-top:56px">
  <h2>📚 More Papers <span class="sub">更多值得关注的论文</span></h2>
  <div class="section-divider"></div>
</div>

<div class="quick-reads-list">
{brief_html}
</div>

<footer>
  <p>Powered by <strong>arXiv</strong> + <strong>Claude AI</strong> · 数据来源 arXiv，AI 解读由 Claude 生成</p>
  <p style="margin-top:8px"><a href="{back}archive/index.html">📁 历史报告 Archive</a></p>
</footer>

</body>
</html>"""


def build_archive_index(reports):
    """Build archive listing page."""
    items_html = ''
    for r in sorted(reports, reverse=True):
        items_html += f"""<div class="archive-item">
  <a href="{r['date']}.html">
    <div class="archive-date">📅 {r['date']}</div>
    <div class="archive-count">{r['count']} papers</div>
  </a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 论文日报 · 历史存档</title>
  <style>{SHARED_CSS}</style>
</head>
<body>
{build_nav('历史存档 Archive', is_archive=True)}
<div class="hero">
  <div class="hero-badge">Archive · 历史存档</div>
  <h1>历史报告</h1>
  <h2>Past Reports Archive</h2>
</div>
<div class="section-header">
  <h2>📁 All Reports <span class="sub">所有历史报告</span></h2>
  <div class="section-divider"></div>
</div>
<div class="archive-grid">
{items_html}
</div>
<footer>
  <p><a href="../index.html">← 返回今日报告 Back to Today</a></p>
</footer>
</body>
</html>"""


def save_report(date_str, featured_papers, brief_papers, docs_dir='docs'):
    docs = Path(docs_dir)
    archive_dir = docs / 'archive'
    archive_dir.mkdir(parents=True, exist_ok=True)

    html = build_full_page(date_str, featured_papers, brief_papers)
    archive_html = build_full_page(date_str, featured_papers, brief_papers, is_archive_copy=True)

    # Write index.html (latest)
    (docs / 'index.html').write_text(html, encoding='utf-8')
    print(f'  Saved docs/index.html')

    # Write archive copy
    archive_file = archive_dir / f'{date_str}.html'
    archive_file.write_text(archive_html, encoding='utf-8')
    print(f'  Saved docs/archive/{date_str}.html')

    # Update archive index
    existing = []
    for f in archive_dir.glob('????-??-??.html'):
        count = featured_papers.__len__() + brief_papers.__len__() if f.stem == date_str else 0
        existing.append({'date': f.stem, 'count': count or 8})

    archive_index = build_archive_index(existing)
    (archive_dir / 'index.html').write_text(archive_index, encoding='utf-8')
    print(f'  Saved docs/archive/index.html ({len(existing)} reports)')
