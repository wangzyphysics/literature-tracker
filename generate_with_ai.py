#!/usr/bin/env python3
"""
使用OpenRouter API生成日报（含AI摘要翻译）
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_summarizer import AISummarizer
from generate_daily_pages import render_daily_html, ensure_dirs

def generate_daily_with_ai(date_str: str):
    """使用AI生成指定日期的完整日报"""
    print(f"\n{'='*50}")
    print(f"📅 生成 {date_str} 的AI日报")
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
    
    # 获取API配置
    api_key = os.environ.get('OPENROUTER_API_KEY') or os.environ.get('AI_API_KEY')
    provider = os.environ.get('AI_PROVIDER', 'openrouter')
    
    if not api_key:
        print("❌ 未设置API密钥 (OPENROUTER_API_KEY 或 AI_API_KEY)")
        return False
    
    print(f"🤖 使用Provider: {provider}")
    
    summarizer = AISummarizer(provider, api_key)
    
    try:
        # 设置超时
        os.environ['AI_DAILY_WAIT_MAX_SECONDS'] = '120'
        summary = summarizer.generate_daily_summary(articles, date_str)
        print(f"✅ AI摘要生成成功 (by: {summary.get('generated_by', 'unknown')})")
    except Exception as e:
        print(f"❌ AI摘要失败: {e}")
        return False
    
    # 检查内容
    has_abstract = any(a.get('abstract_zh') for a in summary.get('full_list', []))
    has_authors = all(a.get('authors') for a in summary.get('full_list', []))
    print(f"📄 含中文摘要: {has_abstract}")
    print(f"👥 含作者列表: {has_authors}")
    
    # 保存响应
    os.makedirs('ai_responses', exist_ok=True)
    with open(f'ai_responses/{date_str}_response.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 响应已保存: ai_responses/{date_str}_response.json")
    
    # 生成HTML
    ensure_dirs()
    html = render_daily_html(date_str, summary)
    with open(f'docs/daily/{date_str}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已生成: docs/daily/{date_str}.html")
    
    return True

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python3 generate_with_ai.py YYYY-MM-DD")
        print("示例: python3 generate_with_ai.py 2026-04-13")
        sys.exit(1)
    
    date = sys.argv[1]
    
    # 检查环境变量
    if not os.environ.get('OPENROUTER_API_KEY'):
        print("❌ 请先设置 OPENROUTER_API_KEY 环境变量")
        sys.exit(1)
    
    success = generate_daily_with_ai(date)
    sys.exit(0 if success else 1)
