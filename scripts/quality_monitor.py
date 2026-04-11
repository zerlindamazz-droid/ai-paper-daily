"""
Self-evolving quality monitor for AI Paper Daily.

After each run:
1. Scores each paper's analysis for completeness and depth
2. Re-analyzes any paper that fails quality checks
3. Uses Claude to generate improvement hints from this run
4. Stores history in docs/quality_history.json
5. On the NEXT run, injects accumulated hints into prompts so quality compounds

Usage:
    from quality_monitor import run_quality_check, load_adaptive_hints
    hints = load_adaptive_hints()   # inject into prompts before analysis
    ...generate report...
    run_quality_check(featured_results, brief_results, date_str)
"""
import json
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

HISTORY_FILE = Path('docs/quality_history.json')
MIN_FIELD_LEN = 15   # minimum meaningful character count


# ── Field definitions ──────────────────────────────────────────────────────────

FEATURED_REQUIRED = [
    ('problem_zh',       '待解决的问题（中文）'),
    ('highlights_zh',    '解决的亮点（中文）'),
    ('experiment_zh',    '实验内容（中文）'),
    ('results_zh',       '实验结果（中文）'),
    ('conclusion_zh',    '结论（中文）'),
    ('why_it_matters_zh','为什么重要（中文）'),
    ('method_zh',        '方法（中文）'),
    ('conclusion_en',    'Conclusion (EN)'),
    ('why_it_matters_en','Why It Matters (EN)'),
]

BRIEF_REQUIRED = [
    ('summary_zh',    '摘要（中文）'),
    ('summary_en',    'Summary (EN)'),
    ('conclusion_zh', '结论（中文）'),
    ('conclusion_en', 'Conclusion (EN)'),
]


# ── Quality checks ─────────────────────────────────────────────────────────────

def _field_issues(d, fields):
    """Return list of (field_name, label) pairs that are empty/too short."""
    return [
        (fname, label)
        for fname, label in fields
        if len(str(d.get(fname, '')).strip()) < MIN_FIELD_LEN
    ]


def check_featured(paper, analysis):
    return _field_issues(analysis, FEATURED_REQUIRED)


def check_brief(summary):
    return _field_issues(summary, BRIEF_REQUIRED)


def _quality_score(featured_results, brief_results):
    """Return overall quality score 0-100."""
    total_fields = 0
    failing_fields = 0

    for r in featured_results:
        issues = check_featured(r['paper'], r['analysis'])
        total_fields += len(FEATURED_REQUIRED)
        failing_fields += len(issues)

    for r in brief_results:
        issues = check_brief(r['summary'])
        total_fields += len(BRIEF_REQUIRED)
        failing_fields += len(issues)

    if total_fields == 0:
        return 100
    return round(100 * (1 - failing_fields / total_fields))


# ── Fix passes ────────────────────────────────────────────────────────────────

def _fix_featured(featured_results):
    from summarizer import analyze_featured
    fixed = 0
    for result in featured_results:
        issues = check_featured(result['paper'], result['analysis'])
        if not issues:
            continue
        issue_names = [f for f, _ in issues]
        print(f'    🔧 Re-analyzing featured: "{result["paper"]["title"][:55]}..."')
        print(f'       Empty fields: {issue_names}')
        try:
            new_analysis = analyze_featured(result['paper'])
            new_issues = check_featured(result['paper'], new_analysis)
            if len(new_issues) <= len(issues):
                result['analysis'].update({
                    k: new_analysis[k]
                    for k in new_analysis
                    if new_analysis.get(k, '') and k in [f for f, _ in issues]
                })
                fixed += 1
                print(f'       ✅ Fixed ({len(issues) - len(new_issues)} fields recovered)')
            else:
                print(f'       ⚠️  Re-analysis same/worse, keeping original')
        except Exception as e:
            print(f'       ❌ Re-analysis failed: {e}')
    return fixed


def _fix_brief(brief_results):
    from summarizer import analyze_single_brief
    fixed = 0
    for result in brief_results:
        issues = check_brief(result['summary'])
        if not issues:
            continue
        issue_names = [f for f, _ in issues]
        print(f'    🔧 Re-analyzing brief: "{result["paper"]["title"][:55]}..."')
        print(f'       Empty fields: {issue_names}')
        try:
            new_summary = analyze_single_brief(result['paper'])
            if isinstance(new_summary, dict):
                new_issues = check_brief(new_summary)
                if len(new_issues) <= len(issues):
                    result['summary'].update({
                        k: new_summary[k]
                        for k in new_summary
                        if new_summary.get(k, '') and k in [f for f, _ in issues]
                    })
                    fixed += 1
                    print(f'       ✅ Fixed ({len(issues) - len(new_issues)} fields recovered)')
        except Exception as e:
            print(f'       ❌ Re-analysis failed: {e}')
    return fixed


