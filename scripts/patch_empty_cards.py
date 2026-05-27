"""One-time patch: fill in empty cards for 2026-05-26 where API limit was hit."""
from pathlib import Path
import re

PATCHES = {
    "paper-2605_26115v1": {  # TriSplat
        "tags": ['🏗️ 3D Reconstruction · 三维重建', '🤖 Simulation · 仿真', '📷 Vision · 视觉'],
        "tag_colors": ['#60a5fa', '#10b981', '#a78bfa'],
        "title_zh": "TriSplat：仿真就绪的前向传播三维场景重建",
        "one_liner_zh": "用三角面片代替高斯球，单次推理直接输出可用于物理仿真的3D网格",
        "one_liner_en": "Replaces Gaussian blobs with triangle meshes — outputs simulation-ready 3D scenes in one forward pass, no conversion needed.",
        "analogy_zh": "就像3D打印机直接打出可以拼装的零件，而不是打出一堆沙子让你自己再成型——TriSplat直接输出物理引擎能用的三角网格。",
        "analogy_en": "Like a 3D printer that outputs finished snap-together parts instead of loose powder you'd have to mold yourself — TriSplat skips the messy conversion step.",
        "problem_zh": "现有三维重建方法输出高斯球基元，要转成物理仿真用的网格还需要昂贵的后处理，破坏了端到端承诺，无位姿场景下尤其困难。",
        "problem_en": "Existing feed-forward 3D methods output Gaussian primitives that need expensive post-processing to become physics-engine-ready meshes — especially hard without known camera poses.",
        "highlights_zh": "直接预测三角面片基元，单次前向传播输出仿真就绪网格；联合估计相机位姿；单目法线自举策略稳定训练；透明度调度逐步锐化表面。",
        "highlights_en": "Predicts oriented triangle primitives for direct mesh output; jointly estimates camera poses; mono-normal bootstrap stabilizes training; opacity scheduling sharpens surface representation.",
        "experiment_zh": "在RealEstate10K和DL3DV数据集上测试，与高斯前向传播基线对比，评估几何重建保真度和新视角渲染质量。",
        "experiment_en": "Tested on RealEstate10K and DL3DV against Gaussian feed-forward baselines, evaluating geometry faithfulness and novel-view synthesis quality.",
        "results_zh": "比高斯基线具有更高几何保真度，同时保持有竞争力的新视角渲染质量；输出可直接被物理引擎、碰撞检测器和标准渲染管线使用。",
        "results_en": "More geometry-faithful than Gaussian baselines while maintaining competitive novel-view rendering; output directly ingestible by physics engines and collision detectors without any conversion.",
        "conclusion_zh": "三角面片基元使前向传播三维重建直接具备仿真就绪能力，渲染原语本身即成为可用的仿真资产。",
        "conclusion_en": "Triangle primitives enable feed-forward 3D reconstruction that is directly usable by physics engines — the rendering primitive itself becomes a simulation-ready asset.",
        "method_zh": "给定稀疏输入图像，网络预测局部三维点图，构建几何法线后经图像条件法线头精炼，转换为稳定局部坐标系用于三角面片参数化。透明度和模糊度调度策略逐步锐化表面，最终实现直接网格提取。",
        "method_en": "Given sparse input images, the network predicts local 3D point maps, derives geometry normals, refines with an image-conditioned normal head, and converts to stable local frames for triangle parameterization. Opacity and blur scheduling progressively sharpens the surface for direct mesh extraction.",
        "why_zh": "让三维重建直接服务于机器人和具身AI仿真场景，消除网格转换瓶颈，是面向仿真应用三维感知的重要突破。",
        "why_en": "Enables 3D reconstruction to directly serve robotics, embodied AI, and physics simulation pipelines — eliminating the long-standing mesh conversion bottleneck.",
    },
    "paper-2605_23463v1": {  # StepAudio 2.5
        "tags": ['🧠 Audio-Language · 音频语言模型', '🦮 RLHF · 强化学习对齐', '💬 Speech · 语音'],
        "tag_colors": ['#818cf8', '#fb923c', '#34d399'],
        "title_zh": "StepAudio 2.5 技术报告",
        "one_liner_zh": "统一音频语言模型通过RLHF同时达到语音识别、合成和实时对话的最优水平",
        "one_liner_en": "A single audio-language model that matches specialized ASR, TTS, and realtime speech systems — all unified via RLHF-centric alignment.",
        "analogy_zh": "就像一个演员既能做同声传译（ASR）、能讲有声书（TTS）、又能即兴脱口秀（实时对话），StepAudio 2.5用一个模型干了三个专业系统的活。",
        "analogy_en": "Like an actor who can simultaneously transcribe speeches, narrate audiobooks, and improvise live conversation — one model doing the work of three specialist systems.",
        "problem_zh": "统一音频语言模型虽能同时处理语音识别、合成和实时对话，但在各任务上始终难以媲美专业系统，这一鸿沟长期未被弥合。",
        "problem_en": "Unified audio-language models promise to bring LLM reasoning to speech, but have consistently fallen short of specialized ASR, TTS, and realtime dialogue systems.",
        "highlights_zh": "以RLHF为核心对齐机制统一三个任务；ASR采用可验证多token解码；TTS通过偏好RLHF实现可控合成；实时对话用生成奖励建模降低延迟并保持人格一致性。",
        "highlights_en": "RLHF-centric alignment unifies all three tasks; ASR uses verifiable multi-token decoding; TTS uses preference-based RLHF for expressive synthesis; Realtime uses generative reward modeling for low-latency persona-consistent dialogue.",
        "experiment_zh": "在ASR、TTS和实时交互标准基准上与专业系统对比，分别评估转录准确率、合成表现力和对话延迟，验证统一模型能否全面超越专业方案。",
        "experiment_en": "Benchmarked against specialized systems on standard ASR, TTS, and Realtime tasks, measuring transcription accuracy, synthesis expressiveness, and dialogue latency.",
        "results_zh": "在ASR、TTS和实时交互三大能力上均达到最新最优（State-of-the-Art），全面媲美或超越各领域专业系统。",
        "results_en": "Achieves state-of-the-art results across all three capabilities — matching or exceeding specialized systems on ASR, TTS, and Realtime benchmarks.",
        "conclusion_zh": "单一音频语言基础模型可同时内化语音理解、生成和实时交互三种不同部署目标，终结了统一模型与专业系统间的性能权衡困境。",
        "conclusion_en": "A unified audio-language model can internalize the distinct objectives of speech understanding, generation, and live interaction — ending the tradeoff between unification and specialization.",
        "method_zh": "共享骨干网络在后训练阶段分化为三种模式：ASR分支采用可验证多token解码提升转录效率；TTS分支通过偏好RLHF和富上下文监督实现可控合成；实时分支在RLHF框架内用生成奖励建模实现低延迟人格一致对话。",
        "method_en": "A shared backbone is specialized into three modes via post-training: ASR uses verifiable multi-token decoding; TTS uses preference-based RLHF with context-rich supervision; Realtime uses generative reward modeling within RLHF for low-latency persona-consistent dialogue.",
        "why_zh": "证明统一模型路线在不牺牲专业性能前提下可大幅简化语音AI系统架构，对工业界部署具有重要意义。",
        "why_en": "Proves unified models can match specialized systems across all speech tasks, dramatically simplifying deployment and opening the door to general-purpose audio-language AI.",
    },
}


