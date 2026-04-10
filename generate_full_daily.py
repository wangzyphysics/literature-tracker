#!/usr/bin/env python3
"""
直接调用AI API生成摘要并立即生成HTML
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_summarizer import AISummarizer
from generate_daily_pages import render_daily_html, ensure_dirs

def generate_full_daily(date_str: str):
    """生成完整日报（AI摘要 + HTML）"""
    print(f"\n{'='*50}")
    print(f"📅 生成 {date_str} 的完整日报")
    print(f"{'='*50}")
    
    # 加载数据
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    if not articles:
        print(f"⚠️ {date_str} 无文章")
        return False
    
    print(f"📊 文章数: {len(articles)}")
    
    # 调用AI
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ 未设置OPENROUTER_API_KEY")
        return False
    
    summarizer = AISummarizer('openrouter', api_key)
    
    print("🤖 调用AI生成摘要...")
    try:
        summary = summarizer.generate_daily_summary(articles, date_str)
        print(f"✅ AI摘要完成 (generated_by: {summary.get('generated_by', 'unknown')})")
    except Exception as e:
        print(f"❌ AI摘要失败: {e}")
        # 使用fallback
        summary = {
            'date': date_str,
            'total': len(articles),
            'overview': f"今日共收录{len(articles)}篇文献。",
            'trends': '',
            'full_list': [],
            'ml_highlights': [],
            'ferro_highlights': [],
            'generated_by': 'fallback'
        }
        for art in articles:
            summary['full_list'].append({
                'title_en': art.get('title'),
                'title_zh': art.get('title_zh') or '待翻译',
                'abstract_zh': '',
                'summary': '',
                'link': art.get('link'),
                'journal': art.get('journal', ''),
                'authors': art.get('authors', []),
                'pub_date': art.get('pub_date', ''),
            })
    
    # 检查是否有摘要
    has_abstract = any(a.get('abstract_zh') for a in summary.get('full_list', []))
    has_summary = any(a.get('summary') for a in summary.get('full_list', []))
    print(f"📄 含中文摘要: {has_abstract}, 含一句话总结: {has_summary}")
    
    # 保存AI响应
    os.makedirs('ai_responses', exist_ok=True)
    with open(f'ai_responses/{date_str}_response.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成HTML
    ensure_dirs()
    html = render_daily_html(date_str, summary)
    with open(f'docs/daily/{date_str}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已生成: docs/daily/{date_str}.html")
    
    return True

if __name__ == '__main__':
    dates = ['2026-04-02', '2026-04-03', '2026-04-06', '2026-04-08']
    
    for date in dates:
        generate_full_daily(date)
        time.sleep(3)
    
    print(f"\n{'='*50}")
    print("全部完成！")
    print(f"{'='*50}")
