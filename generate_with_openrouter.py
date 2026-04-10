#!/usr/bin/env python3
"""
直接调用OpenRouter API生成文章摘要
"""
import os
import sys
import json
import requests
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def generate_summary_for_article(article: dict, api_key: str) -> dict:
    """为单篇文章生成摘要"""
    title = article.get('title', '')
    abstract = article.get('abstract', '') or article.get('summary', '')
    journal = article.get('journal', '')
    
    prompt = f"""请为以下学术论文生成中文信息：

标题: {title}
期刊: {journal}
摘要: {abstract[:500] if abstract else '暂无摘要'}

请用JSON格式返回：
{{
  "title_zh": "中文标题（简洁准确）",
  "abstract_zh": "摘要中文翻译（100字以内，保留关键信息）",
  "one_sentence_summary": "一句话研究亮点（突出创新点）"
}}

只返回JSON，不要其他文字。"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://literature-tracker.local"
            },
            json={
                "model": "anthropic/claude-3.5-sonnet",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 800
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 解析JSON
            try:
                # 尝试直接解析
                data = json.loads(content)
            except:
                # 尝试从markdown代码块中提取
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0]
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0]
                data = json.loads(content.strip())
            
            return {
                'title_zh': data.get('title_zh', '翻译失败'),
                'abstract_zh': data.get('abstract_zh', ''),
                'one_sentence_summary': data.get('one_sentence_summary', ''),
                'success': True
            }
        else:
            print(f"  API错误: {response.status_code}")
            return {'success': False}
    except Exception as e:
        print(f"  请求失败: {e}")
        return {'success': False}

def process_daily(date_str: str):
    """处理指定日期的文章"""
    print(f"\n{'='*50}")
    print(f"📅 处理 {date_str}")
    print(f"{'='*50}")
    
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("❌ 未设置OPENROUTER_API_KEY")
        return
    
    # 加载数据
    data_file = f'ai_prompts/{date_str}_data.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    print(f"文章数: {len(articles)}")
    
    # 为每篇文章生成摘要
    summaries = []
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] {art.get('title', '')[:50]}...")
        
        result = generate_summary_for_article(art, api_key)
        
        if result['success']:
            print(f"  ✅ 标题: {result['title_zh'][:30]}...")
            print(f"  ✅ 摘要: {result['abstract_zh'][:30]}..." if result['abstract_zh'] else "  ⚠️ 无摘要")
            summaries.append({
                'title_en': art.get('title'),
                'title_zh': result['title_zh'],
                'abstract_zh': result['abstract_zh'],
                'summary': result['one_sentence_summary'] or '请查阅原文',
                'link': art.get('link'),
                'journal': art.get('journal', ''),
                'authors': art.get('authors', []),
                'pub_date': art.get('pub_date', ''),
            })
        else:
            print(f"  ❌ 生成失败，使用fallback")
            summaries.append({
                'title_en': art.get('title'),
                'title_zh': art.get('title_zh') or '待翻译',
                'abstract_zh': '',
                'summary': '请查阅原文了解详情',
                'link': art.get('link'),
                'journal': art.get('journal', ''),
                'authors': art.get('authors', []),
                'pub_date': art.get('pub_date', ''),
            })
        
        time.sleep(1)  # 避免rate limit
    
    # 保存结果
    output = {
        'date': date_str,
        'total': len(summaries),
        'overview': f"今日共收录{len(summaries)}篇文献。",
        'trends': '',
        'full_list': summaries,
        'generated_by': 'openrouter_claude'
    }
    
    os.makedirs('ai_responses', exist_ok=True)
    with open(f'ai_responses/{date_str}_response.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 已保存: ai_responses/{date_str}_response.json")
    
    # 生成HTML
    from generate_daily_pages import render_daily_html, ensure_dirs
    ensure_dirs()
    html = render_daily_html(date_str, output)
    with open(f'docs/daily/{date_str}.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ HTML已生成: docs/daily/{date_str}.html")

if __name__ == '__main__':
    dates = ['2026-04-02', '2026-04-03', '2026-04-06', '2026-04-08']
    
    for date in dates:
        process_daily(date)
    
    print(f"\n{'='*50}")
    print("全部完成！")
    print(f"{'='*50}")
