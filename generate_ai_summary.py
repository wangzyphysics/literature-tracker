#!/usr/bin/env python3
"""
调用AI生成完整的文章摘要（含中文标题、摘要翻译、一句话总结）
"""
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_summarizer import AISummarizer

def generate_ai_summary(date_str: str):
    """调用AI生成指定日期的完整摘要"""
    print(f"\n📅 生成 {date_str} 的AI摘要...")
    
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
    
    print(f"  文章数: {len(articles)}")
    
    # 调用AI
    api_key = os.environ.get('AI_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('OPENROUTER_API_KEY')
    provider = os.environ.get('AI_PROVIDER', 'openrouter')
    
    if not api_key:
        print("❌ 未设置AI_API_KEY")
        return False
    
    summarizer = AISummarizer(provider, api_key)
    
    try:
        # 设置较短超时
        os.environ['AI_DAILY_WAIT_MAX_SECONDS'] = '120'
        summary = summarizer.generate_daily_summary(articles, date_str)
        print(f"  ✅ AI摘要生成成功 (by: {summary.get('generated_by', 'unknown')})")
    except Exception as e:
        print(f"❌ AI摘要失败: {e}")
        return False
    
    # 保存响应
    os.makedirs('ai_responses', exist_ok=True)
    response_file = f'ai_responses/{date_str}_response.json'
    with open(response_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 已保存: {response_file}")
    
    # 验证内容
    has_abstract = any(a.get('abstract_zh') for a in summary.get('full_list', []))
    print(f"  📄 含摘要翻译: {has_abstract}")
    
    return True

if __name__ == '__main__':
    dates = ['2026-04-02', '2026-04-03', '2026-04-06', '2026-04-08']
    
    print("=" * 50)
    print("AI生成完整摘要")
    print("=" * 50)
    
    for date_str in dates:
        generate_ai_summary(date_str)
        time.sleep(2)  # 避免rate limit
    
    print("\n" + "=" * 50)
    print("完成！")
    print("=" * 50)
