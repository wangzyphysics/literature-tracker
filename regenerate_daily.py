#!/usr/bin/env python3
"""
用新的过滤标准重新生成本月日报
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from focus_filter import filter_daily_focus_items, filter_focus_items, is_daily_focus, daily_focus_priority, analyze_focus
from ai_summarizer import AISummarizer
from generate_daily_pages import render_daily_html

def regenerate_daily(date_str: str):
    """重新生成指定日期的日报"""
    print(f"\n📅 处理日期: {date_str}")
    
    # 加载数据
    with open('data/index.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    
    # 筛选当日文章
    day_articles = [a for a in articles if (a.get('pub_date') or '').startswith(date_str)]
    print(f"  原始文献: {len(day_articles)} 篇")
    
    if not day_articles:
        print(f"  ⚠️ {date_str} 无数据")
        return
    
    # 应用新的过滤标准
    focused_articles, _ = filter_focus_items(day_articles)
    print(f"  目标领域: {len(focused_articles)} 篇")
    
    daily_articles, _ = filter_daily_focus_items(focused_articles, min_keep=0, max_keep=60)
    print(f"  日报入选: {len(daily_articles)} 篇")
    
    # 显示入选的文章
    for i, art in enumerate(daily_articles[:5], 1):
        signals = analyze_focus(art)
        priority = daily_focus_priority(art)
        print(f"    {i}. [{priority[0]}] {art.get('title', '')[:60]}...")
    
    if len(daily_articles) > 5:
        print(f"    ... 还有 {len(daily_articles) - 5} 篇")
    
    # 保存数据文件供AI生成摘要
    os.makedirs('ai_prompts', exist_ok=True)
    data_file = {
        'date': date_str,
        'raw_count': len(day_articles),
        'focused_count': len(focused_articles),
        'daily_count': len(daily_articles),
        'articles': daily_articles
    }
    
    with open(f'ai_prompts/{date_str}_data.json', 'w', encoding='utf-8') as f:
        json.dump(data_file, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ 数据文件已保存: ai_prompts/{date_str}_data.json")

if __name__ == '__main__':
    # 重新生成4月1日到4月10日的日报
    dates = [f'2026-04-{day:02d}' for day in range(1, 11)]
    
    print("=" * 50)
    print("4月日报重新筛选（新过滤标准）")
    print("=" * 50)
    
    for date_str in dates:
        regenerate_daily(date_str)
    
    print("\n" + "=" * 50)
    print("筛选完成！")
    print("=" * 50)
