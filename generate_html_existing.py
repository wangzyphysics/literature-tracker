#!/usr/bin/env python3
"""
使用现有数据中的翻译信息生成HTML
如果AI翻译不可用，使用原文并标记
"""
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_daily_pages import render_daily_html, ensure_dirs

def generate_html_with_existing_data(date_str: str):
    """使用现有数据生成HTML"""
    print(f"\n📅 生成 {date_str} 的日报...")
    
    # 加载数据
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        print(f"❌ 数据文件不存在")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    if not articles:
        print(f"⚠️ 无文章")
        return False
    
    print(f"  文章数: {len(articles)}")
    
    # 构建summary（尝试从现有数据获取翻译）
    full_list = []
    for art in articles:
        # 尝试获取现有翻译，否则标记为待翻译
        title_zh = art.get('title_zh')
        if not title_zh or title_zh == '待翻译':
            # 尝试从title_en翻译（如果有）
            title_zh = art.get('title') or '待翻译'
        
        item = {
            'title_en': art.get('title'),
            'title_zh': title_zh,
            'abstract_zh': art.get('abstract_zh') or art.get('abstract') or '',
            'summary': art.get('one_sentence_summary') or art.get('summary') or '点击查看原文了解详情',
            'link': art.get('link'),
            'journal': art.get('journal', ''),
            'authors': art.get('authors', []),
            'pub_date': art.get('pub_date', ''),
        }
        full_list.append(item)
    
    summary = {
        'date': date_str,
        'total': len(full_list),
        'overview': f"今日共收录{len(full_list)}篇文献。",
        'trends': '',
        'full_list': full_list,
        'generated_by': 'existing_data'
    }
    
    # 保存响应
    os.makedirs('ai_responses', exist_ok=True)
    with open(f'ai_responses/{date_str}_response.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 生成HTML
    ensure_dirs()
    html = render_daily_html(date_str, summary)
    with open(f'docs/daily/{date_str}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✅ HTML已生成")
    
    return True

if __name__ == '__main__':
    import sys
    
    # 支持命令行参数指定日期
    if len(sys.argv) > 1:
        dates = sys.argv[1:]
    else:
        # 默认生成4月1日到4月10日的日报
        dates = ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-06', 
                 '2026-04-07', '2026-04-08', '2026-04-09', '2026-04-10']
    
    print("=" * 50)
    print("使用现有数据生成日报")
    print("=" * 50)
    
    success_count = 0
    for date in dates:
        if generate_html_with_existing_data(date):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"完成！成功生成 {success_count}/{len(dates)} 个日报")
    print("=" * 50)
