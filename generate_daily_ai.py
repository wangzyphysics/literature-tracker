#!/usr/bin/env python3
"""
用AI生成指定日期的日报摘要和HTML
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_summarizer import AISummarizer
from generate_daily_pages import render_daily_html, ensure_dirs

def generate_daily_with_ai(date_str: str):
    """用AI生成日报"""
    print(f"\n📅 生成 {date_str} 的日报...")
    
    # 加载数据
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在: {data_file}")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    if not articles:
        print(f"⚠️ {date_str} 无文章需要生成")
        return False
    
    print(f"  文章数: {len(articles)}")
    
    # 调用AI生成摘要
    api_key = os.environ.get('AI_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
    provider = os.environ.get('AI_PROVIDER', 'openrouter')
    
    if not api_key:
        print("❌ 未设置AI_API_KEY环境变量")
        return False
    
    summarizer = AISummarizer(provider, api_key)
    
    try:
        summary = summarizer.generate_daily_summary(articles, date_str)
        print(f"  ✅ AI摘要生成成功")
    except Exception as e:
        print(f"❌ AI摘要生成失败: {e}")
        return False
    
    # 保存AI响应
    os.makedirs('ai_responses', exist_ok=True)
    response_file = f'ai_responses/{date_str}_response.json'
    with open(response_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 响应已保存: {response_file}")
    
    # 生成HTML
    ensure_dirs()
    html_content = render_daily_html(date_str, summary)
    
    html_file = f'docs/daily/{date_str}.html'
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"  ✅ HTML已生成: {html_file}")
    
    return True

if __name__ == '__main__':
    dates = ['2026-04-03', '2026-04-08']
    
    print("=" * 50)
    print("AI生成日报")
    print("=" * 50)
    
    for date_str in dates:
        generate_daily_with_ai(date_str)
    
    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
