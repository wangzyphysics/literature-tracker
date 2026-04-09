"""
摘要爬取模块 - 从网页获取文献摘要
用于补充RSS中缺失或不完整的摘要信息
"""

import requests
import re
import time
from bs4 import BeautifulSoup
from typing import Optional, Tuple
from urllib.parse import urlparse


class AbstractScraper:
    """摘要爬取器"""
    
    # 请求头，模拟浏览器
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    # 不同网站的摘要选择器配置
    SITE_CONFIGS = {
        'nature.com': {
            'selectors': [
                'div#Abs1-content p',
                'div.c-article-section__content p',
                'section[data-title="Abstract"] p',
                'div#abstract-content p',
                'meta[name="description"]',
            ],
            'meta_attr': 'content'
        },
        'science.org': {
            'selectors': [
                'div.section.abstract p',
                'section.abstract p',
                'div#abstract p',
                'meta[name="description"]',
            ],
            'meta_attr': 'content'
        },
        'acs.org': {
            'selectors': [
                'div.article_abstract p',
                'p.articleBody_abstractText',
                'div#abstractBox p',
                'meta[name="dc.Description"]',
                'meta[name="description"]',
            ],
            'meta_attr': 'content'
        },
        'wiley.com': {
            'selectors': [
                'div.article-section__content.en.main p',
                'section.article-section__abstract p',
                'div#abstract p',
                'meta[name="citation_abstract"]',
                'meta[name="description"]',
            ],
            'meta_attr': 'content'
        },
        'arxiv.org': {
            'selectors': [
                'blockquote.abstract',
                'div.abstract',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'pnas.org': {
            'selectors': [
                'div#abstract-1 p',
                'section.abstract p',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'aip.org': {
            'selectors': [
                'div.abstract p',
                'section.abstract p',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'iop.org': {
            'selectors': [
                'div.article-content__abstract p',
                'div#articleAbsctract p',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'aps.org': {
            'selectors': [
                'section.abstract p',
                'div.abstract p',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'sciencedirect.com': {
            'selectors': [
                'div.abstract.author p',
                'div#abstracts p',
                'meta[name="citation_abstract"]',
            ],
            'meta_attr': 'content'
        },
        'default': {
            'selectors': [
                'meta[name="citation_abstract"]',
                'meta[name="dc.description"]',
                'meta[name="description"]',
                'meta[property="og:description"]',
                'div.abstract p',
                'section.abstract p',
                '#abstract p',
                '.abstract p',
            ],
            'meta_attr': 'content'
        }
    }
    
    # 判断摘要是否有效的最小长度
    MIN_ABSTRACT_LENGTH = 100
    
    # 无效摘要的特征模式
    INVALID_PATTERNS = [
        r'^[\w\s]+,?\s*(?:Published|Online|DOI|doi)',  # 期刊信息开头
        r'^DOI:?\s*10\.',  # DOI开头
        r'^\d{4}-\d{2}-\d{2}',  # 日期开头
        r'^Volume\s+\d+',  # Volume开头
        r'^Issue\s+\d+',  # Issue开头
        r'^pp?\.\s*\d+',  # 页码开头
        r'^https?://',  # URL开头
    ]
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def is_abstract_valid(self, abstract: str) -> bool:
        """
        判断摘要是否有效（包含实际内容）
        
        Args:
            abstract: 摘要文本
            
        Returns:
            bool: 是否有效
        """
        if not abstract:
            return False
        
        # 清理空白字符
        clean = abstract.strip()
        
        # 长度检查
        if len(clean) < self.MIN_ABSTRACT_LENGTH:
            return False
        
        # 检查无效模式
        for pattern in self.INVALID_PATTERNS:
            if re.match(pattern, clean, re.IGNORECASE):
                return False
        
        # 检查是否主要是期刊元信息
        meta_keywords = ['doi:', 'published', 'volume', 'issue', 'pages', 
                        '期刊', '杂志', '在线发布', '出版']
        meta_count = sum(1 for kw in meta_keywords if kw.lower() in clean.lower())
        
        # 如果元信息关键词占比过高，认为无效
        word_count = len(clean.split())
        if word_count < 30 and meta_count >= 2:
            return False
        
        return True
    
    def scrape_abstract(self, url: str) -> Tuple[Optional[str], str]:
        """
        从网页爬取摘要
        
        Args:
            url: 文献链接
            
        Returns:
            Tuple[Optional[str], str]: (摘要文本, 状态信息)
        """
        if not url:
            return None, "URL为空"
        
        try:
            # 获取网站配置
            domain = self._get_domain(url)
            config = self._get_site_config(domain)
            
            # 发送请求
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            response.raise_for_status()
            
            # 解析HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 尝试各种选择器
            for selector in config['selectors']:
                abstract = self._extract_by_selector(soup, selector, config.get('meta_attr', 'content'))
                if abstract and self.is_abstract_valid(abstract):
                    return abstract, "成功"
            
            return None, "未找到有效摘要"
            
        except requests.Timeout:
            return None, "请求超时"
        except requests.RequestException as e:
            return None, f"请求失败: {str(e)[:50]}"
        except Exception as e:
            return None, f"解析失败: {str(e)[:50]}"
    
    def _get_domain(self, url: str) -> str:
        """提取域名"""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""
    
    def _get_site_config(self, domain: str) -> dict:
        """获取网站配置"""
        for site_key, config in self.SITE_CONFIGS.items():
            if site_key in domain:
                return config
        return self.SITE_CONFIGS['default']
    
    def _extract_by_selector(self, soup: BeautifulSoup, selector: str, meta_attr: str) -> Optional[str]:
        """使用选择器提取文本"""
        try:
            # 检查是否是meta标签选择器
            if selector.startswith('meta['):
                element = soup.select_one(selector)
                if element:
                    return element.get(meta_attr, '').strip()
            else:
                elements = soup.select(selector)
                if elements:
                    # 合并所有匹配元素的文本
                    texts = [el.get_text(strip=True) for el in elements]
                    combined = ' '.join(texts)
                    # 清理多余空白
                    combined = re.sub(r'\s+', ' ', combined).strip()
                    # 移除"Abstract"前缀
                    combined = re.sub(r'^Abstract[:\s]*', '', combined, flags=re.IGNORECASE)
                    return combined
        except Exception:
            pass
        return None


def enhance_article_abstract(article, scraper: AbstractScraper, translator_func) -> bool:
    """
    增强文献摘要：如果原摘要无效，尝试从网页爬取
    
    Args:
        article: Article对象
        scraper: AbstractScraper实例
        translator_func: 翻译函数
        
    Returns:
        bool: 是否成功增强
    """
    # 检查原摘要是否有效
    if scraper.is_abstract_valid(article.abstract):
        return False  # 原摘要有效，无需增强
    
    print(f"    📄 摘要不完整，尝试从网页获取...")
    
    # 爬取摘要
    new_abstract, status = scraper.scrape_abstract(article.link)
    
    if new_abstract:
        # 保留原有信息，添加新摘要
        if article.abstract:
            article.abstract = f"{new_abstract}\n\n[原始信息] {article.abstract}"
        else:
            article.abstract = new_abstract
        
        # 翻译新摘要
        article.abstract_zh = translator_func(new_abstract)
        
        print(f"    ✅ 成功获取摘要 ({len(new_abstract)} 字符)")
        return True
    else:
        print(f"    ⚠️ 无法获取摘要: {status}")
        return False


# 测试函数
if __name__ == "__main__":
    scraper = AbstractScraper()
    
    # 测试URL
    test_urls = [
        "https://www.nature.com/articles/s41467-025-67884-1",
        "https://pubs.acs.org/doi/10.1021/acs.jctc.5c01293",
    ]
    
    for url in test_urls:
        print(f"\n测试: {url}")
        abstract, status = scraper.scrape_abstract(url)
        if abstract:
            print(f"状态: {status}")
            print(f"摘要: {abstract[:200]}...")
        else:
            print(f"失败: {status}")
