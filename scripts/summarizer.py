"""Use Claude API to select and summarize papers with bilingual analysis."""
import anthropic
import json
import re

client = anthropic.Anthropic()


def select_and_rank(papers):
    """Send all papers to Claude for ranking. Returns top 8 with scores."""
    paper_list = '\n\n'.join([
        f'[{i+1}] ID: {p["id"]}\nTitle: {p["title"]}\nCategories: {", ".join(p["categories"][:3])}\nAbstract: {p["abstract"][:500]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""You are an expert AI researcher curating a daily digest of the most important AI model training papers.

From the following {len(papers)} arXiv papers, select:
- Top 3 FEATURED papers (most significant contributions to AI model training)
- Next 5 BRIEF papers (worth mentioning, broader coverage)

Focus areas to cover (try to diversify): LLMs, fine-tuning/PEFT, training efficiency, architecture innovation, RLHF/alignment, multimodal training, diffusion models, optimization, distributed training.

Papers:
{paper_list}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "featured": [
    {{"rank": 1, "paper_index": <1-based index>, "importance_score": <1-10>, "topic_tags_en": ["tag1","tag2","tag3"], "topic_tags_zh": ["标签1","标签2","标签3"]}},
    {{"rank": 2, "paper_index": ..., "importance_score": ..., "topic_tags_en": [...], "topic_tags_zh": [...]}},
    {{"rank": 3, "paper_index": ..., "importance_score": ..., "topic_tags_en": [...], "topic_tags_zh": [...]}}
  ],
  "brief": [
    {{"paper_index": <1-based index>, "topic_tags_en": [...], "topic_tags_zh": [...]}},
    ...5 items total...
  ]
}}"""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}]
    )

    text = resp.content[0].text.strip()
    # Extract JSON block if wrapped in markdown
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        text = m.group()
    return json.loads(text)


def analyze_featured(paper):
    """Deep bilingual analysis for a featured paper."""
    prompt = f"""You are an expert AI researcher writing for a bilingual (Chinese + English) daily digest.
Analyze this paper deeply but in plain, accessible language. Keep math formulas accurate but explain them intuitively.

Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Abstract: {paper['abstract']}

Return ONLY valid JSON (no markdown, no wrapping text):
{{
  "title_zh": "中文标题翻译",
  "one_liner_zh": "一句话概括这篇论文的核心贡献（通俗中文，20字以内）",
  "one_liner_en": "One sentence core contribution (plain English, under 20 words)",
  "problem_zh": "解决了什么问题？（通俗中文，2-3句话，让非专业人士也能理解）",
  "problem_en": "What problem does it solve? (plain English, 2-3 sentences, accessible to non-experts)",
  "method_zh": "怎么解决的？（通俗中文，3-4句话，可适当提及关键技术术语）",
  "method_en": "How does it solve it? (plain English, 3-4 sentences)",
  "results_zh": "取得了什么效果？（通俗中文，具体数字优先）",
  "results_en": "What results were achieved? (plain English, specific numbers if available)",
  "key_formulas": [
    {{
      "latex": "LaTeX formula string (if any core formula is in abstract/title, else omit)",
      "explanation_zh": "这个公式的通俗解释（中文，1-2句）",
      "explanation_en": "Plain English explanation of this formula (1-2 sentences)"
    }}
  ],
  "why_it_matters_zh": "为什么这篇论文值得关注？对AI领域的意义（中文，2句话）",
  "why_it_matters_en": "Why does this paper matter? Its significance to the AI field (2 sentences)"
}}

Notes:
- key_formulas can be empty array [] if no specific formulas are in the abstract
- LaTeX should use standard notation (e.g. \\\\mathcal{{L}}, \\\\theta, etc.)
- Be specific with numbers/percentages in results
- Plain language means: explain it to a smart person who doesn't know ML"""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}]
    )

    text = resp.content[0].text.strip()
    m = re.search(r'\{[\s\S]*\}', text)
    if m:
        text = m.group()
    return json.loads(text)


def analyze_brief_batch(papers):
    """Brief bilingual analysis for multiple papers in one call."""
    paper_list = '\n\n'.join([
        f'[{i+1}] Title: {p["title"]}\nAbstract: {p["abstract"][:400]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""Provide brief bilingual summaries for these {len(papers)} AI papers for a daily digest.

{paper_list}

Return ONLY valid JSON array (no markdown):
[
  {{
    "index": 1,
    "title_zh": "中文标题翻译",
    "summary_zh": "2-3句话的中文简介，通俗易懂",
    "summary_en": "2-3 sentence English summary, plain language"
  }},
  ...{len(papers)} items total...
]"""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}]
    )

    text = resp.content[0].text.strip()
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        text = m.group()
    return json.loads(text)
