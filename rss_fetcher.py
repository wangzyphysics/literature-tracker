"""
RSS抓取模块 - 从RSS源获取文献信息
"""

import feedparser
import hashlib
import re
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from typing import Optional
from bs4 import BeautifulSoup

# 北京时间 UTC+8，用于统一存储 pub_date 为「北京时间的日历日」，避免 Actions(UTC) 与统计日期时差
BEIJING_TZ = timezone(timedelta(hours=8))


class Article:
    """文献数据类"""
    
    def __init__(self, title: str, abstract: str, authors: list, 
                 pub_date: str, journal: str, link: str, source_url: str):
        self.title = title
        self.abstract = abstract
        self.authors = authors
        self.pub_date = pub_date
        self.journal = journal
        self.link = link
        self.source_url = source_url
        self.id = self._generate_id()
        
        # 翻译后的字段
        self.title_zh = ""
        self.abstract_zh = ""
    
    def _generate_id(self) -> str:
        """生成唯一ID"""
        content = f"{self.title}{self.link}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "title_zh": self.title_zh,
            "abstract": self.abstract,
            "abstract_zh": self.abstract_zh,
            "authors": self.authors,
            "pub_date": self.pub_date,
            "journal": self.journal,
            "link": self.link,
            "source_url": self.source_url,
            "fetch_time": datetime.now().isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Article':
        """从字典创建实例"""
        article = cls(
            title=data.get("title", ""),
            abstract=data.get("abstract", ""),
            authors=data.get("authors", []),
            pub_date=data.get("pub_date", ""),
            journal=data.get("journal", ""),
            link=data.get("link", ""),
            source_url=data.get("source_url", ""),
        )
        article.id = data.get("id", article.id)
        article.title_zh = data.get("title_zh", "")
        article.abstract_zh = data.get("abstract_zh", "")
        return article


class RSSFetcher:
    """RSS抓取器"""
    
    # 期刊名称映射
    JOURNAL_MAP = {
        "feeds.aps.org": "APS",
        "nature.com": "Nature",
        "science.org": "Science",
        "acs.org": "ACS",
        "wiley.com": "Wiley",
        "arxiv.org": "arXiv",
        "pnas.org": "PNAS",
        "aip.scitation.org": "AIP",
        "pubs.aip.org": "AIP",
        "iopscience.iop.org": "IOP",
        "phys.org": "Phys.org",
        "chemrxiv.org": "ChemRxiv",
        "researchsquare.com": "Research Square",
        "annualreviews.org": "Annual Reviews",
        "academic.oup.com": "Oxford Academic",
        "sciencedirect.com": "ScienceDirect",
    }
    
    def __init__(self, keywords: list):
        self.keywords = [kw.lower() for kw in keywords]
    
    def fetch_feed(self, url: str) -> list:
        """抓取单个RSS源"""
        articles = []
        try:
            feed = feedparser.parse(url)
            journal = self._get_journal_name(url, feed)
            
            for entry in feed.entries:
                article = self._parse_entry(entry, url, journal)
                if article:
                    articles.append(article)
        except Exception as e:
            print(f"抓取失败 {url}: {e}")
        
        return articles
    
    def fetch_all(self, urls: list) -> list:
        """抓取所有RSS源"""
        all_articles = []
        for url in urls:
            print(f"正在抓取: {url}")
            articles = self.fetch_feed(url)
            all_articles.extend(articles)
            print(f"  获取 {len(articles)} 篇文献")
        
        return all_articles
    
    def filter_by_keywords(self, articles: list) -> list:
        """根据关键词筛选文献"""
        filtered = []
        for article in articles:
            text = f"{article.title} {article.abstract}".lower()
            if any(kw in text for kw in self.keywords):
                filtered.append(article)
        return filtered
    
    def _parse_entry(self, entry, source_url: str, journal: str) -> Optional[Article]:
        """解析RSS条目"""
        try:
            title = self._clean_html(entry.get("title", ""))
            if not title:
                return None
            
            # 获取摘要
            abstract = ""
            if "summary" in entry:
                abstract = self._clean_html(entry.summary)
            elif "description" in entry:
                abstract = self._clean_html(entry.description)
            elif "content" in entry and entry.content:
                abstract = self._clean_html(entry.content[0].get("value", ""))
            
            # 获取作者
            authors = self._parse_authors(entry)
            
            # 获取发布日期
            pub_date = self._parse_date(entry)
            
            # 获取链接
            link = entry.get("link", "")
            
            return Article(
                title=title,
                abstract=abstract,
                authors=authors,
                pub_date=pub_date,
                journal=journal,
                link=link,
                source_url=source_url,
            )
        except Exception as e:
            print(f"解析条目失败: {e}")
            return None
    
    def _clean_html(self, text: str) -> str:
        """清理HTML标签"""
        if not text:
            return ""
        soup = BeautifulSoup(text, "html.parser")
        clean = soup.get_text(separator=" ")
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def _parse_authors(self, entry) -> list:
        """解析作者信息"""
        authors = []
        
        if "authors" in entry:
            for author in entry.authors:
                name = author.get("name", "")
                if name:
                    authors.append(name)
        elif "author" in entry:
            authors.append(entry.author)
        elif "dc_creator" in entry:
            authors.append(entry.dc_creator)
        
        return authors
    
    def _parse_date(self, entry) -> str:
        """
        解析发布日期，统一为北京时间的日历日 (YYYY-MM-DD)。
        RSS 时间多为 UTC，Actions 运行在 UTC；统一转为北京时间再取日期，避免「今天」在 UTC 与北京不一致导致漏筛/多筛。
        """
        date_str = ""
        for field in ["published", "updated", "created", "dc_date"]:
            if field in entry:
                date_str = entry[field]
                break
        if date_str:
            try:
                dt = date_parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                beijing_dt = dt.astimezone(BEIJING_TZ)
                return beijing_dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    
    def _get_journal_name(self, url: str, feed) -> str:
        """获取期刊名称"""
        # 先尝试从feed标题获取
        if feed.feed.get("title"):
            title = feed.feed.title
            
            # 移除 "Recent Articles in " 前缀
            if title.startswith("Recent Articles in "):
                title = title.replace("Recent Articles in ", "")
            
            # 清理标题
            if " - " in title:
                title = title.split(" - ")[0]
            
            if len(title) < 50:
                return title
        
        # 从URL推断
        for domain, name in self.JOURNAL_MAP.items():
            if domain in url:
                return name
        
        return "Unknown"
