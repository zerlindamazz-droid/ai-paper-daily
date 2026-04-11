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
    """Select and rank papers using tool_use for guaranteed structured output."""
    paper_list = '\n\n'.join([
        f'[{i+1}] ID: {p["id"]}\nTitle: {p["title"]}\nCategories: {", ".join(p["categories"][:3])}\nAbstract: {p["abstract"][:400]}'
        for i, p in enumerate(papers)
    ])

    tool = {
        "name": "paper_selection",
        "description": "Select and rank the most important AI training papers",
        "input_schema": {
            "type": "object",
            "properties": {
                "featured": {
                    "type": "array",
                    "description": "Top 3 featured papers",
                    "minItems": 3, "maxItems": 3,
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer"},
                            "paper_index": {"type": "integer", "description": "1-based index from paper list"},
                            "importance_score": {"type": "integer", "minimum": 1, "maximum": 10},
                            "topic_tags_en": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
                            "topic_tags_zh": {"type": "array", "items": {"type": "string"}, "maxItems": 4}
                        },
                        "required": ["rank", "paper_index", "importance_score", "topic_tags_en", "topic_tags_zh"]
                    }
                },
                "brief": {
                    "type": "array",
                    "description": "Next 5 brief mention papers",
                    "minItems": 5, "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "paper_index": {"type": "integer"},
                            "topic_tags_en": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                            "topic_tags_zh": {"type": "array", "items": {"type": "string"}, "maxItems": 3}
                        },
                        "required": ["paper_index", "topic_tags_en", "topic_tags_zh"]
                    }
                }
            },
            "required": ["featured", "brief"]
        }
    }

    prompt = f"""You are an expert AI researcher curating a high-quality daily digest from the past 30 days of arXiv papers.

From these {len(papers)} candidate papers (already filtered to exclude previously sent ones), select the BEST for today's digest:
- Top 3 FEATURED: most significant, novel, and impactful AI model training contributions
- Next 5 BRIEF: broader coverage of important but slightly less groundbreaking work

Quality criteria (prioritize papers that):
- Introduce a genuinely new idea or method (not incremental)
- Show strong empirical results with specific numbers
- Come from reputable labs or have strong methodology
- Would be widely cited or discussed in the AI community

Diversity: cover LLMs, fine-tuning/PEFT, training efficiency, architecture, RLHF/alignment, multimodal, diffusion, optimization, distributed training, VLA/robotics/embodied AI.

Papers:
{paper_list}

Call paper_selection with your choices."""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=1000,
        tools=[tool],
        tool_choice={"type": "any"},
        messages=[{'role': 'user', 'content': prompt}]
    )

    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'paper_selection':
            return block.input

    raise ValueError('No tool_use response from select_and_rank')


