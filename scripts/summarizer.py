"""Use Claude API to select and summarize papers with bilingual analysis."""
import anthropic
import json
import re

client = anthropic.Anthropic()


def _extract_json(text, expect_array=False):
    """Robustly extract JSON from Claude response, handling common issues."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Find the outermost JSON object or array
    if expect_array:
        m = re.search(r'\[[\s\S]*\]', text)
    else:
        m = re.search(r'\{[\s\S]*\}', text)

    if not m:
        raise ValueError(f'No JSON found in response: {text[:200]}')

    raw = m.group()

    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fix common Claude JSON issues: unescaped newlines in strings
    # Replace literal newlines inside string values with \\n
    fixed = re.sub(r'(?<=": ")(.*?)(?="[,\n\}])', lambda m: m.group().replace('\n', '\\n'), raw, flags=re.DOTALL)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # Last resort: use json5-style tolerant parsing by removing trailing commas
    fixed2 = re.sub(r',\s*([}\]])', r'\1', raw)
    return json.loads(fixed2)


def _call_with_retry(prompt, max_tokens=1000, expect_array=False, retries=2):
    """Call Claude with retry logic for JSON parse failures."""
    last_err = None
    for attempt in range(retries + 1):
        instruction = "Return ONLY valid JSON. No markdown fences, no explanation, no text before or after. All string values must be properly escaped (use \\n for newlines, \\\" for quotes inside strings)."
        full_prompt = f"{instruction}\n\n{prompt}" if attempt == 0 else f"{instruction}\n\nIMPORTANT: Your previous response had a JSON syntax error. Return ONLY the JSON, nothing else.\n\n{prompt}"

        resp = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=max_tokens,
            messages=[{'role': 'user', 'content': full_prompt}]
        )
        text = resp.content[0].text
        try:
            return _extract_json(text, expect_array=expect_array)
        except Exception as e:
            last_err = e
            print(f'   JSON parse attempt {attempt+1} failed: {e}')

    raise ValueError(f'JSON parse failed after {retries+1} attempts: {last_err}')


def select_and_rank(papers):
    """Send all papers to Claude for ranking. Returns ranking dict."""
    paper_list = '\n\n'.join([
        f'[{i+1}] ID: {p["id"]}\nTitle: {p["title"]}\nCategories: {", ".join(p["categories"][:3])}\nAbstract: {p["abstract"][:400]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""You are an expert AI researcher curating a daily digest of the most important AI model training papers.

From the following {len(papers)} arXiv papers, select:
- Top 3 FEATURED papers (most significant contributions to AI model training)
- Next 5 BRIEF papers (worth mentioning, broader coverage)

Diversify topics: LLMs, fine-tuning/PEFT, training efficiency, architecture, RLHF/alignment, multimodal, diffusion, optimization, distributed training.

Papers:
{paper_list}

Return this exact JSON structure:
{{
  "featured": [
    {{"rank": 1, "paper_index": 5, "importance_score": 9, "topic_tags_en": ["LLM", "Fine-tuning"], "topic_tags_zh": ["大语言模型", "微调"]}},
    {{"rank": 2, "paper_index": 12, "importance_score": 8, "topic_tags_en": ["Diffusion"], "topic_tags_zh": ["扩散模型"]}},
    {{"rank": 3, "paper_index": 3, "importance_score": 8, "topic_tags_en": ["Optimization"], "topic_tags_zh": ["优化"]}}
  ],
  "brief": [
    {{"paper_index": 7, "topic_tags_en": ["RLHF"], "topic_tags_zh": ["强化学习"]}},
    {{"paper_index": 9, "topic_tags_en": ["Multimodal"], "topic_tags_zh": ["多模态"]}},
    {{"paper_index": 15, "topic_tags_en": ["Architecture"], "topic_tags_zh": ["架构"]}},
    {{"paper_index": 20, "topic_tags_en": ["Efficiency"], "topic_tags_zh": ["效率"]}},
    {{"paper_index": 25, "topic_tags_en": ["Training"], "topic_tags_zh": ["训练"]}}
  ]
}}"""

    return _call_with_retry(prompt, max_tokens=800)


def analyze_featured(paper):
    """Deep bilingual analysis for a featured paper."""
    prompt = f"""Analyze this AI paper for a bilingual daily digest. Use plain, accessible language. Be specific with numbers.

Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Abstract: {paper['abstract']}

Return this exact JSON (all values are strings, use \\n for line breaks if needed):
{{
  "title_zh": "中文标题翻译",
  "one_liner_zh": "一句话核心贡献（中文，20字以内）",
  "one_liner_en": "Core contribution in one sentence (under 20 words)",
  "problem_zh": "解决了什么问题（通俗中文，2-3句）",
  "problem_en": "What problem it solves (plain English, 2-3 sentences)",
  "method_zh": "怎么解决的（通俗中文，3-4句，可提关键术语）",
  "method_en": "How it solves it (plain English, 3-4 sentences)",
  "results_zh": "取得了什么效果（中文，含具体数字）",
  "results_en": "Results achieved (specific numbers if available)",
  "key_formulas": [],
  "why_it_matters_zh": "为什么值得关注（中文，2句）",
  "why_it_matters_en": "Why it matters (2 sentences)"
}}

Note: key_formulas should be an empty array [] unless the abstract explicitly contains a formula. If it does, use: [{{"latex": "formula", "explanation_zh": "解释", "explanation_en": "explanation"}}]"""

    return _call_with_retry(prompt, max_tokens=1500)


def analyze_brief_batch(papers):
    """Brief bilingual analysis for multiple papers in one call."""
    paper_list = '\n\n'.join([
        f'[{i+1}] Title: {p["title"]}\nAbstract: {p["abstract"][:350]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""Provide brief bilingual summaries for these {len(papers)} AI papers.

{paper_list}

Return a JSON array with exactly {len(papers)} items:
[
  {{"index": 1, "title_zh": "中文标题", "summary_zh": "2-3句中文简介", "summary_en": "2-3 sentence English summary"}},
  {{"index": 2, "title_zh": "中文标题", "summary_zh": "2-3句中文简介", "summary_en": "2-3 sentence English summary"}},
  {{"index": 3, "title_zh": "中文标题", "summary_zh": "2-3句中文简介", "summary_en": "2-3 sentence English summary"}},
  {{"index": 4, "title_zh": "中文标题", "summary_zh": "2-3句中文简介", "summary_en": "2-3 sentence English summary"}},
  {{"index": 5, "title_zh": "中文标题", "summary_zh": "2-3句中文简介", "summary_en": "2-3 sentence English summary"}}
]"""

    return _call_with_retry(prompt, max_tokens=1500, expect_array=True)
