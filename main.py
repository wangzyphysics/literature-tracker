#!/usr/bin/env python3
"""
RSS文献追踪系统 - 主程序
功能：抓取RSS文献、关键词筛选、翻译、保存、邮件通知
"""

import os
import sys
import argparse
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import RSS_FEEDS, KEYWORDS, EMAIL_CONFIG, DATA_DIR, ARTICLES_DIR
from rss_fetcher import RSSFetcher
from translator import translate_text
from data_manager import DataManager
from email_notifier import EmailNotifier
from abstract_scraper import AbstractScraper, enhance_article_abstract


def run_fetch(send_email: bool = True, verbose: bool = True):
    """执行一次抓取任务"""
    print(f"\n{'='*60}")
    print(f"开始抓取 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # 初始化组件
    fetcher = RSSFetcher(KEYWORDS)
    data_manager = DataManager(DATA_DIR, ARTICLES_DIR)
    
    # 1. 抓取所有RSS源
    print("📡 正在抓取RSS源...")
    all_articles = fetcher.fetch_all(RSS_FEEDS)
    print(f"\n共获取 {len(all_articles)} 篇文献")
    
    # 2. 关键词筛选
    print(f"\n🔍 使用关键词筛选: {', '.join(KEYWORDS)}")
    filtered_articles = fetcher.filter_by_keywords(all_articles)
    print(f"筛选后剩余 {len(filtered_articles)} 篇文献")
    
    # 3. 获取新文献（去重）
    new_articles = data_manager.get_new_articles(filtered_articles)
    print(f"其中新文献 {len(new_articles)} 篇")
    
    if not new_articles:
        print("\n✅ 没有新文献，任务完成")
        return []
    
    # 4. 翻译新文献（并增强摘要）
    print(f"\n🌐 正在处理 {len(new_articles)} 篇新文献...")
    scraper = AbstractScraper()
    enhanced_count = 0
    
    for i, article in enumerate(new_articles, 1):
        print(f"  [{i}/{len(new_articles)}] {article.title[:50]}...")
        
        # 先检查并增强摘要
        if enhance_article_abstract(article, scraper, translate_text):
            enhanced_count += 1
        else:
            # 如果没有增强，正常翻译
            if article.abstract:
                article.abstract_zh = translate_text(article.abstract)
            else:
                article.abstract_zh = ""
        
        # 翻译标题
        article.title_zh = translate_text(article.title)
    
    if enhanced_count > 0:
        print(f"\n📊 共增强 {enhanced_count} 篇文献的摘要")
    
    # 5. 保存到历史记录
    print("\n💾 保存数据...")
    data_manager.add_articles(new_articles)
    
    # 6. 生成Markdown文件
    print("📝 生成Markdown文件...")
    for article in new_articles:
        filepath = data_manager.save_article_markdown(article)
        if verbose:
            print(f"  已保存: {filepath}")
    
    # 7. 生成索引JSON
    data_manager.generate_index_json()
    print("📊 索引文件已更新")
    
    # 8. 发送邮件通知
    if send_email and EMAIL_CONFIG.get("sender_email"):
        print("\n📧 发送邮件通知...")
        notifier = EmailNotifier(
            smtp_server=EMAIL_CONFIG["smtp_server"],
            smtp_port=EMAIL_CONFIG["smtp_port"],
            sender_email=EMAIL_CONFIG["sender_email"],
            sender_password=EMAIL_CONFIG["sender_password"],
        )
        notifier.send_notification(EMAIL_CONFIG["recipient"], new_articles)
    
    print(f"\n✅ 任务完成！共处理 {len(new_articles)} 篇新文献")
    return new_articles


def run_scheduler():
    """运行定时任务（每12小时执行一次）"""
    import schedule
    import time
    
    print("🕐 定时任务已启动，每12小时执行一次")
    print("   按 Ctrl+C 停止\n")
    
    # 立即执行一次
    run_fetch()
    
    # 设置定时任务
    schedule.every(12).hours.do(run_fetch)
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description="RSS文献追踪系统")
    parser.add_argument("--once", action="store_true", help="只执行一次")
    parser.add_argument("--no-email", action="store_true", help="不发送邮件")
    parser.add_argument("--schedule", action="store_true", help="启动定时任务")
    
    args = parser.parse_args()
    
    if args.schedule:
        run_scheduler()
    else:
        run_fetch(send_email=not args.no_email)


if __name__ == "__main__":
    main()
