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
  --bg: #f5f6fa;
  --bg2: #ffffff;
  --bg3: #f0f1f8;
  --bg4: #e4e6f0;
  --accent: #5b5ef4;
  --accent2: #a855f7;
  --accent-light: #eef0ff;
  --text: #1a1a2e;
  --text2: #555577;
  --text3: #8888aa;
  --border: #e2e4f0;
  --card-shadow: 0 2px 16px rgba(91,94,244,0.08);
  --radius: 20px;
  --radius-sm: 12px;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
  font-size: 19px;
  line-height: 1.8;
  min-height: 100vh;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* NAV */
nav {
  position: sticky; top: 0; z-index: 100;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 0 32px;
  display: flex; align-items: center; gap: 20px;
  height: 60px;
  box-shadow: 0 1px 8px rgba(0,0,0,0.06);
}
nav .logo {
  font-weight: 800; font-size: 17px;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-right: auto;
  letter-spacing: -0.02em;
}
nav a {
  color: var(--text2); font-size: 15px; font-weight: 500;
  padding: 6px 14px; border-radius: 8px;
  transition: all 0.2s;
}
nav a:hover { background: var(--accent-light); color: var(--accent); text-decoration: none; }
.nav-date { color: var(--text3); font-size: 14px; font-weight: 500; }

/* HERO */
.hero {
  text-align: center;
  padding: 72px 24px 56px;
  background: linear-gradient(180deg, #eef0ff 0%, #f5f6fa 100%);
  border-bottom: 1px solid var(--border);
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--accent-light);
  border: 1.5px solid rgba(91,94,244,0.2);
  color: var(--accent);
  font-size: 13px; font-weight: 700; letter-spacing: 0.05em;
  padding: 5px 14px; border-radius: 100px;
  margin-bottom: 24px;
  text-transform: uppercase;
}
.hero h1 {
  font-size: clamp(32px, 5vw, 52px);
  font-weight: 900; letter-spacing: -0.04em;
  color: var(--text);
  margin-bottom: 10px;
  line-height: 1.15;
}
.hero h1 span {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero h2 {
  font-size: clamp(16px, 2.5vw, 20px);
  font-weight: 400; color: var(--text2);
  margin-bottom: 28px;
}
.hero-meta {
  display: flex; justify-content: center; gap: 8px; flex-wrap: wrap;
}
.hero-chip {
  background: white; border: 1px solid var(--border);
  border-radius: 100px; padding: 6px 16px;
  font-size: 14px; color: var(--text2); font-weight: 500;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

/* SECTION HEADERS */
.section-header {
  display: flex; align-items: center; gap: 14px;
  padding: 0 32px; margin: 56px auto 28px;
  max-width: 1160px;
}
.section-header h2 {
  font-size: 22px; font-weight: 800; white-space: nowrap;
  letter-spacing: -0.02em;
}
.section-header .sub {
  color: var(--text2); font-size: 16px; font-weight: 400; margin-left: 6px;
}
.section-divider {
  flex: 1; height: 1px;
  background: var(--border);
}

/* FEATURED PAPERS GRID */
.featured-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 360px), 1fr));
  gap: 24px;
  padding: 0 32px;
  max-width: 1160px; margin: 0 auto;
}

/* PAPER CARD */
.paper-card {
  background: var(--bg2);
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex; flex-direction: column;
  box-shadow: var(--card-shadow);
}
.paper-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(91,94,244,0.14);
}

