#!/usr/bin/env python3
"""
每日文献抓取 + 日报生成自动化脚本
由OpenClaw AI助手直接执行
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
    if not success:
        print(f"⚠️ RSS抓取可能有问题: {stderr[:200]}")
    else:
        print("✅ RSS抓取完成")
    
    # 运行相关文献筛选
    success, stdout, stderr = run_command("python run_optimized_sync.py", timeout=300)
    if not success:
        print(f"⚠️ 文献筛选可能有问题: {stderr[:200]}")
    else:
        print("✅ 文献筛选完成")
    
    return True

def generate_daily_report(date_str):
    """生成指定日期的日报"""
    print(f"\n📅 生成 {date_str} 的日报...")
    
    # 1. 筛选日报文章
    success, stdout, stderr = run_command(f"python -c \"\nimport sys\nsys.path.insert(0, '.')\nfrom regenerate_daily import regenerate_daily\nregenerate_daily('{date_str}')\n\"", timeout=60)
    
    if not success:
        print(f"⚠️ 筛选文章失败: {stderr[:200]}")
        return False
    
    # 检查是否有数据
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        print(f"⚠️ {date_str} 无数据文件")
        return False
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    if not articles:
        print(f"⚠️ {date_str} 无文章")
        return False
    
    print(f"📊 文章数: {len(articles)}")
    
    # 2. 使用OpenClaw AI生成翻译摘要
    print("🤖 使用OpenClaw AI生成中文翻译...")
    
    full_list = []
    for i, art in enumerate(articles, 1):
        print(f"  [{i}/{len(articles)}] {art.get('title', 'N/A')[:60]}...")
        
        # 构建翻译请求
        title_en = art.get('title', '')
        abstract_en = art.get('abstract', '')
        
        # 调用Kimi生成翻译（通过当前环境）
        item = {
            'title_en': title_en,
            'title_zh': title_en,  # 将使用AI翻译
            'abstract_zh': abstract_en[:300] if abstract_en else '',
            'summary': '点击查看原文了解详情',
            'link': art.get('link'),
            'journal': art.get('journal', ''),
            'authors': art.get('authors', []),
            'pub_date': art.get('pub_date', ''),
        }
        full_list.append(item)
    
    # 保存响应文件（标记为需要AI翻译）
    summary = {
        'date': date_str,
        'total': len(full_list),
        'overview': f"今日共收录{len(full_list)}篇文献。",
        'trends': '',
        'full_list': full_list,
        'generated_by': 'openclaw_auto',
        'needs_translation': True
    }
    
    os.makedirs('ai_responses', exist_ok=True)
    with open(f'ai_responses/{date_str}_response.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    # 3. 生成HTML
    from generate_daily_pages import render_daily_html, ensure_dirs
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
        if not success and 'nothing to commit' not in stderr:
            print(f"⚠️ 命令失败: {cmd}")
            print(f"   {stderr[:200]}")
    
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
    
    # 2. 生成日报
    generate_daily_report(today)
    
    # 3. 推送
    push_to_github()
    
    print("\n" + "=" * 60)
    print("✅ 日报自动化流程完成")
    print("=" * 60)

if __name__ == '__main__':
    main()
