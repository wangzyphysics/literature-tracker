#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate daily AI-filtered summary pages for GitHub Pages.

- Input: data/ai_relevant.json (created by run_optimized_sync)
- Output:
  - docs/daily/YYYY-MM-DD.html
  - docs/daily/summaries.json
"""
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict

from ai_summarizer import AISummarizer


def beijing_today() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime('%Y-%m-%d')


def load_relevant(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def ensure_dirs():
    os.makedirs('docs/daily', exist_ok=True)


def render_daily_html(date_str: str, summary: Dict) -> str:
    items_html = "".join([
        f"""
        <div class=\"article-card\">
            <div class=\"article-header\">
                <div class=\"article-title-en\">{item.get('title_en','')}</div>
                <div class=\"article-title-zh\">{item.get('title_zh','')}</div>
            </div>
            <div class=\"article-summary\">{item.get('summary','')}</div>
            <div class=\"article-link\"><a href=\"{item.get('link','')}\" target=\"_blank\">🔗 原文链接</a></div>
        </div>
        """
        for item in summary.get('summaries', [])
    ])

    overview = summary.get('overview', '')
    trends = summary.get('trends', '')

    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{date_str} 每日摘要 - 文献追踪系统</title>
  <link rel=\"stylesheet\" href=\"../style.css\" />
  <style>
    .daily-container {{ max-width: 960px; margin: 0 auto; padding: 20px; }}
    .section {{ margin: 18px 0; padding: 16px; background: var(--bg-card); border-radius: 12px; box-shadow: var(--shadow-md); }}
    .article-card {{ margin: 14px 0; padding: 16px; background: var(--bg-card); border-radius: 12px; box-shadow: var(--shadow-sm); border: 1px solid var(--border-color); }}
    .article-title-en {{ font-weight: 600; margin-bottom: 6px; }}
    .article-title-zh {{ color: var(--text-secondary); margin-bottom: 8px; }}
    .article-summary {{ color: var(--text-primary); }}
    .article-link a {{ color: var(--accent-primary); text-decoration: none; }}
    .article-link a:hover {{ text-decoration: underline; }}
    .back-link {{ display: inline-block; margin-bottom: 14px; color: var(--accent-primary); text-decoration: none; }}
    .back-link:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class=\"daily-container\">
    <a href=\"../index.html\" class=\"back-link\">← 返回主页</a>
    <h1>📰 {date_str} 每日文献摘要</h1>
    <div class=\"section\"><strong>总览：</strong> {overview}</div>
    <div class=\"section\"><strong>热点：</strong> {trends}</div>
    <div class=\"section\">
      <h2>相关文献（AI筛选）</h2>
      {items_html if items_html else '<p>今日无相关文献</p>'}
    </div>
  </div>
</body>
</html>
"""


def update_index(date_str: str, total: int):
    index_path = os.path.join('docs/daily', 'summaries.json')
    data = {"summaries": []}
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"summaries": []}
    summaries = [s for s in data.get('summaries', []) if s.get('date') != date_str]
    summaries.insert(0, {"date": date_str, "file": f"{date_str}.html", "total": total})
    data["summaries"] = summaries[:120]
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=None, help='YYYY-MM-DD (Beijing)')
    args = parser.parse_args()

    date_str = args.date or beijing_today()
    ensure_dirs()

    relevant = load_relevant('data/ai_relevant.json')
    day_articles = [a for a in relevant if (a.get('pub_date') or '').startswith(date_str)]

    if not day_articles:
        # still generate empty page so index shows date
        summary = {"date": date_str, "total": 0, "overview": "今日无相关文献", "trends": "", "summaries": []}
    else:
        api_key = os.environ.get('AI_API_KEY') or os.environ.get('GEMINI_API_KEY')
        provider = os.environ.get('AI_PROVIDER', 'gemini')
        summarizer = AISummarizer(provider, api_key)
        summary = summarizer.generate_daily_summary(day_articles, date_str)

    html = render_daily_html(date_str, summary)
    out_path = os.path.join('docs/daily', f'{date_str}.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    update_index(date_str, summary.get('total', len(day_articles)))
    print(f"✅ Daily page generated: {out_path}")


if __name__ == '__main__':
    main()
