import os
import sys
import json
from datetime import datetime, timezone, timedelta
import time

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RSS_FEEDS, KEYWORDS, DEDUP_CONFIG, AI_CONFIG
from rss_fetcher import RSSFetcher
from deduplicator import Deduplicator
from deep_analyser import DeepAnalyser
from notion_tg_notifier import NotionTGNotifier
from translator import translate_text
from ai_summarizer import AISummarizer

def get_beijing_time():
    beijing_tz = timezone(timedelta(hours=8))
    return datetime.now(beijing_tz)

def get_beijing_today():
    return get_beijing_time().strftime('%Y-%m-%d')

def run_optimized_sync():
    print(f"\n{'='*60}")
    print(f"开始优化同步 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 1. Fetch & Basic Filter
    fetcher = RSSFetcher(KEYWORDS)
    print("📡 正在抓取所有RSS源 (不进行全文翻译)...")
    all_articles = fetcher.fetch_all(RSS_FEEDS)
    print(f"获取 {len(all_articles)} 篇原始文献")
    
    filtered = fetcher.filter_by_keywords(all_articles)
    print(f"关键词筛选后剩余 {len(filtered)} 篇")
    
    if DEDUP_CONFIG.get('enabled', True):
        deduper = Deduplicator(similarity_threshold=DEDUP_CONFIG.get('similarity_threshold', 0.98))
        filtered, dup_count = deduper.deduplicate(filtered)
        print(f"去重后剩余 {len(filtered)} 篇 (去除 {dup_count} 篇)")

    # Update global index first
    full_data_path = "data/index.json"
    os.makedirs('data', exist_ok=True)
    existing_articles = []
    if os.path.exists(full_data_path):
        try:
            with open(full_data_path, 'r', encoding='utf-8') as f:
                existing_articles = json.load(f).get('articles', [])
        except: pass
    
    existing_links = {a['link'] for a in existing_articles}
    for a in filtered:
        if a.link not in existing_links:
            existing_articles.append(a.to_dict())
    
    existing_articles.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
    with open(full_data_path, 'w', encoding='utf-8') as f:
        json.dump({'articles': existing_articles[:5000]}, f, ensure_ascii=False, indent=2)
    print(f"📊 索引文件已更新 (Total: {len(existing_articles[:5000])})")

    # 2. Deep Filter with Gemini
    analyser = DeepAnalyser()
    notifier = NotionTGNotifier()
    
    processed_file = "data/deep_history.json"
    processed_ids = set()
    if os.path.exists(processed_file):
        try:
            with open(processed_file, "r") as f:
                processed_ids = set(json.load(f))
        except: pass

    today = get_beijing_today()
    yesterday = (get_beijing_time() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Target: new papers from today/yesterday not yet deep-analyzed
    recent_papers = [a for a in filtered if a.pub_date in [today, yesterday] and a.link not in processed_ids]
    
    print(f"需要深度分析的近期文献数: {len(recent_papers)}")
    
    newly_relevant_count = 0
    for article in recent_papers:
        print(f"正在深度分析: {article.title[:60]}...")
        analysis = analyser.analyze_relevance(article.to_dict())
        
        # Ensure analysis is a dict
        if isinstance(analysis, list) and len(analysis) > 0:
            analysis = analysis[0]
        if not isinstance(analysis, dict):
            print(f"  ⚠️ AI返回格式异常: {type(analysis)}")
            continue

        if analysis.get('is_relevant') and analysis.get('score', 0) >= 6:
            print(f"  🔥 判定相关! 分数: {analysis['score']}")
            
            # Translate for relevant papers only
            article.title_zh = translate_text(article.title)
            article.abstract_zh = translate_text(article.abstract)
            
            # Save to AI-relevant pool for daily pages
            ai_relevant_path = "data/ai_relevant.json"
            try:
                existing = []
                if os.path.exists(ai_relevant_path):
                    with open(ai_relevant_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
            except Exception:
                existing = []
            existing_links = {a.get('link') for a in existing}
            if article.link not in existing_links:
                item = article.to_dict()
                item.update({
                    "ai_score": analysis.get('score'),
                    "ai_explanation": analysis.get('explanation'),
                    "ai_detailed_summary": analysis.get('detailed_summary'),
                })
                existing.append(item)
                with open(ai_relevant_path, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
            
            # Immediate Push
            msg = f"<b>🆕 发现高度相关文献 (Score: {analysis['score']})</b>\n\n"
            msg += f"<b>{article.title_zh or article.title}</b>\n"
            msg += f"<i>{article.journal}</i>\n\n"
            msg += f"🤖 <b>AI推荐理由：</b>\n{analysis['explanation']}\n\n"
            msg += f"📝 <b>深度解析：</b>\n{analysis['detailed_summary']}\n\n"
            msg += f"<a href='{article.link}'>🔗 查看原文</a>"
            
            notifier.send_tg_message(msg)
            notifier.sync_article(article.to_dict(), analysis['detailed_summary'])
            newly_relevant_count += 1
            
        processed_ids.add(article.link)
        with open(processed_file, "w") as f:
            json.dump(list(processed_ids), f)
            
    print(f"\n✅ 同步完成！发现并推送 {newly_relevant_count} 篇高价值文献")

def send_daily_summary():
    print(f"[{datetime.now()}] 正在生成每日汇总报告...")
    today = get_beijing_today()
    
    index_path = "data/index.json"
    if not os.path.exists(index_path):
        print("未发现文献数据，跳过报告")
        return
        
    with open(index_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    articles = data.get("articles", [])
    today_articles = [a for a in articles if (a.get('pub_date') or '').startswith(today)]
    
    if not today_articles:
        print(f"今日 ({today}) 无新文献，跳过报告")
        return
        
    api_key = os.environ.get('AI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    provider = os.environ.get('AI_PROVIDER', 'gemini')
    
    summarizer = AISummarizer(provider, api_key)
    summary = summarizer.generate_daily_summary(today_articles, today)
    
    notifier = NotionTGNotifier()
    notifier.send_daily_report(summary)
    print("✅ 每日报告已推送至 TG 和 Notion")

if __name__ == "__main__":
    if "--summary" in sys.argv:
        send_daily_summary()
    else:
        run_optimized_sync()
