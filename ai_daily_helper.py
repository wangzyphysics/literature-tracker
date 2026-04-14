#!/usr/bin/env python3
"""
OpenClaw AI 日报生成助手
使用方法: python3 ai_daily_helper.py [YYYY-MM-DD]

此脚本会：
1. 抓取最新文献
2. 筛选日报文章
3. 生成待翻译文件
4. 提示用户（OpenClaw AI）完成翻译
5. 生成最终HTML
6. 推送到GitHub
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def run(cmd, timeout=300):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def fetch():
    log("📚 抓取文献...")
    success, out, err = run("timeout 300 python3 run_optimized_sync.py", timeout=350)
    if success:
        log("✅ 文献抓取完成")
    else:
        log(f"⚠️ 抓取警告: {err[:100]}")
    return True

def prepare_daily(date_str):
    log(f"📅 准备 {date_str} 的日报数据...")
    
    success, out, err = run(f"python3 -c \"import sys; sys.path.insert(0, '.'); from regenerate_daily import regenerate_daily; regenerate_daily('{date_str}')\"", timeout=60)
    
    data_file = f'ai_prompts/{date_str}_data.json'
    if not os.path.exists(data_file):
        log(f"⚠️ {date_str} 无数据")
        return None
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    log(f"📊 文章数: {len(articles)}")
    return articles

def create_translation_task(date_str, articles):
    """创建翻译任务文件"""
    task_file = f'/tmp/literature_task_{date_str}.json'
    
    task = {
        'date': date_str,
        'articles': articles,
        'status': 'pending_translation',
        'created_at': datetime.now().isoformat()
    }
    
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(task, f, ensure_ascii=False, indent=2)
    
    return task_file

def generate_with_ai_translation(date_str, articles, translations=None):
    """生成日报（含AI翻译）"""
    from generate_daily_pages import render_daily_html, ensure_dirs
    
    full_list = []
    for i, art in enumerate(articles):
        # 如果有翻译数据则使用，否则使用原文
        trans = translations.get(str(i)) if translations else None
        
        item = {
            'title_en': art.get('title'),
            'title_zh': trans['title_zh'] if trans else art.get('title'),
            'abstract_zh': trans['abstract_zh'] if trans else art.get('abstract', '')[:300],
            'summary': trans['summary'] if trans else '点击查看原文了解详情',
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
        'generated_by': 'openclaw_ai'
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
    
    log(f"✅ HTML已生成: docs/daily/{date_str}.html")
    return True

def push():
    log("🚀 推送到GitHub...")
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    run("git add -A")
    run(f"git commit -m '📚 Daily update {date_str} [OpenClaw AI]' || true")
    run("git pull origin main --no-rebase || true")
    success, out, err = run("git push origin main")
    
    if success:
        log("✅ 推送成功")
    else:
        log(f"⚠️ 推送问题: {err[:100]}")
    return success

def main():
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"📚 OpenClaw AI 日报助手 - {date_str}")
    print("=" * 60)
    
    # 1. 抓取
    fetch()
    
    # 2. 准备数据
    articles = prepare_daily(date_str)
    if not articles:
        print("\n⚠️ 今日无新文章，跳过")
        return
    
    # 3. 创建翻译任务
    task_file = create_translation_task(date_str, articles)
    print(f"\n📝 翻译任务文件: {task_file}")
    
    # 4. 显示文章列表（供AI翻译使用）
    print("\n📋 待翻译文章列表:")
    print("-" * 60)
    for i, art in enumerate(articles, 1):
        print(f"\n[{i}] {art.get('title', 'N/A')[:70]}")
        print(f"    期刊: {art.get('journal', 'N/A')}")
        print(f"    作者: {', '.join(art.get('authors', [])[:3]) if art.get('authors') else 'N/A'}")
        abstract = art.get('abstract', 'N/A')
        print(f"    摘要: {abstract[:150]}..." if len(abstract) > 150 else f"    摘要: {abstract}")
    
    print("\n" + "=" * 60)
    print("💡 OpenClaw AI 请完成以下操作:")
    print(f"   1. 读取任务文件: {task_file}")
    print(f"   2. 为每篇文章生成中文翻译")
    print(f"   3. 保存翻译到: /tmp/literature_translations_{date_str}.json")
    print("=" * 60)
    
    # 5. 检查是否有翻译文件
    trans_file = f'/tmp/literature_translations_{date_str}.json'
    if os.path.exists(trans_file):
        log(f"✅ 找到翻译文件，生成最终HTML...")
        with open(trans_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        generate_with_ai_translation(date_str, articles, translations)
        push()
    else:
        log("⏳ 等待翻译文件...")
        log(f"   请创建: {trans_file}")
        print("\n临时生成基础HTML（无AI翻译）...")
        os.system(f"python3 generate_with_local_ai.py {date_str}")
        push()

if __name__ == '__main__':
    main()
