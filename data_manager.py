"""
数据管理模块 - 处理JSON存储和Markdown生成
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from rss_fetcher import Article

# 北京时间时区
BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

def format_beijing_time(dt=None):
    """格式化为北京时间字符串"""
    if dt is None:
        dt = get_beijing_time()
    elif dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC并转换
        dt = dt.replace(tzinfo=timezone.utc).astimezone(BEIJING_TZ)
    return dt.strftime('%Y-%m-%d %H:%M:%S') + ' (北京时间)'


class DataManager:
    """数据管理器"""
    
    def __init__(self, data_dir: str = "data", articles_dir: str = "articles"):
        self.data_dir = data_dir
        self.articles_dir = articles_dir
        self.history_file = os.path.join(data_dir, "history.json")
        self.favorites_file = os.path.join(data_dir, "favorites.json")
        
        # 确保目录存在
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(articles_dir, exist_ok=True)
    
    def load_history(self) -> dict:
        """加载历史数据"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"articles": {}, "last_update": None}
    
    def save_history(self, history: dict):
        """保存历史数据（使用北京时间）"""
        history["last_update"] = format_beijing_time()
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def load_favorites(self) -> list:
        """加载收藏列表"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def save_favorites(self, favorites: list):
        """保存收藏列表"""
        with open(self.favorites_file, 'w', encoding='utf-8') as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
    
    def add_favorite(self, article_id: str):
        """添加收藏"""
        favorites = self.load_favorites()
        if article_id not in favorites:
            favorites.append(article_id)
            self.save_favorites(favorites)
    
    def remove_favorite(self, article_id: str):
        """移除收藏"""
        favorites = self.load_favorites()
        if article_id in favorites:
            favorites.remove(article_id)
            self.save_favorites(favorites)
    
    def get_new_articles(self, articles: list) -> list:
        """获取新文献（不在历史记录中的）"""
        history = self.load_history()
        existing_ids = set(history.get("articles", {}).keys())
        return [a for a in articles if a.id not in existing_ids]
    
    def add_articles(self, articles: list):
        """添加文献到历史记录"""
        history = self.load_history()
        
        for article in articles:
            history["articles"][article.id] = article.to_dict()
        
        self.save_history(history)
    
    def generate_markdown(self, article: Article) -> str:
        """生成Markdown文件内容"""
        authors_str = ", ".join(article.authors) if article.authors else "未知"
        
        # 处理标题中的引号
        title_escaped = article.title.replace('"', "'")
        title_zh_escaped = article.title_zh.replace('"', "'") if article.title_zh else ""
        
        md_content = f"""---
id: {article.id}
title: "{title_escaped}"
title_zh: "{title_zh_escaped}"
date: {article.pub_date}
journal: "{article.journal}"
authors: "{authors_str}"
link: "{article.link}"
---

# {article.title}

## 中文标题
{article.title_zh}

## 基本信息
- **期刊**: {article.journal}
- **作者**: {authors_str}
- **发表日期**: {article.pub_date}
- **原文链接**: [{article.link}]({article.link})

## Abstract
{article.abstract}

## 摘要（中文）
{article.abstract_zh}
"""
        return md_content
    
    def save_article_markdown(self, article: Article) -> str:
        """保存文献为Markdown文件"""
        filename = f"{article.pub_date}_{article.id}.md"
        filepath = os.path.join(self.articles_dir, filename)
        
        content = self.generate_markdown(article)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def generate_index_json(self) -> str:
        """生成索引JSON文件供网页使用"""
        import config
        
        history = self.load_history()
        favorites = self.load_favorites()
        
        articles_list = []
        for article_id, data in history.get("articles", {}).items():
            data["is_favorite"] = article_id in favorites
            articles_list.append(data)
        
        # 按日期排序
        articles_list.sort(key=lambda x: x.get("pub_date", ""), reverse=True)
        
        # 获取用户关键词配置
        user_keywords = getattr(config, 'USER_KEYWORDS', {})
        
        index_data = {
            "articles": articles_list,
            "total": len(articles_list),
            "last_update": history.get("last_update"),
            "favorites_count": len(favorites),
            "user_keywords": user_keywords,  # 添加用户关键词配置
        }
        
        index_file = os.path.join(self.data_dir, "index.json")
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        return index_file
