"""Send daily AI paper digest email via Gmail SMTP."""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from datetime import datetime


SENDER = 'zerlindamazz@gmail.com'
RECIPIENT = 'zerlindamazz@gmail.com'
SITE_URL = 'https://zerlindamazz-droid.github.io/ai-paper-daily/'


def build_email_html(date_str, featured_papers, brief_papers):
    """Build a lightweight email-friendly HTML (no base64 images, just links)."""

    # Featured paper cards for email
    featured_html = ''
    rank_emojis = ['🥇', '🥈', '🥉', '4️⃣']
    rank_colors = ['#5b5ef4', '#06b6d4', '#f59e0b', '#10b981']

    for i, result in enumerate(featured_papers):
        paper = result['paper']
        analysis = result['analysis']
        color = rank_colors[i] if i < len(rank_colors) else '#8888aa'
        emoji = rank_emojis[i] if i < len(rank_emojis) else f'#{i+1}'
        tags = ' · '.join(paper.get('topic_tags_zh', [])[:3])
        score = paper.get('importance_score', 8)

        def _cell(label_zh, label_en, val_zh, val_en, c=color):
            return f"""
      <tr>
        <td style="padding:10px 12px;border-top:1px solid #e2e4f0;background:#f8f9ff;
                   width:90px;font-size:11px;font-weight:800;color:{c};white-space:nowrap;
                   vertical-align:top">{label_zh}</td>
        <td style="padding:10px 12px;border-top:1px solid #e2e4f0;font-size:14px;
                   color:#1a1a2e;line-height:1.65;vertical-align:top">
          <span style="display:block">{val_zh}</span>
          <span style="display:block;font-size:12px;color:#8888aa;margin-top:3px">{val_en}</span>
        </td>
      </tr>"""

        featured_html += f"""
<div style="background:#ffffff;border:1.5px solid #e2e4f0;border-radius:16px;
            margin-bottom:20px;overflow:hidden;box-shadow:0 2px 12px rgba(91,94,244,0.07)">
  <div style="height:5px;background:linear-gradient(to right,{color},{color}88)"></div>
  <div style="padding:20px 24px">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <span style="font-size:22px">{emoji}</span>
      <span style="background:#eef0ff;color:{color};font-size:12px;font-weight:700;
                   padding:3px 10px;border-radius:100px;border:1px solid {color}33">
        ★ {score}/10
      </span>
      <span style="color:#8888aa;font-size:13px">{tags}</span>
    </div>
    <div style="font-size:18px;font-weight:800;color:#1a1a2e;line-height:1.4;margin-bottom:4px">
      {paper['title']}
    </div>
    <div style="font-size:16px;font-weight:600;color:{color};margin-bottom:6px">
      {analysis.get('title_zh', '')}
    </div>
    <div style="font-size:13px;color:#8888aa;margin-bottom:14px">
      🧑‍🔬 {', '.join(paper['authors'][:4])}{'  et al.' if len(paper['authors'])>4 else ''}
    </div>

    <div style="background:#eef0ff;border-left:4px solid {color};
                border-radius:0 10px 10px 0;padding:12px 16px;margin-bottom:16px">
      <div style="font-size:17px;font-weight:700;color:#1a1a2e;margin-bottom:4px">
        🎯 {analysis.get('one_liner_zh', '')}
      </div>
      <div style="font-size:15px;color:#555577">
        {analysis.get('one_liner_en', '')}
      </div>
    </div>

    <!-- Summary table -->
    <table style="width:100%;border-collapse:collapse;border:1.5px solid #e2e4f0;
                  border-radius:10px;overflow:hidden">
      <thead>
        <tr style="background:#eef0ff">
          <th style="padding:8px 12px;font-size:11px;font-weight:800;color:{color};
                     text-align:left;letter-spacing:0.06em;text-transform:uppercase;
                     width:90px">维度</th>
          <th style="padding:8px 12px;font-size:11px;font-weight:800;color:{color};
                     text-align:left;letter-spacing:0.06em;text-transform:uppercase">
            中文 / English</th>
        </tr>
      </thead>
      <tbody>
        {_cell('❓ 待解决<br>的问题', 'Problem', analysis.get('problem_zh',''), analysis.get('problem_en',''))}
        {_cell('💡 解决<br>的亮点', 'Highlights', analysis.get('highlights_zh',''), analysis.get('highlights_en',''))}
        {_cell('🧪 实验<br>内容', 'Experiment', analysis.get('experiment_zh',''), analysis.get('experiment_en',''))}
        {_cell('📊 实验<br>结果', 'Results', analysis.get('results_zh',''), analysis.get('results_en',''))}
        {_cell('🏁 结论', 'Conclusion', analysis.get('conclusion_zh',''), analysis.get('conclusion_en',''))}
        <tr>
          <td style="padding:10px 12px;border-top:1px solid #e2e4f0;background:#f8f9ff;
                     font-size:11px;font-weight:800;color:{color};white-space:nowrap;
                     vertical-align:top">🔗 论文<br>链接</td>
          <td style="padding:10px 12px;border-top:1px solid #e2e4f0;vertical-align:top">
            <a href="{paper['arxiv_url']}" style="color:{color};font-weight:700;
               text-decoration:none;font-size:14px">📄 arXiv: {paper['id']}</a>
            &nbsp;·&nbsp;
            <a href="{paper['pdf_url']}" style="color:#555577;font-size:13px;
               text-decoration:none">📥 PDF</a>
          </td>
        </tr>
      </tbody>
    </table>

    <div style="margin-top:14px;text-align:right">
      <a href="{SITE_URL}" style="color:#5b5ef4;font-size:13px;
         text-decoration:none;font-weight:600">🌐 查看图文版（含论文截图）→</a>
    </div>
  </div>
</div>"""

    # Brief paper rows
    brief_html = ''
    for result in brief_papers:
        paper = result['paper']
        summary = result['summary'] if isinstance(result['summary'], dict) else {}
        tags = ' · '.join(paper.get('topic_tags_zh', [])[:2])
        brief_html += f"""
<div style="background:#ffffff;border:1.5px solid #e2e4f0;border-radius:12px;
            padding:16px 20px;margin-bottom:12px">
  <div style="font-size:16px;font-weight:800;color:#1a1a2e;margin-bottom:3px">
    {paper['title']}
  </div>
  <div style="font-size:15px;font-weight:600;color:#5b5ef4;margin-bottom:8px">
    {summary.get('title_zh', '')}
    <span style="font-size:12px;color:#8888aa;font-weight:400;margin-left:8px">{tags}</span>
  </div>
  <div style="font-size:15px;color:#1a1a2e;line-height:1.65;margin-bottom:4px">
    {summary.get('summary_zh', '')}
  </div>
  <div style="font-size:14px;color:#8888aa;line-height:1.6;margin-bottom:8px">
    {summary.get('summary_en', '')}
  </div>
  <div style="background:linear-gradient(135deg,#eef0ff,#f5f0ff);
              border-left:3px solid #5b5ef4;border-radius:0 8px 8px 0;
              padding:8px 12px;margin-bottom:10px;font-size:14px">
    <span style="color:#1a1a2e;font-weight:600">🏁 结论：{summary.get('conclusion_zh', '')}</span>
    <span style="display:block;color:#8888aa;font-size:13px;margin-top:2px">
      {summary.get('conclusion_en', '')}
    </span>
  </div>
  <a href="{paper['arxiv_url']}" style="color:#5b5ef4;font-size:13px;font-weight:600;
     text-decoration:none">📄 {paper['id']} →</a>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI 论文日报 · {date_str}</title>
</head>
<body style="margin:0;padding:0;background:#f5f6fa;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif">

<div style="max-width:700px;margin:0 auto;padding:24px 16px">

  <!-- HEADER -->
  <div style="background:linear-gradient(135deg,#5b5ef4,#a855f7);border-radius:20px;
              padding:32px 32px 28px;text-align:center;margin-bottom:24px">
    <div style="font-size:13px;font-weight:700;letter-spacing:0.1em;color:rgba(255,255,255,0.8);
                text-transform:uppercase;margin-bottom:12px">
      🔬 AI Model Training · Daily Digest
    </div>
    <div style="font-size:32px;font-weight:900;color:white;letter-spacing:-0.03em;margin-bottom:6px">
      AI 模型训练论文日报
    </div>
    <div style="font-size:16px;color:rgba(255,255,255,0.85);margin-bottom:16px">
      AI Training Papers Daily
    </div>
    <div style="display:inline-block;background:rgba(255,255,255,0.2);border-radius:100px;
                padding:6px 20px;font-size:14px;color:white;font-weight:600">
      📅 {date_str} · {len(featured_papers) + len(brief_papers)} papers
    </div>
  </div>

  <!-- VIEW ONLINE BANNER -->
  <div style="background:#eef0ff;border:1.5px solid rgba(91,94,244,0.2);border-radius:12px;
              padding:14px 20px;text-align:center;margin-bottom:28px">
    <span style="font-size:15px;color:#555577">📖 查看图文完整版（含论文截图）→ </span>
    <a href="{SITE_URL}" style="color:#5b5ef4;font-weight:700;font-size:15px;
       text-decoration:none">{SITE_URL}</a>
  </div>

  <!-- FEATURED -->
  <div style="font-size:20px;font-weight:800;color:#1a1a2e;margin-bottom:16px;
              letter-spacing:-0.02em">
    🔥 今日精选 Today's Highlights
  </div>
  {featured_html}

  <!-- BRIEF -->
  <div style="font-size:20px;font-weight:800;color:#1a1a2e;margin:28px 0 16px;
              letter-spacing:-0.02em">
    📚 更多论文 More Papers
  </div>
  {brief_html}

  <!-- FOOTER -->
  <div style="text-align:center;padding:24px 0 8px;color:#8888aa;font-size:13px;
              border-top:1px solid #e2e4f0;margin-top:16px">
    <p>由 <strong>arXiv</strong> + <strong>Claude AI</strong> 自动生成 · 每天洛杉矶时间早上 6:00 发送</p>
    <p style="margin-top:6px">
      <a href="{SITE_URL}" style="color:#5b5ef4;text-decoration:none">🌐 在线阅读</a>
      &nbsp;·&nbsp;
      <a href="{SITE_URL}archive/index.html" style="color:#5b5ef4;text-decoration:none">📁 历史存档</a>
    </p>
  </div>

</div>
</body>
</html>"""


