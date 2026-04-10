#!/usr/bin/env python3
"""生成AI prompt文件"""

import json
import os

def format_article(article, index):
    title = article.get('title_en') or article.get('title') or ''
    title_zh = article.get('title_zh', '')
    journal = article.get('journal', '')
    authors = article.get('authors', [])
    author_str = ', '.join(authors[:3]) + (' et al.' if len(authors) > 3 else '') if authors else '未知'
    link = article.get('link', '')
    return f"[{index}] {title}\n    中文标题: {title_zh}\n    期刊: {journal}\n    作者: {author_str}\n    链接: {link}"

for date in ['2026-04-01', '2026-04-02', '2026-04-03', '2026-04-04', '2026-04-07', '2026-04-08', '2026-04-09']:
    # 加载数据
    with open(f'ai_prompts/{date}_data.json') as f:
        data = json.load(f)
    
    articles = data['articles']
    if not articles:
        continue
    
    # 构建prompt
    articles_text = '\n'.join([format_article(a, i+1) for i, a in enumerate(articles[:40])])
    
    prompt = f"""你是AI×Science文献分析专家。请为{date}的文献生成日报摘要。

【今日收录文献】（共{len(articles)}篇）
{articles_text}

请生成以下JSON格式的摘要：
{{
  "overview": "用3-4句话概括今日文献的整体特点，包括主要研究方向、热点主题、方法学进展等",
  "trends": "列出3-4个今日研究热点趋势，每点一句话",
  "full_list": [
    {{
      "title_en": "英文标题",
      "title_zh": "中文标题", 
      "summary": "2-3句话的技术摘要",
      "key_findings": ["关键发现1", "关键发现2"],
      "significance": "一句话说明研究意义"
    }}
  ]
}}

要求：
1. 用中文撰写
2. 突出AI与Science的交叉点
3. 每个文献的summary控制在100字以内"""

    # 保存prompt
    with open(f'ai_prompts/{date}_prompt.txt', 'w') as f:
        f.write(prompt)
    
    print(f'{date}: prompt已生成')

print('✅ 全部完成')
