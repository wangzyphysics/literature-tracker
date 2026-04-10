#!/usr/bin/env python3
"""手动生成4月日报HTML"""

import os
import json
import html
from datetime import datetime
from urllib.parse import urlparse

def safe_text(value):
    if value is None:
        return ""
    return html.escape(str(value), quote=True)

def safe_url(value):
    url = (value or "").strip()
    if not url:
        return "#"
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return "#"
    except Exception:
        return "#"
    return html.escape(url, quote=True)

def render_daily_html(date_str, summary_data, articles):
    """渲染日报HTML"""
    
    overview = summary_data.get('overview', '')
    trends = summary_data.get('trends', '')
    summaries = summary_data.get('full_list', [])
    
    # 构建文献卡片
    article_cards = []
    for i, article in enumerate(articles[:40]):
        title = article.get('title', '') or article.get('title_en', '')
        title_zh = article.get('title_zh', '')
        journal = article.get('journal', '')
        link = article.get('link', '')
        
        # 获取对应的summary
        summary_obj = summaries[i] if i < len(summaries) else {}
        summary_text = summary_obj.get('summary', '') if isinstance(summary_obj, dict) else ''
        
        card = f"""
<div class="daily-paper-card">
  <div class="daily-paper-number">{i+1}</div>
  <div class="daily-paper-body">
    <div class="daily-paper-title-zh">{safe_text(title_zh) or safe_text(title)}</div>
    <div class="daily-paper-title-en">{safe_text(title)}</div>
    <div class="daily-paper-meta">
      <span class="daily-chip daily-chip-topic">{safe_text(journal)}</span>
    </div>
    <div class="daily-paper-summary">{safe_text(summary_text)}</div>
    <div class="daily-paper-actions">
      <a href="{safe_url(link)}" target="_blank" class="daily-news-link">查看原文 →</a>
    </div>
  </div>
</div>"""
        article_cards.append(card)
    
    articles_html = '\n'.join(article_cards)
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>{date_str} 文献日报 - 文献追踪系统</title>
<link href="../style.css" rel="stylesheet"/>
<style>
body {{ background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(248, 250, 252, 0.85) 220px), var(--bg-primary); overflow-x: hidden; }}
.daily-shell {{ max-width: 1260px; margin: 0 auto; padding: 28px 20px 48px; }}
.daily-article {{ background: rgba(255,255,255,0.76); border: 1px solid rgba(148,163,184,0.28); border-radius: 28px; box-shadow: var(--shadow-lg); backdrop-filter: blur(14px); padding: 32px; }}
.daily-hero {{ padding-bottom: 18px; border-bottom: 1px solid var(--border-color); }}
.daily-title {{ margin: 18px 0 10px; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.15; letter-spacing: -0.03em; }}
.daily-subtitle {{ font-size: 1.02rem; color: var(--text-secondary); margin-bottom: 18px; line-height: 1.8; }}
.daily-summary-card {{ padding: 18px 20px; border-radius: 20px; background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(244,247,255,0.96)); border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); line-height: 1.85; margin: 20px 0; }}
.daily-paper-card {{ display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; padding: 20px; border-radius: 22px; background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(249,250,251,0.92)); border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); align-items: flex-start; margin-top: 16px; }}
.daily-paper-number {{ width: 42px; height: 42px; display: inline-flex; align-items: center; justify-content: center; border-radius: 14px; font-weight: 800; color: white; background: var(--gradient-accent); box-shadow: var(--shadow-sm); flex-shrink: 0; }}
.daily-paper-title-zh {{ font-size: 1.12rem; font-weight: 700; line-height: 1.5; margin-bottom: 6px; }}
.daily-paper-title-en {{ color: var(--text-secondary); font-size: 0.96rem; line-height: 1.6; }}
.daily-paper-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
.daily-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 999px; font-size: 0.88rem; color: var(--text-secondary); background: rgba(99,102,241,0.08); }}
.daily-paper-summary {{ color: var(--text-primary); line-height: 1.8; margin-top: 10px; }}
.daily-news-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--accent-primary); text-decoration: none; font-weight: 600; margin-top: 10px; }}
.back-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--accent-primary); text-decoration: none; font-weight: 600; margin-bottom: 20px; }}
</style>
</head>
<body>
<div class="daily-shell">
  <a href="../index.html" class="back-link">← 返回首页</a>
  <article class="daily-article">
    <header class="daily-hero">
      <div style="color: var(--accent-primary); font-weight: 700; letter-spacing: 0.04em;">文献日报</div>
      <h1 class="daily-title">{date_str}</h1>
      <p class="daily-subtitle">今日收录 {len(articles)} 篇 AI×Science 文献</p>
    </header>
    
    <div class="daily-summary-card">
      <h3 style="margin-top: 0; color: var(--accent-primary);">📊 今日概览</h3>
      <p>{safe_text(overview)}</p>
      <h4 style="color: var(--accent-primary); margin-top: 16px;">🔥 研究热点</h4>
      <p>{safe_text(trends).replace(chr(10), '<br/>')}</p>
    </div>
    
    <h3 style="margin-top: 28px; margin-bottom: 16px;">文献详情</h3>
    {articles_html}
    
  </article>
</div>
</body>
</html>"""
    
    return html_content

# 生成4月日报
for date_str in ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-04', '2026-04-07', '2026-04-08', '2026-04-09']:
    # 加载数据
    with open(f'ai_prompts/{date_str}_data.json') as f:
        data = json.load(f)
    
    # 加载AI响应
    resp_path = f'ai_responses/{date_str}_response.json'
    if os.path.exists(resp_path):
        with open(resp_path) as f:
            summary = json.load(f)
    else:
        summary = {'overview': '今日文献摘要', 'trends': '', 'full_list': []}
    
    articles = data.get('articles', [])
    
    # 生成HTML
    html_content = render_daily_html(date_str, summary, articles)
    
    # 保存
    out_path = f'docs/daily/{date_str}.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f'✅ {date_str}: {len(articles)}篇文献已生成')

print('🎉 全部完成！')