def analyze_featured(paper, adaptive_hints=''):
    """Deep bilingual analysis using tool_use for guaranteed JSON output.
    adaptive_hints: string from quality_monitor.load_adaptive_hints() injected into prompt.
    """
    tool = {
        "name": "paper_analysis",
        "description": "Submit bilingual analysis of an AI paper",
        "input_schema": {
            "type": "object",
            "properties": {
                "importance_score": {"type": "integer", "minimum": 1, "maximum": 10,
                                     "description": "Impact score 1-10 for the AI research community"},
                "topic_tags_en": {"type": "array", "items": {"type": "string"}, "maxItems": 4,
                                  "description": "Up to 4 topic tags in English (e.g. RL, Robotics, LLM, Fine-tuning)"},
                "topic_tags_zh": {"type": "array", "items": {"type": "string"}, "maxItems": 4,
                                  "description": "Same tags in Chinese"},
                "title_zh": {"type": "string", "description": "Chinese translation of the paper title"},
                "one_liner_zh": {"type": "string", "description": "One-sentence core contribution in Chinese, under 20 characters"},
                "one_liner_en": {"type": "string", "description": "One-sentence core contribution in English, under 20 words"},
                "problem_zh": {"type": "string", "description": "待解决的问题：Plain Chinese, 2-3 sentences, accessible to non-experts"},
                "problem_en": {"type": "string", "description": "Problem being solved: Plain English, 2-3 sentences"},
                "highlights_zh": {"type": "string", "description": "解决的亮点：Core innovations and key contributions in Chinese, 2-3 bullet-point style sentences"},
                "highlights_en": {"type": "string", "description": "Key highlights and innovations in English, 2-3 concise sentences"},
                "method_zh": {"type": "string", "description": "How does it solve the problem? Plain Chinese, 3-4 sentences"},
                "method_en": {"type": "string", "description": "How does it solve the problem? Plain English, 3-4 sentences"},
                "experiment_zh": {"type": "string", "description": "实验内容：本文做了哪些实验？用了什么数据集、基线模型、评估指标？通俗说明，2-3句"},
                "experiment_en": {"type": "string", "description": "What experiments were conducted? Datasets, baselines, evaluation metrics, experimental setup. 2-3 plain sentences."},
                "results_zh": {"type": "string", "description": "实验结果：具体的数字指标、性能提升、benchmark排名，要有具体数字"},
                "results_en": {"type": "string", "description": "Experimental results: specific numbers, percentage improvements, benchmark rankings"},
                "conclusion_zh": {"type": "string", "description": "结论：本文最终证明了什么？对领域的贡献和意义是什么？1-2句话总结"},
                "conclusion_en": {"type": "string", "description": "Conclusion: What did this paper ultimately prove? Key contribution and impact on the field. 1-2 sentences."},
                "why_it_matters_zh": {"type": "string", "description": "Why does this paper matter to the AI field? Chinese, 2 sentences"},
                "why_it_matters_en": {"type": "string", "description": "Why does this paper matter? 2 sentences"},
                "key_formulas": {
                    "type": "array",
                    "description": "Key formulas from the abstract, empty array if none",
                    "items": {
                        "type": "object",
                        "properties": {
                            "latex": {"type": "string", "description": "LaTeX formula string"},
                            "explanation_zh": {"type": "string", "description": "Plain Chinese explanation"},
                            "explanation_en": {"type": "string", "description": "Plain English explanation"}
                        },
                        "required": ["latex", "explanation_zh", "explanation_en"]
                    }
                }
            },
            "required": ["importance_score", "topic_tags_en", "topic_tags_zh",
                         "title_zh", "one_liner_zh", "one_liner_en",
                         "problem_zh", "problem_en", "highlights_zh", "highlights_en",
                         "method_zh", "method_en",
                         "experiment_zh", "experiment_en",
                         "results_zh", "results_en",
                         "conclusion_zh", "conclusion_en",
                         "why_it_matters_zh", "why_it_matters_en", "key_formulas"]
        }
    }

    prompt = f"""Analyze this AI paper for a bilingual daily digest targeting ML/RL/Robotics researchers. Use plain, accessible language.

Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Abstract: {paper['abstract']}

Call the paper_analysis tool with your analysis. ALL fields are REQUIRED — do not leave any field empty.

Field guidance:
- highlights_zh/en: KEY innovations (what's novel/clever about the approach), bullet-point style
- experiment_zh/en: what experiments were done — datasets, baselines, evaluation setup (NOT the numbers)
- results_zh/en: specific numbers, benchmark names, % improvements — must have concrete figures
- conclusion_zh/en: 【必须填写】what was ultimately proven; the paper's final contribution in 1-2 sentences
- why_it_matters_zh/en: 【必须填写】why this matters to the AI/ML field; broader impact in 2 sentences

Both Chinese and English for EVERY field must be complete. Conclusion and why_it_matters are especially important.{adaptive_hints}"""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=4000,
        tools=[tool],
        tool_choice={"type": "any"},
        messages=[{'role': 'user', 'content': prompt}]
    )

    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'paper_analysis':
            return block.input

    raise ValueError('No tool_use response received')


