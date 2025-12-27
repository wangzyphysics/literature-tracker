"""
文献去重模块 - 基于DOI和标题相似度去重
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional


class Deduplicator:
    """文献去重器"""
    
    def __init__(self, similarity_threshold: float = 0.9):
        """
        初始化去重器
        
        Args:
            similarity_threshold: 标题相似度阈值（0-1），默认0.9
        """
        self.similarity_threshold = similarity_threshold
    
    def deduplicate(self, articles: List) -> Tuple[List, int]:
        """
        对文献列表进行去重
        
        Args:
            articles: 文献列表
            
        Returns:
            Tuple[List, int]: (去重后的文献列表, 去除的重复数量)
        """
        if not articles:
            return [], 0
        
        # 按DOI分组
        doi_groups: Dict[str, List] = {}
        no_doi_articles: List = []
        
        for article in articles:
            doi = self._extract_doi(article)
            if doi:
                if doi not in doi_groups:
                    doi_groups[doi] = []
                doi_groups[doi].append(article)
            else:
                no_doi_articles.append(article)
        
        # 处理有DOI的文献 - 每组保留最完整的
        unique_articles = []
        doi_duplicates = 0
        
        for doi, group in doi_groups.items():
            if len(group) > 1:
                doi_duplicates += len(group) - 1
                best = self._select_best_article(group)
                unique_articles.append(best)
            else:
                unique_articles.append(group[0])
        
        # 处理无DOI的文献 - 基于标题相似度去重
        title_duplicates = 0
        for article in no_doi_articles:
            is_duplicate = False
            for existing in unique_articles:
                if self._is_title_similar(article.title, existing.title):
                    is_duplicate = True
                    title_duplicates += 1
                    # 如果新文献信息更完整，替换
                    if self._get_completeness_score(article) > self._get_completeness_score(existing):
                        unique_articles.remove(existing)
                        unique_articles.append(article)
                    break
            
            if not is_duplicate:
                unique_articles.append(article)
        
        total_duplicates = doi_duplicates + title_duplicates
        return unique_articles, total_duplicates
    
    def _extract_doi(self, article) -> Optional[str]:
        """
        从文献中提取DOI
        
        Args:
            article: 文献对象
            
        Returns:
            Optional[str]: DOI字符串或None
        """
        # 检查article对象是否有doi属性
        if hasattr(article, 'doi') and article.doi:
            return self._normalize_doi(article.doi)
        
        # 从链接中提取DOI
        if hasattr(article, 'link') and article.link:
            doi = self._extract_doi_from_url(article.link)
            if doi:
                return doi
        
        # 从摘要中提取DOI
        if hasattr(article, 'abstract') and article.abstract:
            doi = self._extract_doi_from_text(article.abstract)
            if doi:
                return doi
        
        return None
    
    def _extract_doi_from_url(self, url: str) -> Optional[str]:
        """从URL中提取DOI"""
        if not url:
            return None
        
        # 常见DOI URL模式
        patterns = [
            r'doi\.org/(10\.\d{4,}/[^\s&?#]+)',
            r'dx\.doi\.org/(10\.\d{4,}/[^\s&?#]+)',
            r'doi/(10\.\d{4,}/[^\s&?#]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return self._normalize_doi(match.group(1))
        
        return None
    
    def _extract_doi_from_text(self, text: str) -> Optional[str]:
        """从文本中提取DOI"""
        if not text:
            return None
        
        # DOI模式
        pattern = r'10\.\d{4,}/[^\s<>"\'&?#]+'
        match = re.search(pattern, text)
        if match:
            return self._normalize_doi(match.group(0))
        
        return None
    
    def _normalize_doi(self, doi: str) -> str:
        """标准化DOI格式"""
        if not doi:
            return ""
        
        # 移除URL前缀
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        
        # 移除尾部标点
        doi = doi.rstrip('.,;:')
        
        # 转小写
        return doi.lower().strip()
    
    def _is_title_similar(self, title1: str, title2: str) -> bool:
        """
        判断两个标题是否相似
        
        Args:
            title1: 第一个标题
            title2: 第二个标题
            
        Returns:
            bool: 是否相似
        """
        if not title1 or not title2:
            return False
        
        # 标准化标题
        t1 = self._normalize_title(title1)
        t2 = self._normalize_title(title2)
        
        # 完全相同
        if t1 == t2:
            return True
        
        # 计算相似度
        similarity = SequenceMatcher(None, t1, t2).ratio()
        return similarity >= self.similarity_threshold
    
    def _normalize_title(self, title: str) -> str:
        """标准化标题用于比较"""
        if not title:
            return ""
        
        # 转小写
        title = title.lower()
        
        # 移除特殊字符
        title = re.sub(r'[^\w\s]', '', title)
        
        # 移除多余空格
        title = ' '.join(title.split())
        
        return title
    
    def _select_best_article(self, articles: List) -> object:
        """
        从重复文献中选择信息最完整的
        
        Args:
            articles: 重复文献列表
            
        Returns:
            最完整的文献对象
        """
        if not articles:
            return None
        
        if len(articles) == 1:
            return articles[0]
        
        # 按完整度评分排序
        scored = [(a, self._get_completeness_score(a)) for a in articles]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[0][0]
    
    def _get_completeness_score(self, article) -> int:
        """
        计算文献信息完整度评分
        
        Args:
            article: 文献对象
            
        Returns:
            int: 完整度评分
        """
        score = 0
        
        # 标题
        if hasattr(article, 'title') and article.title:
            score += 10
        
        # 中文标题
        if hasattr(article, 'title_zh') and article.title_zh:
            score += 5
        
        # 摘要
        if hasattr(article, 'abstract') and article.abstract:
            score += 10
            # 摘要长度加分
            score += min(len(article.abstract) // 100, 10)
        
        # 中文摘要
        if hasattr(article, 'abstract_zh') and article.abstract_zh:
            score += 5
        
        # 作者
        if hasattr(article, 'authors') and article.authors:
            score += 5
            score += min(len(article.authors), 5)
        
        # 期刊
        if hasattr(article, 'journal') and article.journal:
            score += 5
        
        # 日期
        if hasattr(article, 'pub_date') and article.pub_date:
            score += 3
        
        # 链接
        if hasattr(article, 'link') and article.link:
            score += 2
        
        return score