def send_email(date_str, featured_papers, brief_papers, pdf_path=None):
    app_password = os.environ.get('GMAIL_APP_PASSWORD', '')
    if not app_password:
        print('  ⚠️  GMAIL_APP_PASSWORD not set, skipping email')
        return

    html = build_email_html(date_str, featured_papers, brief_papers)

    # Use 'mixed' to support both HTML body + PDF attachment
    msg = MIMEMultipart('mixed')
    msg['Subject'] = f'⚡ AI 论文日报 {date_str} · {len(featured_papers)+len(brief_papers)} papers'
    msg['From'] = SENDER
    msg['To'] = RECIPIENT

    # HTML body
    body = MIMEMultipart('alternative')
    body.attach(MIMEText(html, 'html', 'utf-8'))
    msg.attach(body)

    # PDF attachment
    if pdf_path and Path(pdf_path).exists():
        with open(pdf_path, 'rb') as f:
            pdf_data = f.read()
        pdf_part = MIMEApplication(pdf_data, _subtype='pdf')
        filename = f'AI论文日报_{date_str}.pdf'
        pdf_part.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.attach(pdf_part)
        size_kb = len(pdf_data) // 1024
        print(f'  PDF attached: {filename} ({size_kb} KB)')

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER, app_password)
            server.sendmail(SENDER, RECIPIENT, msg.as_string())
        print(f'  ✅ Email sent to {RECIPIENT}')
    except Exception as e:
        print(f'  ❌ Email failed: {e}')
        raise
