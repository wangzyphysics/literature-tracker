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
from zh_enricher import enrich_articles_zh

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
    
    existing_links = {a.get('link') for a in existing_articles if a.get('link')}
    new_count = 0
    for a in filtered:
        if a.link and a.link not in existing_links:
            existing_articles.append(a.to_dict())
            new_count += 1

    # Enrich zh fields (title_zh/abstract_zh) for newest missing items
    ai_key = (os.environ.get("AI_API_KEY") or AI_CONFIG.get("api_key") or "").strip()
    ai_provider = (os.environ.get("AI_PROVIDER") or AI_CONFIG.get("provider") or "gemini").strip()
    ai_model = (os.environ.get("AI_MODEL") or AI_CONFIG.get("model") or "").strip() or None
    zh_max_items = int(os.environ.get("AI_ZH_MAX_ITEMS", "120"))
    zh_updated = enrich_articles_zh(
        existing_articles,
        provider_name=ai_provider,
        api_key=ai_key,
        model=ai_model,
        max_items=zh_max_items,
    )
    if zh_updated:
        print(f"🌐 已补全中文标题/摘要: {zh_updated} 篇 (本次新增: {new_count})")
    elif new_count:
        print(f"🌐 本次新增: {new_count} 篇 (中文字段补全: 0)")
    
    existing_articles.sort(key=lambda x: x.get('pub_date', ''), reverse=True)
    with open(full_data_path, 'w', encoding='utf-8') as f:
        json.dump({'articles': existing_articles[:5000]}, f, ensure_ascii=False, indent=2)
    print(f"📊 索引文件已更新 (Total: {len(existing_articles[:5000])})")

    # 2. Deep Filter with Gemini
    # Use the same AI config path as summarizer
    analyser = DeepAnalyser(api_key=ai_key, provider=ai_provider, model=ai_model)
    notifier = NotionTGNotifier()

    # Ensure ai_relevant.json exists and load it once
    ai_relevant_path = "data/ai_relevant.json"
    ai_relevant_list = []
    if os.path.exists(ai_relevant_path):
        try:
            with open(ai_relevant_path, "r", encoding="utf-8") as f:
                ai_relevant_list = json.load(f) or []
        except Exception:
            ai_relevant_list = []
    existing_relevant_links = {a.get("link") for a in ai_relevant_list if isinstance(a, dict)}
    
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
            
            # Ensure zh fields exist (prefer the already enriched index; fallback to translator)
            if not article.title_zh:
                for a in existing_articles[:500]:  # only scan a small prefix (newest) for speed
                    if a.get("link") == article.link:
                        article.title_zh = a.get("title_zh") or ""
                        article.abstract_zh = a.get("abstract_zh") or ""
                        break
            if not article.title_zh:
                article.title_zh = translate_text(article.title)
            if article.abstract and not article.abstract_zh:
                article.abstract_zh = translate_text(article.abstract)
            
            # Save to AI-relevant pool for daily pages
            if article.link and article.link not in existing_relevant_links:
                item = article.to_dict()
                item.update(
                    {
                        "ai_score": analysis.get("score"),
                        "ai_explanation": analysis.get("explanation"),
                        "ai_detailed_summary": analysis.get("detailed_summary"),
                    }
                )
                ai_relevant_list.append(item)
                existing_relevant_links.add(article.link)
            
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

    # Persist ai_relevant.json even if empty (stable downstream daily generation)
    with open(ai_relevant_path, "w", encoding="utf-8") as f:
        json.dump(ai_relevant_list, f, ensure_ascii=False, indent=2)
            
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
    provider = os.environ.get('AI_PROVIDER') or 'gemini'
    
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
