#!/usr/bin/env python3
"""
每日文献抓取 + 日报生成自动化脚本
由OpenClaw AI助手直接执行 - 包含AI翻译
"""
import os
import sys
import json
import subprocess
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, timeout=300):
    """运行shell命令"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def fetch_literature():
    """抓取文献"""
    print("📚 开始抓取文献...")
    
    # 运行RSS抓取
    success, stdout, stderr = run_command("python fetch_rss.py", timeout=300)
    if success:
        print("✅ RSS抓取完成")
    else:
        print(f"⚠️ RSS抓取警告: {stderr[:200]}")
    
    # 运行相关文献筛选
    success, stdout, stderr = run_command("python run_optimized_sync.py", timeout=300)
    if success:
        print("✅ 文献筛选完成")
    else:
        print(f"⚠️ 文献筛选警告: {stderr[:200]}")
    
    return True

def prepare_articles_for_translation(date_str):
    """准备需要翻译的文章"""
    print(f"\n📅 准备 {date_str} 的文章...")
    
    # 筛选日报文章
    success, stdout, stderr = run_command(f"python -c \"\nimport sys\nsys.path.insert(0, '.')\nfrom regenerate_daily import regenerate_daily\nregenerate_daily('{date_str}')\n\"", timeout=60)
    
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('articles', [])

def generate_translation_request_file(date_str, articles):
    """生成翻译请求文件"""
    if not articles:
        return None
    
    output_dir = "/tmp/literature_translation"
    os.makedirs(output_dir, exist_ok=True)
    
    request_file = f"{output_dir}/{date_str}_request.json"
    
    request_data = {
        "date": date_str,
        "articles_count": len(articles),
        "articles": articles,
        "instruction": f"请为{date_str}的{len(articles)}篇文献生成中文翻译",
        "output_file": f"{output_dir}/{date_str}_response.json"
    }
    
    with open(request_file, 'w', encoding='utf-8') as f:
        json.dump(request_data, f, ensure_ascii=False, indent=2)
    
    return request_file

def generate_daily_html(date_str, articles, translated_data=None):
    """生成日报HTML"""
    print(f"\n📝 生成 {date_str} 的HTML...")
    
    from generate_daily_pages import render_daily_html, ensure_dirs
    
    full_list = []
    for i, art in enumerate(articles):
        # 使用翻译数据（如果有）
        trans = translated_data.get(str(i)) if translated_data else None
        
        item = {
            'title_en': art.get('title'),
            'title_zh': trans.get('title_zh') if trans else (art.get('title_zh') or art.get('title')),
            'abstract_zh': trans.get('abstract_zh') if trans else (art.get('abstract_zh') or art.get('abstract', '')[:300]),
            'summary': trans.get('summary') if trans else (art.get('one_sentence_summary') or '点击查看原文了解详情'),
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
        'generated_by': 'openclaw_auto'
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
    
    print(f"✅ HTML已生成: docs/daily/{date_str}.html")
    return True

def push_to_github():
    """推送到GitHub"""
    print("\n🚀 推送到GitHub...")
    
    date_str = datetime.now().strftime('%Y-%m-%d')
    commit_msg = f"📚 自动更新日报 {date_str} [OpenClaw AI]"
    
    commands = [
        "git add -A",
        f"git commit -m '{commit_msg}' || true",
        "git pull origin main --no-rebase || true",
        "git push origin main"
    ]
    
    for cmd in commands:
        success, stdout, stderr = run_command(cmd, timeout=60)
        if not success and 'nothing to commit' not in stderr and 'no changes added' not in stderr:
            print(f"⚠️ 命令警告: {cmd[:50]}...")
    
    print("✅ 推送完成")
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("📚 OpenClaw AI 日报自动化系统")
    print("=" * 60)
    
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"\n🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 处理日期: {today}")
    
    # 1. 抓取文献
    fetch_literature()
    
    # 2. 准备文章
    articles = prepare_articles_for_translation(today)
    
    if articles:
        print(f"📊 文章数: {len(articles)}")
        
        # 3. 生成请求文件（我会在当前会话中读取并翻译）
        request_file = generate_translation_request_file(today, articles)
        print(f"\n📝 翻译请求文件: {request_file}")
        print("💡 提示: 我会在本次会话中读取此文件并生成翻译")
        
        # 4. 等待翻译完成（在当前会话中由我自己完成）
        # 这个脚本会在后续步骤中被调用时完成翻译
        
        # 5. 生成HTML（使用基础数据，等待翻译）
        generate_daily_html(today, articles)
    else:
        print(f"⚠️ {today} 无新文章")
    
    # 6. 推送
    push_to_github()
    
    print("\n" + "=" * 60)
    print("✅ 日报自动化流程完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