# ── Self-evolution: learn from each run ───────────────────────────────────────

def _collect_run_issues(featured_results, brief_results):
    """Collect all quality issues from this run as plain text."""
    lines = []
    for r in featured_results:
        issues = check_featured(r['paper'], r['analysis'])
        if issues:
            labels = [lbl for _, lbl in issues]
            lines.append(f'  Featured "{r["paper"]["title"][:50]}": missing {labels}')
    for r in brief_results:
        issues = check_brief(r['summary'])
        if issues:
            labels = [lbl for _, lbl in issues]
            lines.append(f'  Brief "{r["paper"]["title"][:50]}": missing {labels}')
    return lines


def _generate_improvement_hints(issue_lines, past_hints):
    """Ask Claude to turn this run's issues into actionable prompt hints."""
    if not issue_lines:
        return []

    past_text = '\n'.join(f'- {h}' for h in past_hints[-10:]) if past_hints else 'None yet.'
    issues_text = '\n'.join(issue_lines)

    prompt = f"""You are the quality controller for an AI paper digest generator.

Issues found in TODAY's run:
{issues_text}

Previously recorded improvement hints (to avoid duplicates):
{past_text}

Generate 2-4 concise, actionable improvement hints (each under 30 words) that should be injected into future analysis prompts to prevent these issues from recurring. Focus on what Claude should do differently.

Respond with a JSON array of strings only. Example:
["Always write at least 2 sentences for conclusion_zh.", "Experiment section must name specific datasets used."]"""

    resp = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=400,
        messages=[{'role': 'user', 'content': prompt}]
    )
    text = resp.content[0].text.strip()
    # Parse JSON array
    import re
    m = re.search(r'\[[\s\S]*\]', text)
    if m:
        try:
            hints = json.loads(m.group())
            return [h for h in hints if isinstance(h, str)]
        except Exception:
            pass
    return []


# ── History storage ───────────────────────────────────────────────────────────

def load_quality_history():
    """Load quality history from disk."""
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'runs': [], 'accumulated_hints': []}


def _save_quality_history(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')


def load_adaptive_hints():
    """
    Return the accumulated improvement hints to inject into analysis prompts.
    Call this at the START of main() to get the hints for this run.
    Returns a string ready to be appended to prompts, or '' if no hints yet.
    """
    history = load_quality_history()
    hints = history.get('accumulated_hints', [])
    if not hints:
        return ''
    hint_lines = '\n'.join(f'- {h}' for h in hints[-8:])  # use last 8 hints
    return f'\nLearned improvements from past runs (apply these):\n{hint_lines}'


# ── Main entry point ──────────────────────────────────────────────────────────

def run_quality_check(featured_results, brief_results, date_str):
    """
    Full quality check + fix + evolution cycle.
    Call this after generating featured/brief analysis, before rendering HTML.
    Mutates featured_results and brief_results in place.
    """
    print('\n🔍 Quality check...')

    # Score before fixes
    score_before = _quality_score(featured_results, brief_results)
    print(f'   Quality score before fix: {score_before}/100')

    # Fix pass 1
    feat_fixed = _fix_featured(featured_results)
    brief_fixed = _fix_brief(brief_results)

    # Score after fixes
    score_after = _quality_score(featured_results, brief_results)
    print(f'   Quality score after fix:  {score_after}/100  (fixed {feat_fixed}f + {brief_fixed}b)')

    # Collect remaining issues for evolution
    remaining_issues = _collect_run_issues(featured_results, brief_results)

    # Load history, generate new hints from this run's issues
    history = load_quality_history()
    past_hints = history.get('accumulated_hints', [])

    new_hints = []
    if remaining_issues:
        print(f'   🧠 Generating improvement hints from {len(remaining_issues)} remaining issues...')
        try:
            new_hints = _generate_improvement_hints(remaining_issues, past_hints)
            print(f'   💡 New hints: {new_hints}')
        except Exception as e:
            print(f'   Hint generation failed: {e}')

    # Deduplicate and accumulate hints (keep up to 20 total)
    all_hints = past_hints + [h for h in new_hints if h not in past_hints]
    all_hints = all_hints[-20:]

    # Save run record
    history['accumulated_hints'] = all_hints
    history['runs'].append({
        'date': date_str,
        'score_before': score_before,
        'score_after': score_after,
        'issues': remaining_issues,
        'new_hints': new_hints,
    })
    history['runs'] = history['runs'][-60:]  # keep last 60 runs
    _save_quality_history(history)

    if score_after >= 90:
        print('   ✅ Quality check passed')
    elif score_after >= 70:
        print('   ⚠️  Quality acceptable but some fields still weak')
    else:
        print('   ❌ Quality still low — check API tokens or abstracts')
