"""
RSS抓取模块 - 从RSS源获取文献信息
"""

import feedparser
import hashlib
import os
import re
from datetime import datetime, timezone, timedelta
from dateutil import parser as date_parser
from typing import Optional
from bs4 import BeautifulSoup
from author_utils import normalize_author_names
from focus_filter import is_target_domain
from text_normalizer import normalize_text

# 北京时间 UTC+8，用于统一存储 pub_date 为「北京时间的日历日」，避免 Actions(UTC) 与统计日期时差
BEIJING_TZ = timezone(timedelta(hours=8))


class Article:
    """文献数据类"""
    
    def __init__(self, title: str, abstract: str, authors: list, 
                 pub_date: str, journal: str, link: str, source_url: str, arxiv_category: str = ""):
        self.title = normalize_text(title)
        self.abstract = normalize_text(abstract)
        self.authors = normalize_author_names(authors)
        self.pub_date = pub_date
        self.journal = normalize_text(journal)
        self.link = link
        self.source_url = source_url
        self.arxiv_category = arxiv_category
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
            "arxiv_category": self.arxiv_category,
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
            arxiv_category=data.get("arxiv_category", ""),
        )
        article.id = data.get("id", article.id)
        article.title_zh = normalize_text(data.get("title_zh", ""))
        article.abstract_zh = normalize_text(data.get("abstract_zh", ""))
        article.arxiv_category = data.get("arxiv_category", article.arxiv_category)
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
        "rss.arxiv.org": "arXiv",
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

        # 常见时区缩写映射（dateutil 无法识别时会给出 UnknownTimezoneWarning）
        self._tzinfos = {
            "UTC": timezone.utc,
            "GMT": timezone.utc,
            "EST": timezone(timedelta(hours=-5)),
            "EDT": timezone(timedelta(hours=-4)),
            "CST": timezone(timedelta(hours=-6)),
            "CDT": timezone(timedelta(hours=-5)),
            "MST": timezone(timedelta(hours=-7)),
            "MDT": timezone(timedelta(hours=-6)),
            "PST": timezone(timedelta(hours=-8)),
            "PDT": timezone(timedelta(hours=-7)),
        }
    
    def fetch_feed(self, url: str) -> list:
        """抓取单个RSS源"""
        articles = []
        try:
            feed = feedparser.parse(url)
            journal = self._get_journal_name(url, feed)

            # Some feeds (e.g., Research Square) can return 1000+ entries, which is wasteful and slows Actions.
            # Keep it configurable; default keeps enough recent history for daily/weekly summaries.
            try:
                max_entries = int((os.environ.get("RSS_MAX_ENTRIES_PER_FEED", "200") or "200").strip())
            except Exception:
                max_entries = 200
            entries = feed.entries if max_entries <= 0 else feed.entries[:max_entries]

            for entry in entries:
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
            if any(kw in text for kw in self.keywords) and is_target_domain(article.to_dict()):
                filtered.append(article)
        return filtered
    
    def _parse_entry(self, entry, source_url: str, journal: str) -> Optional[Article]:
        """解析RSS条目"""
        if not hasattr(entry, "get"):
            return None
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

            arxiv_category = self._infer_arxiv_category(source_url)
            
            return Article(
                title=title,
                abstract=abstract,
                authors=authors,
                pub_date=pub_date,
                journal=journal,
                link=link,
                source_url=source_url,
                arxiv_category=arxiv_category,
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
        return normalize_text(clean)
    
    def _parse_authors(self, entry) -> list:
        """解析作者信息"""
        authors = []
        
        if "authors" in entry:
            for author in entry.authors:
                if isinstance(author, dict):
                    name = author.get("name", "")
                else:
                    name = str(author or "")
                if name:
                    authors.append(name)
        elif "author" in entry:
            authors.append(entry.author)
        elif "dc_creator" in entry:
            authors.append(entry.dc_creator)
        
        return normalize_author_names(authors)
    
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
                dt = date_parser.parse(date_str, tzinfos=self._tzinfos)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                beijing_dt = dt.astimezone(BEIJING_TZ)
                return beijing_dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        return datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    
    def _get_journal_name(self, url: str, feed) -> str:
        """获取期刊名称"""
        # arXiv RSS 的 feed.title 往往是 "cs.LG updates on arXiv.org" 之类，
        # 这会导致前端/周报的期刊筛选无法匹配 "arXiv"。
        # 因此优先统一期刊名为 "arXiv"，分类信息写入 arxiv_category 字段。
        if "rss.arxiv.org/rss/" in url or "arxiv.org" in url:
            return "arXiv"

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

    def _infer_arxiv_category(self, source_url: str) -> str:
        """Infer arXiv category from RSS source url."""
        source_url = (source_url or "").strip()
        if not source_url:
            return ""
        marker = "/rss/"
        if marker not in source_url:
            return ""
        try:
            cat = source_url.split(marker, 1)[1]
            return cat.strip()
        except Exception:
            return ""