/* CARD TOP COLOR STRIPE */
.card-stripe {
  height: 5px;
  background: linear-gradient(to right, var(--accent), var(--accent2));
}
.card-stripe.rank-2 { background: linear-gradient(to right, #06b6d4, #3b82f6); }
.card-stripe.rank-3 { background: linear-gradient(to right, #f59e0b, #ef4444); }

/* RANK BADGE */
.card-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px 0;
  gap: 10px;
}
.rank-badge {
  display: flex; align-items: center; gap: 5px;
  font-size: 13px; font-weight: 800;
  padding: 4px 10px; border-radius: 100px;
}
.rank-1 { background: #fff7ed; color: #d97706; border: 1.5px solid #fed7aa; }
.rank-2 { background: #eff6ff; color: #2563eb; border: 1.5px solid #bfdbfe; }
.rank-3 { background: #fef2f2; color: #dc2626; border: 1.5px solid #fecaca; }
.importance-score {
  font-size: 13px; color: var(--text3); font-weight: 600;
  background: var(--bg3); padding: 3px 10px; border-radius: 100px;
}

/* TAGS */
.tags {
  display: flex; flex-wrap: wrap; gap: 6px;
  padding: 12px 20px 0;
}
.tag {
  font-size: 12px; font-weight: 600;
  padding: 3px 10px; border-radius: 100px;
  background: var(--accent-light);
  color: var(--accent);
  border: 1px solid rgba(91,94,244,0.15);
  white-space: nowrap;
}

/* PAPER TITLE */
.paper-title { padding: 14px 20px 4px; }
.paper-title .title-en {
  font-size: 19px; font-weight: 800; line-height: 1.4;
  color: var(--text); display: block; margin-bottom: 5px;
  letter-spacing: -0.01em;
}
.paper-title .title-zh {
  font-size: 17px; color: var(--accent); display: block;
  font-weight: 600;
}
.paper-authors {
  font-size: 14px; color: var(--text3);
  padding: 3px 20px 10px;
}

/* FIGURE */
.paper-figure {
  margin: 10px 20px 0;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--bg3);
  border: 1px solid var(--border);
}
.paper-figure img {
  width: 100%; max-height: 220px;
  object-fit: contain;
  display: block;
  background: white;
}
.figure-caption {
  font-size: 12px; color: var(--text3);
  padding: 5px 10px;
  text-align: center;
  background: var(--bg3);
}

/* ONE-LINER */
.one-liner {
  margin: 14px 20px 0;
  padding: 12px 16px;
  background: var(--accent-light);
  border-left: 4px solid var(--accent);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.one-liner .zh { color: var(--text); font-weight: 700; font-size: 18px; line-height: 1.5; }
.one-liner .en { color: var(--text2); font-size: 16px; margin-top: 4px; }

/* CONTENT SECTIONS */
.content-sections { padding: 14px 20px 0; flex: 1; }
.content-section { margin-bottom: 18px; }
.content-section h4 {
  font-size: 12px; font-weight: 800; letter-spacing: 0.08em;
  color: var(--accent); text-transform: uppercase;
  margin-bottom: 8px; display: flex; align-items: center; gap: 5px;
}
.bilingual { display: flex; flex-direction: column; gap: 8px; }
.bilingual .zh {
  font-size: 18px; color: var(--text); line-height: 1.75;
  background: var(--bg3); padding: 12px 16px;
  border-radius: var(--radius-sm);
}
.bilingual .en {
  font-size: 16px; color: var(--text2); line-height: 1.7;
  padding: 0 4px;
}

/* FORMULAS */
.formulas-section { margin-bottom: 18px; }
.formulas-section h4 {
  font-size: 12px; font-weight: 800; letter-spacing: 0.08em;
  color: var(--accent); text-transform: uppercase; margin-bottom: 10px;
}
.formula-block {
  background: #fafafa;
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  margin-bottom: 10px;
}
.formula-math {
  font-size: 16px; overflow-x: auto;
  padding: 6px 0; margin-bottom: 10px;
  color: var(--text);
}
.formula-explain { display: flex; flex-direction: column; gap: 5px; }
.formula-explain .zh { font-size: 17px; color: var(--text); }
.formula-explain .en { font-size: 15px; color: var(--text2); }

/* CARD FOOTER */
.card-footer {
  padding: 14px 20px 18px;
  display: flex; gap: 10px; flex-wrap: wrap;
  border-top: 1px solid var(--border);
  margin-top: 14px;
}
.btn {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 14px; font-weight: 600;
  padding: 7px 16px; border-radius: 10px;
  border: 1.5px solid var(--border);
  color: var(--text2);
  transition: all 0.2s;
  background: var(--bg3);
}
.btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  text-decoration: none;
  background: var(--accent-light);
}
.btn-primary {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  border-color: transparent; color: #fff;
  box-shadow: 0 2px 8px rgba(91,94,244,0.3);
}
.btn-primary:hover { opacity: 0.9; color: #fff; box-shadow: 0 4px 12px rgba(91,94,244,0.4); }

/* QUICK READS */
.quick-reads-list {
  max-width: 1160px; margin: 0 auto;
  padding: 0 32px;
  display: flex; flex-direction: column; gap: 14px;
}
.quick-card {
  background: var(--bg2);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 20px 24px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 16px;
  align-items: start;
  transition: all 0.2s;
  box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.quick-card:hover {
  border-color: rgba(91,94,244,0.3);
  box-shadow: 0 4px 16px rgba(91,94,244,0.1);
  transform: translateY(-1px);
}
.quick-title-en { font-size: 18px; font-weight: 800; margin-bottom: 3px; color: var(--text); }
.quick-title-zh { font-size: 17px; color: var(--accent); font-weight: 600; margin-bottom: 10px; }
.quick-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
.quick-summary { line-height: 1.7; }
.quick-summary .zh { font-size: 17px; color: var(--text); margin-bottom: 5px; }
.quick-summary .en { font-size: 15px; color: var(--text2); }
.quick-links {
  display: flex; flex-direction: column; gap: 8px; flex-shrink: 0;
}

/* FOOTER */
footer {
  margin-top: 80px;
  padding: 36px 24px;
  border-top: 1px solid var(--border);
  text-align: center;
  color: var(--text3);
  font-size: 14px;
  background: white;
}
footer a { color: var(--text2); font-weight: 500; }
footer a:hover { color: var(--accent); }

/* ARCHIVE PAGE */
.archive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 14px;
  max-width: 1160px; margin: 0 auto; padding: 0 32px;
}
.archive-item {
  background: var(--bg2);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 20px;
  transition: all 0.2s;
  box-shadow: 0 1px 6px rgba(0,0,0,0.04);
}
.archive-item:hover {
  border-color: rgba(91,94,244,0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(91,94,244,0.1);
}
.archive-item a { color: var(--text); display: block; }
.archive-item a:hover { text-decoration: none; }
.archive-date { font-size: 17px; font-weight: 800; margin-bottom: 4px; }
.archive-count { font-size: 13px; color: var(--text3); }

/* RESPONSIVE */
@media (max-width: 640px) {
  .featured-grid { padding: 0 16px; gap: 16px; }
  .quick-reads-list { padding: 0 16px; }
  .quick-card { grid-template-columns: 1fr; }
  nav { padding: 0 16px; }
  .section-header { padding: 0 16px; }
}

/* RANK 4 */
.card-stripe.rank-4 { background: linear-gradient(to right, #10b981, #06b6d4); }
.rank-4 { background: #f0fdf4; color: #059669; border: 1.5px solid #a7f3d0; }

/* SUMMARY TABLE */
.summary-table {
  width: calc(100% - 40px);
  margin: 16px 20px 0;
  border-collapse: collapse;
  font-size: 15px;
  border: 1.5px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}
.summary-table thead tr { background: var(--accent-light); }
.summary-table th {
  color: var(--accent);
  font-size: 11px;
  font-weight: 800;
  padding: 8px 12px;
  text-align: left;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.summary-table td {
  padding: 10px 12px;
  border-top: 1px solid var(--border);
  vertical-align: top;
  line-height: 1.65;
}
.summary-table td.dim-label {
  width: 90px;
  font-size: 12px;
  font-weight: 800;
  color: var(--accent);
  background: var(--bg3);
  white-space: nowrap;
}
.summary-table .cell-zh { font-size: 15px; color: var(--text); display: block; }
.summary-table .cell-en { font-size: 13px; color: var(--text2); display: block; margin-top: 3px; }
.summary-table .link-row td { background: var(--bg3); }
.summary-table .link-row a { color: var(--accent); font-weight: 600; font-size: 14px; }

/* CONCLUSION BANNER (quick cards) */
.quick-conclusion {
  margin-top: 8px;
  padding: 8px 12px;
  background: linear-gradient(135deg, #eef0ff, #f5f0ff);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  font-size: 14px;
}
.quick-conclusion .zh { color: var(--text); font-weight: 600; }
.quick-conclusion .en { color: var(--text2); margin-top: 2px; font-size: 13px; }

/* SCROLLBAR */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: #c7c9e0; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
"""


def _rank_stripe(rank):
    classes = {1: 'rank-1', 2: 'rank-2', 3: 'rank-3', 4: 'rank-4'}
    return f'<div class="card-stripe {classes.get(rank, "")}"></div>'


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
            if not isinstance(f, dict):
                continue
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
  {_rank_stripe(rank)}
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

  <!-- Summary Table: quick-glance overview -->
  <table class="summary-table">
    <thead>
      <tr>
        <th>维度</th>
        <th>中文</th>
        <th>English</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td class="dim-label">❓ 待解决<br>的问题</td>
        <td><span class="cell-zh">{analysis.get('problem_zh', '')}</span></td>
        <td><span class="cell-en">{analysis.get('problem_en', '')}</span></td>
      </tr>
      <tr>
        <td class="dim-label">💡 解决<br>的亮点</td>
        <td><span class="cell-zh">{analysis.get('highlights_zh', '')}</span></td>
        <td><span class="cell-en">{analysis.get('highlights_en', '')}</span></td>
      </tr>
      <tr>
        <td class="dim-label">🧪 实验<br>内容</td>
        <td><span class="cell-zh">{analysis.get('experiment_zh', '')}</span></td>
        <td><span class="cell-en">{analysis.get('experiment_en', '')}</span></td>
      </tr>
      <tr>
        <td class="dim-label">📊 实验<br>结果</td>
        <td><span class="cell-zh">{analysis.get('results_zh', '')}</span></td>
        <td><span class="cell-en">{analysis.get('results_en', '')}</span></td>
      </tr>
      <tr>
        <td class="dim-label">🏁 结论</td>
        <td><span class="cell-zh">{analysis.get('conclusion_zh', '')}</span></td>
        <td><span class="cell-en">{analysis.get('conclusion_en', '')}</span></td>
      </tr>
      <tr class="link-row">
        <td class="dim-label">🔗 论文<br>链接</td>
        <td colspan="2">
          <a href="{paper['arxiv_url']}" target="_blank">arXiv: {paper['id']}</a>
          &nbsp;·&nbsp;
          <a href="{paper['pdf_url']}" target="_blank">📥 PDF</a>
        </td>
      </tr>
    </tbody>
  </table>

  <div class="content-sections">
    <div class="content-section">
      <h4>⚙️ Method · 方法详解</h4>
      <div class="bilingual">
        <span class="zh">{analysis.get('method_zh', '')}</span>
        <span class="en">{analysis.get('method_en', '')}</span>
      </div>
    </div>

    {formulas_html}

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
    if not isinstance(summary, dict):
        summary = {}
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
    <div class="quick-conclusion">
      <div class="zh">🏁 结论：{summary.get('conclusion_zh', '')}</div>
      <div class="en">{summary.get('conclusion_en', '')}</div>
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
  <div class="hero-badge">🔬 AI Model Training · Daily Digest</div>
  <h1>AI 模型训练<span>论文日报</span></h1>
  <h2>AI Training Papers Daily</h2>
  <div class="hero-meta">
    <span class="hero-chip">📅 {date_str}</span>
    <span class="hero-chip">📄 {total} papers</span>
    <span class="hero-chip">🤖 LLM · Robotics · Multimodal · RL</span>
    <span class="hero-chip">🔬 cs.LG · cs.AI · cs.CL · cs.RO · stat.ML</span>
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
    for r in sorted(reports, key=lambda x: x['date'], reverse=True):
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
