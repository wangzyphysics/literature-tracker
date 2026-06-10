import os
import json
import requests
from datetime import datetime
from ai_summarizer import AISummarizer
import time

class NotionTGNotifier:
    def __init__(self, config_path=".env.lit"):
        self.config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        self.config[k] = v.strip('"')
        
        self.bot_token = os.environ.get("TG_LIT_BOT_TOKEN") or self.config.get("TG_LIT_BOT_TOKEN")
        self.chat_id = os.environ.get("TG_LIT_CHAT_ID") or self.config.get("TG_LIT_CHAT_ID")
        self.notion_token = os.environ.get("NOTION_API_KEY") or self.config.get("NOTION_API_KEY")
        self.parent_id = os.environ.get("NOTION_LIT_PARENT_ID") or self.config.get("NOTION_LIT_PARENT_ID")
        self.proxy = os.environ.get("http_proxy") or "http://127.0.0.1:7897"
        
        self.notion_headers = {
            "Authorization": f"Bearer {self.notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

    def send_tg_message(self, text):
        if not self.bot_token or not self.chat_id:
            print("TG credentials missing")
            return
        
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        
        proxies = {"http": self.proxy, "https": self.proxy} if self.proxy else None
        try:
            r = requests.post(url, json=payload, proxies=proxies, timeout=10)
            if r.status_code != 200:
                print(f"TG Error: {r.text}")
            return r.json()
        except Exception as e:
            print(f"TG Connection Error: {e}")
            return None

    def get_or_create_page(self, parent_id, title):
        # 1. Try to find existing child page by title
        url = f"https://api.notion.com/v1/blocks/{parent_id.replace('-', '')}/children"
        try:
            r = requests.get(url, headers=self.notion_headers, timeout=15)
            if r.status_code == 200:
                results = r.json().get("results", [])
                for block in results:
                    if block["type"] == "child_page":
                        if block["child_page"]["title"] == title:
                            return block["id"]
        except Exception as e:
            print(f"Error fetching child pages: {e}")

        # 2. Create new page if not found
        url = "https://api.notion.com/v1/pages"
        payload = {
            "parent": {"page_id": parent_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        }
        try:
            r = requests.post(url, headers=self.notion_headers, json=payload, timeout=15)
        except Exception as e:
            print(f"Notion Create Page Error: {type(e).__name__}: {e}")
            return None
        if r.status_code == 200:
            return r.json()["id"]
        else:
            print(f"Notion Create Page Error ({r.status_code}): {r.text}")
            return None

    def append_blocks(self, page_id, blocks):
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        try:
            r = requests.patch(url, headers=self.notion_headers, json={"children": blocks}, timeout=15)
        except Exception as e:
            print(f"Notion Append Blocks Error: {type(e).__name__}: {e}")
            return False
        if r.status_code != 200:
            print(f"Notion Append Blocks Error: {r.text}")
        return r.status_code == 200

    def sync_article(self, article_data, ai_analysis):
        if not self.notion_token or not self.parent_id:
            print("Notion credentials missing, skip Notion sync")
            return
        # 1. Get/Create Month Page
        now = datetime.now()
        month_str = now.strftime("%Y年%m月")
        month_page_id = self.get_or_create_page(self.parent_id, month_str)
        if not month_page_id: return
        
        # 2. Get/Create Day Page
        day_str = now.strftime("%Y-%m-%d")
        day_page_id = self.get_or_create_page(month_page_id, day_str)
        if not day_page_id: return
        
        # 3. Append Article blocks
        blocks = [
            {
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": article_data.get('title_zh') or article_data.get('title')}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "🔗 "}, "annotations": {"bold": True}},
                        {"type": "text", "text": {"content": "原文链接", "link": {"url": article_data.get('link')}}}
                    ]
                }
            },
            {
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [{"type": "text", "text": {"content": ai_analysis}}],
                    "icon": {"emoji": "🤖"}
                }
            },
            {
                "object": "block",
                "type": "divider",
                "divider": {}
            }
        ]
        self.append_blocks(day_page_id, blocks)

    def send_daily_report(self, summary_data):
        # 1. Telegram
        if self.bot_token and self.chat_id:
            msg = f"<b>📊 每日文献汇总报告 ({summary_data['date']})</b>\n\n"
            msg += f"今日收录: {summary_data['total']} 篇\n\n"
            msg += f"<b>💡 总览：</b>\n{summary_data.get('overview', '无')}\n\n"
            
            # Add full list to TG
            msg += "<b>📋 文献列表：</b>\n"
            for i, item in enumerate(summary_data.get('full_list', []), 1):
                # Ensure titles and summaries exist
                t_en = item.get('title_en', 'Untitled')
                t_zh = item.get('title_zh', '')
                summary_text = item.get('summary', '')
                link = item.get('link', '#')
                
                line = f"{i}. <a href='{link}'>{t_en}</a>\n"
                if t_zh: line += f"   <i>{t_zh}</i>\n"
                if summary_text: line += f"   📝 {summary_text}\n"
                line += "\n"
                
                if len(msg) + len(line) > 3800:
                    msg += "... (列表过长，更多内容请查阅 Notion)\n"
                    break
                msg += line
            
            self.send_tg_message(msg)
        else:
            print("TG credentials missing, skip Telegram daily report")
        
        # 2. Notion
        if not self.notion_token or not self.parent_id:
            print("Notion credentials missing, skip Notion daily report")
            return
        month_str = datetime.now().strftime("%Y年%m月")
        month_page_id = self.get_or_create_page(self.parent_id, month_str)
        day_str = summary_data['date']
        day_page_id = self.get_or_create_page(month_page_id, day_str)
        
        report_blocks = [
            {
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": f"📅 {day_str} 汇总报告"}}]
                }
            },
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary_data.get('overview', '')}}]
                }
            }
        ]
        
        for item in summary_data.get('full_list', []):
            report_blocks.extend([
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": item.get('title_en', 'Untitled')}}]
                    }
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": f"🇨🇳 {item.get('title_zh', '')}\n"}},
                            {"type": "text", "text": {"content": f"📝 {item.get('summary', '')}\n"}},
                            {"type": "text", "text": {"content": "🔗 原文链接", "link": {"url": item.get('link', 'https://example.com')}}}
                        ]
                    }
                },
                {"object": "block", "type": "divider", "divider": {}}
            ])
            
            if len(report_blocks) >= 60:
                self.append_blocks(day_page_id, report_blocks)
                report_blocks = []

        if report_blocks:
            self.append_blocks(day_page_id, report_blocks)

if __name__ == "__main__":
    # Test sync
    notifier = NotionTGNotifier()
    # notifier.send_tg_message("Test from Pi")