def select_brief(papers):
    """Select 5 brief papers focused on ML / RL / Robotics using tool_use."""
    tool = {
        "name": "brief_selection",
        "description": "Select 5 recommended papers focused on ML, RL, and Robotics",
        "input_schema": {
            "type": "object",
            "properties": {
                "papers": {
                    "type": "array",
                    "description": "Exactly 5 selected papers",
                    "minItems": 5, "maxItems": 5,
                    "items": {
                        "type": "object",
                        "properties": {
                            "paper_index": {"type": "integer", "description": "1-based index from the list"},
                            "topic_tags_en": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                            "topic_tags_zh": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                        },
                        "required": ["paper_index", "topic_tags_en", "topic_tags_zh"]
                    }
                }
            },
            "required": ["papers"]
        }
    }

    paper_list = '\n\n'.join([
        f'[{i+1}] ID: {p["id"]}\nTitle: {p["title"]}\nCategories: {", ".join(p["categories"][:3])}\nAbstract: {p["abstract"][:300]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""You are curating a daily AI digest. From these {len(papers)} candidate papers, select exactly 5 for the "More Papers" recommendation section.

PRIORITY: Papers related to Machine Learning, Reinforcement Learning (RL), or Robotics/Embodied AI.
- Prefer papers from cs.LG, cs.RO, cs.AI categories
- Prefer novel methods, strong results, or practical impact
- Cover diverse sub-topics (don't pick 5 similar papers)

Papers:
{paper_list}

Call brief_selection with your 5 chosen papers."""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=600,
        tools=[tool],
        tool_choice={"type": "any"},
        messages=[{'role': 'user', 'content': prompt}]
    )

    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'brief_selection':
            return block.input['papers']

    raise ValueError('No tool_use response from select_brief')


def analyze_brief_batch(papers):
    """Brief bilingual analysis using tool_use for guaranteed structured output."""
    tool = {
        "name": "brief_summaries",
        "description": "Submit brief bilingual summaries for multiple AI papers",
        "input_schema": {
            "type": "object",
            "properties": {
                "summaries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "index": {"type": "integer"},
                            "title_zh": {"type": "string", "description": "Chinese title translation"},
                            "summary_zh": {"type": "string", "description": "2-3 sentence Chinese summary, plain language"},
                            "summary_en": {"type": "string", "description": "2-3 sentence English summary, plain language"},
                            "conclusion_zh": {"type": "string", "description": "一句话结论：本文最重要的takeaway或意义，15字以内"},
                            "conclusion_en": {"type": "string", "description": "One-sentence conclusion: the most important takeaway, under 20 words"},
                        },
                        "required": ["index", "title_zh", "summary_zh", "summary_en", "conclusion_zh", "conclusion_en"]
                    }
                }
            },
            "required": ["summaries"]
        }
    }

    paper_list = '\n\n'.join([
        f'[{i+1}] Title: {p["title"]}\nAbstract: {p["abstract"][:350]}'
        for i, p in enumerate(papers)
    ])

    prompt = f"""Provide brief bilingual summaries for these {len(papers)} AI papers. Be plain and accessible.

{paper_list}

ALL fields are REQUIRED for every paper — do not leave any field empty:
- title_zh: Chinese translation of the title
- summary_zh: 2-3 plain Chinese sentences explaining what the paper does and how
- summary_en: 2-3 plain English sentences (same content)
- conclusion_zh: 【必须填写】ONE sentence — the most important takeaway in Chinese (10-20 chars)
- conclusion_en: 【必须填写】ONE sentence — the most important takeaway in English

Call brief_summaries with complete summaries for all {len(papers)} papers."""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=3500,
        tools=[tool],
        tool_choice={"type": "any"},
        messages=[{'role': 'user', 'content': prompt}]
    )

    for block in resp.content:
        if block.type == 'tool_use' and block.name == 'brief_summaries':
            return block.input['summaries']

    raise ValueError('No tool_use response from analyze_brief_batch')


def analyze_single_brief(paper):
    """Analyze one brief paper individually (used by quality monitor for re-analysis)."""
    results = analyze_brief_batch([paper])
    return results[0] if results else {}