def make_tags_html(tags, colors):
    html = ''
    for tag, color in zip(tags, colors):
        html += f'<span class="tag" style="border-color:{color}33;color:{color}">{tag}</span>'
    return html


def patch_card(html: str, card_id: str, p: dict) -> str:
    card_start = html.find(f'id="{card_id}"')
    if card_start == -1:
        print(f'  Card {card_id} not found')
        return html
    card_end = html.find('</article>', card_start) + len('</article>')
    card = html[card_start:card_end]

    # tags
    card = re.sub(
        r'(<div class="tags">)(</div>)',
        r'\g<1>' + make_tags_html(p['tags'], p['tag_colors']) + r'\g<2>',
        card, count=1
    )
    # title_zh
    card = re.sub(
        r'(<span class="title-zh">)[^<]*(</span>)',
        r'\g<1>' + p['title_zh'] + r'\g<2>',
        card, count=1
    )
    # one-liner
    card = re.sub(
        r'(<div class="zh">🎯 )暂无中文摘要(</div>)',
        r'\g<1>' + p['one_liner_zh'] + r'\g<2>',
        card, count=1
    )
    card = re.sub(
        r'(<div class="en">)Analysis unavailable(</div>)',
        r'\g<1>' + p['one_liner_en'] + r'\g<2>',
        card, count=1
    )
    # analogy bubble
    analogy_html = (
        f'\n\n  <div class="analogy-bubble">'
        f'<span class="analogy-label">🗣️ 一句话比喻 · Plain-English Analogy</span>'
        f'<span class="zh">{p["analogy_zh"]}</span>'
        f'<span class="en">{p["analogy_en"]}</span>'
        f'</div>'
    )
    card = card.replace(
        '<!-- Summary Table: quick-glance overview -->',
        analogy_html + '\n\n  <!-- Summary Table: quick-glance overview -->'
    )
    # table cells (5 rows × 2 columns)
    rows = [
        (p['problem_zh'],    p['problem_en']),
        (p['highlights_zh'], p['highlights_en']),
        (p['experiment_zh'], p['experiment_en']),
        (p['results_zh'],    p['results_en']),
        (p['conclusion_zh'], p['conclusion_en']),
    ]
    for zh, en in rows:
        card = re.sub(r'(<span class="cell-zh">)(</span>)', r'\g<1>' + zh + r'\g<2>', card, count=1)
        card = re.sub(r'(<span class="cell-en">)(</span>)', r'\g<1>' + en + r'\g<2>', card, count=1)

    # method
    card = re.sub(
        r'(⚙️ Method · 方法详解</h4>\s*<div class="bilingual">\s*<span class="zh">)(</span>)(\s*<span class="en">)(</span>)',
        r'\g<1>' + p['method_zh'] + r'\g<2>\g<3>' + p['method_en'] + r'\g<4>',
        card, count=1, flags=re.DOTALL
    )
    # why it matters
    card = re.sub(
        r'(🌟 Why It Matters · 为什么重要</h4>\s*<div class="bilingual">\s*<span class="zh">)(</span>)(\s*<span class="en">)(</span>)',
        r'\g<1>' + p['why_zh'] + r'\g<2>\g<3>' + p['why_en'] + r'\g<4>',
        card, count=1, flags=re.DOTALL
    )

    return html[:card_start] + card + html[card_end:]


def main():
    path = Path('docs/index.html')
    html = path.read_text(encoding='utf-8')
    original_len = len(html)

    for card_id, patch in PATCHES.items():
        print(f'  Patching {card_id}...')
        html = patch_card(html, card_id, patch)

    path.write_text(html, encoding='utf-8')
    print(f'  Done. File grew by {len(html) - original_len:+} bytes.')


if __name__ == '__main__':
    main()
