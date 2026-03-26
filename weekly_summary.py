#!/usr/bin/env python3
"""
周报生成器 - 每周总结Nature/Science系列的磁性/铁电工作
"""

import os
import json
import requests
import html
from urllib.parse import urlparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from ai_summarizer import build_provider
from abstract_scraper import AbstractScraper
from translator import translate_text
from concurrent.futures import ThreadPoolExecutor, as_completed
from weekly_page_enhancer import enhance_weekly_archive
import time
from abstract_scraper import AbstractScraper
from translator import translate_text

try:
    from config import AI_CONFIG as DEFAULT_AI_CONFIG
except ImportError:
    DEFAULT_AI_CONFIG = {}


def _safe_text(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _safe_multiline(value) -> str:
    return _safe_text(value).replace("\n", "<br/>")


def _safe_url(value) -> str:
    url = str(value or "").strip()
    if not url:
        return "#"
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return "#"
    except Exception:
        return "#"
    return html.escape(url, quote=True)


def _safe_id(value) -> str:
    raw = str(value or "")
    cleaned = "".join(c if (c.isalnum() or c in "-_") else "_" for c in raw)
    return cleaned or "x"


class WeeklySummarizer:
    """周报生成器"""
    
    # 顶刊列表 - 精确匹配，避免误匹配
    TOP_JOURNALS = [
        # Nature 系列
        'Nature',
        'Nature Materials',
        'Nature Physics',
        'Nature Chemistry',
        'Nature Communications',
        'Nature Nanotechnology',
        'Nature Electronics',
        'Nature Energy',
        'Nat. Mater.',
        'Nat. Phys.',
        'Nat. Chem.',
        'Nat. Commun.',
        'Nat. Nanotechnol.',
        'Nat. Electron.',
        'Nat. Energy',
        # Science 系列（注意：只包含正刊，不包含 ScienceDirect）
        'Science',
        'Science Advances',
        'Sci. Adv.',
        # 其他顶刊
        'Physical Review Letters',
        'Phys. Rev. Lett.',
        'PRL',
        'Advanced Materials',
        'Adv. Mater.'
        ,
        # arXiv（允许非常相关的预印本出现在周报）
        'arXiv'
    ]
    
    # 磁性/铁电关键词
    FERRO_KEYWORDS = [
        'ferroelectric', 'ferromagnet', 'multiferroic', 'piezoelectric',
        'antiferroelectric', 'antiferromagnet', 'magnetoelectric',
        'polarization', 'magnetization', 'domain wall', 'skyrmion',
        'spin', 'magnetic', 'ferroic', 'perovskite',
        '铁电', '铁磁', '多铁', '压电', '反铁电', '反铁磁', '磁电',
        '极化', '磁化', '畴壁', '斯格明子', '自旋', '磁性', '铁性'
    ]
    
    # AI/机器学习关键词（使用更精确的匹配，避免误匹配神经科学内容）
    AI_KEYWORDS = [
        'machine learning', 'deep learning', 'neural network', 'artificial intelligence',
        'graph neural network', 'graph neural', 'transformer', 'gnn', 'mlip', 'ml potential', 
        'machine-learn', 'ai-driven', 'data-driven', 'convolutional neural', 'recurrent neural',
        'reinforcement learning', 'generative model', 'diffusion model', 
        'large language model', 'llm', 'transformer model', 'attention mechanism',
        '机器学习', '深度学习', '神经网络', '人工智能', '生成式', '卷积神经网络', '循环神经网络'
    ]
    
    def __init__(self, api_key: str = None, provider: str = None, model: str = None):
        """初始化周报生成器"""
        api_key = (
            (api_key or "").strip()
            or (os.environ.get("AI_API_KEY") or "").strip()
            or (DEFAULT_AI_CONFIG.get("api_key") if isinstance(DEFAULT_AI_CONFIG, dict) else "")  # type: ignore[arg-type]
        )
        provider = (
            (provider or "").strip()
            or (os.environ.get("AI_PROVIDER") or "").strip()
            or (DEFAULT_AI_CONFIG.get("provider") if isinstance(DEFAULT_AI_CONFIG, dict) else "gemini")  # type: ignore[arg-type]
            or "gemini"
        )
        model = (
            (model or "").strip()
            or (os.environ.get("AI_MODEL") or "").strip()
            or (DEFAULT_AI_CONFIG.get("model") if isinstance(DEFAULT_AI_CONFIG, dict) else "")  # type: ignore[arg-type]
        ) or None
        
        if api_key:
            self.provider = build_provider(provider, api_key, model=model)
        else:
            self.provider = None
            print("⚠️ 未配置AI API密钥，将使用基础模板")
        
        # 初始化摘要爬取器
        self.abstract_scraper = AbstractScraper()
    
    def _loose_matches_ferro_keywords(self, text: str) -> bool:
        """宽松的关键词匹配（第一步筛选，获取更多候选）"""
        text_lower = text.lower()
        
        # 宽松的关键词列表（包含更多可能相关的词）
        loose_keywords = [
            # 核心关键词
            'ferroelectric', 'ferromagnet', 'multiferroic', 'piezoelectric',
            'antiferroelectric', 'antiferromagnet', 'magnetoelectric',
            'domain wall', 'skyrmion', 'ferroic', 'perovskite', 'ferro',
            '铁电', '铁磁', '多铁', '压电', '反铁电', '反铁磁', '磁电',
            '畴壁', '斯格明子', '铁性',
            # 扩展关键词（更宽松）
            'polarization', 'magnetization', 'spin', 'magnetic', 'magnet',
            '极化', '磁化', '自旋', '磁性', '磁',
            # 相关物理概念
            'spintronic', 'topological', 'quantum', 'hall effect',
            '自旋电子', '拓扑', '量子', '霍尔效应',
            # 材料相关
            '2d material', 'van der waals', 'heterostructure',
            '二维材料', '范德华', '异质结'
        ]
        
        # 简单匹配：只要包含关键词就认为可能相关
        for keyword in loose_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def _matches_ferro_keywords(self, text: str) -> bool:
        """检查文本是否匹配铁性关键词（精确匹配）- 保留用于其他场景"""
        return self._loose_matches_ferro_keywords(text)
    
    def _loose_matches_ai_keywords(self, text: str) -> bool:
        """宽松的AI关键词匹配（第一步筛选，获取更多候选）"""
        text_lower = text.lower()
        
        # 宽松的关键词列表（包含更多可能相关的词）
        loose_keywords = [
            # 核心关键词
            'learning', 'artificial intelligence',
            'network', 'neural', 'transformer', 'gnn',
            'mlip', 'ml potential', 'machine-learn', 'ai-driven', 'data-driven',
            'convolutional neural', 'recurrent neural', 'reinforcement learning',
            'generative model', 'diffusion model', 'large language model', 'llm',
            'transformer model', 'attention mechanism',
            '机器学习', '深度学习', '神经网络', '人工智能', '生成式',
            '卷积神经网络', '循环神经网络',
            # 扩展关键词（更宽松）
            'neural network', 'neural', 'network', 'learning', 'model',
            'algorithm', 'prediction', 'classification', 'optimization',
            '神经网络', '学习', '模型', '算法', '预测', '分类', '优化',
            # AI在科学中的应用
            'ml potential', 'mlip', 'dft', 'quantum', 'molecular',
            '材料发现', '性质预测', '分子设计'
        ]
        
        # 简单匹配：只要包含关键词就认为可能相关
        for keyword in loose_keywords:
            if keyword.lower() in text_lower:
                return True
        
        return False
    
    def _matches_ai_keywords(self, text: str) -> bool:
        """检查文本是否匹配AI关键词（精确匹配）- 保留用于其他场景"""
        return self._loose_matches_ai_keywords(text)
    
    def _ai_judge_ai_relevance(self, text: str) -> bool:
        """使用AI判断文本是否与AI/机器学习相关（用于边缘情况）"""
        if not self.provider:
            return False
        
        try:
            prompt = f"""请判断以下文献摘要是否与AI/机器学习、材料科学中的AI应用、AI驱动的物理/化学研究相关。

判断标准：
1. 明确使用机器学习、深度学习、神经网络等方法
2. AI在材料科学、物理、化学中的应用（如MLIP、材料发现、性质预测）
3. 数据驱动的科学研究方法
4. 排除：纯神经科学、生物学中的神经网络（除非明确是AI方法）

摘要：
{text[:1000]}

请只回答"是"或"否"，不要其他内容："""
            
            response = self.provider.call_api(prompt)
            return '是' in response or 'yes' in response.lower()
        except:
            return False
    
    def _ai_judge_ferro_relevance(self, text: str) -> bool:
        """使用AI判断文本是否与铁性材料相关（用于排除明显不相关的）"""
        if not self.provider:
            return True  # 如果没有AI，默认保留（宽松策略）
        
        try:
            prompt = f"""请判断以下文献是否与铁性材料（铁电、铁磁、多铁、压电等）相关。

判断标准（必须满足至少一条）：
1. 研究铁电、铁磁、多铁、压电材料及其性质
2. 研究极化、磁化、畴壁、斯格明子等铁性物理现象
3. 研究磁电耦合、自旋电子学、拓扑磁性
4. 研究铁性材料的应用（如存储、传感器等）

排除标准（如果符合以下情况，则不是铁性相关）：
- 纯磁性应用（如MRI、磁共振成像）但不涉及材料研究
- 生物磁性（如生物体内的磁性）但不涉及材料研究
- 仅提到"磁"但指的是磁场、磁力等，不涉及铁性材料
- 仅提到"电"但指的是电子、电路等，不涉及铁性材料

文献内容：
{text[:1500]}

请只回答"是"或"否"，不要其他内容："""
            
            response = self.provider.call_api(prompt)
            result = '是' in response or 'yes' in response.lower()
            if not result:
                print(f"    🤖 AI判断：不相关（铁性）")
            return result
        except Exception as e:
            print(f"    ⚠️ AI判断失败: {e}，默认保留")
            return True  # 如果AI判断失败，默认保留（宽松策略）
    
    def _analyze_single_article(self, article: Dict) -> str:
        """为单篇文章生成AI简要分析"""
        if not self.provider:
            return ""
        
        try:
            title = article.get('title_zh') or article.get('title', '')
            abstract = article.get('abstract_zh') or article.get('abstract', '')
            journal = article.get('journal', '')
            
            if not abstract:
                return ""
            
            prompt = f"""请对以下文献进行简要分析，生成一段50-80字的简要总结，突出核心创新点和研究意义。

标题: {title}
期刊: {journal}
摘要: {abstract[:500]}

要求:
1. 用中文输出
2. 50-80字，简洁明了
3. 突出核心创新点
4. 说明研究意义或应用价值
5. 不要重复摘要内容，而是进行分析总结

直接输出分析结果，不要添加任何前缀或格式："""
            
            response = self.provider.call_api(prompt)
            # 清理响应，移除可能的引号、JSON格式或格式
            analysis = response.strip()
            # 移除JSON格式
            if analysis.startswith('{'):
                import json
                try:
                    data = json.loads(analysis)
                    # 尝试提取analysis字段
                    if 'analysis' in data:
                        analysis = data['analysis']
                    elif 'summary' in data:
                        analysis = data['summary']
                    else:
                        # 如果无法解析，使用原始响应
                        analysis = response.strip()
                except:
                    analysis = response.strip()
            # 移除引号
            analysis = analysis.strip('"').strip("'").strip()
            # 移除可能的markdown格式
            if analysis.startswith('```'):
                lines = analysis.split('\n')
                analysis = '\n'.join([l for l in lines if not l.startswith('```')])
            return analysis[:100]  # 限制长度
            
        except Exception as e:
            print(f"⚠️ 文章分析失败: {e}")
            return ""
    
    def filter_articles(self, articles: List[Dict], start_date: str, end_date: str, category: str = 'all') -> List[Dict]:
        """
        筛选符合条件的文献
        
        Args:
            articles: 文献列表
            start_date: 开始日期
            end_date: 结束日期
            category: 'all' | 'ferro' | 'ai' - 筛选类别
        """
        filtered = []
        
        # 排除关键词（这些不是真正的期刊）
        EXCLUDE_KEYWORDS = [
            'sciencedirect', 'springer', 'table of contents', 'toc',
            'editor', 'suggestion', 'news', 'highlight'
        ]
        
        for article in articles:
            # 检查日期范围
            pub_date = article.get('pub_date', '')
            if not (start_date <= pub_date <= end_date):
                continue
            
            # 检查期刊 - 精确匹配，避免误匹配
            journal = article.get('journal', '')
            if not journal:
                continue
            
            journal_lower = journal.lower()
            
            # 排除非期刊内容
            if any(exclude in journal_lower for exclude in EXCLUDE_KEYWORDS):
                continue
            
            # 精确匹配顶刊列表
            is_top_journal = False
            for top_journal in self.TOP_JOURNALS:
                top_lower = top_journal.lower()
                
                # 精确匹配
                if journal == top_journal:
                    is_top_journal = True
                    break
                
                # 包含匹配（但要小心处理）
                if top_lower in journal_lower:
                    # 特殊处理 Science：必须是 "Science" 或 "Science Advances"，不能是 "ScienceDirect"
                    if top_lower == 'science':
                        if journal_lower == 'science' or journal_lower.startswith('science advances') or journal_lower.startswith('sci. adv'):
                            is_top_journal = True
                            break
                        else:
                            continue
                    else:
                        is_top_journal = True
                        break
            
            if not is_top_journal:
                continue
            
            # 第一步：宽松的关键词筛选（获取更多候选）
            text = ' '.join([
                article.get('title', ''),
                article.get('title_zh', ''),
                article.get('abstract', ''),
                article.get('abstract_zh', '')
            ])
            
            # 宽松匹配
            is_ferro_candidate = False
            is_ai_candidate = False
            
            if category == 'ferro':
                is_ferro_candidate = self._loose_matches_ferro_keywords(text)
            elif category == 'ai':
                is_ai_candidate = self._loose_matches_ai_keywords(text)
            else:  # 'all'
                is_ferro_candidate = self._loose_matches_ferro_keywords(text)
                is_ai_candidate = self._loose_matches_ai_keywords(text)
            
            # 如果宽松匹配失败，直接跳过
            if not (is_ferro_candidate or is_ai_candidate):
                continue
            
            # 第二步：使用AI排除明显不相关的文章
            # 注意：只在有足够文本内容时才使用AI判断（避免对标题等短文本误判）
            if self.provider and len(text.strip()) > 100:
                # 对于铁性候选，用AI判断是否真的相关
                if is_ferro_candidate and category in ['ferro', 'all']:
                    if not self._ai_judge_ferro_relevance(text):
                        is_ferro_candidate = False
                
                # 对于AI候选，用AI判断是否真的相关
                if is_ai_candidate and category in ['ai', 'all']:
                    if not self._ai_judge_ai_relevance(text):
                        is_ai_candidate = False
            
            # 根据最终判断结果添加文章
            if category == 'ferro' and is_ferro_candidate:
                filtered.append(article)
            elif category == 'ai' and is_ai_candidate:
                filtered.append(article)
            elif category == 'all' and (is_ferro_candidate or is_ai_candidate):
                filtered.append(article)
        
        return filtered
    
    def generate_weekly_summary(self, articles: List[Dict], week_start: str) -> Dict:
        """生成周报"""
        # 计算周结束日期
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        end_date = start_date + timedelta(days=6)
        week_end = end_date.strftime('%Y-%m-%d')
        
        # 分别筛选铁性和AI文献
        ferro_articles = self.filter_articles(articles, week_start, week_end, 'ferro')
        ai_articles = self.filter_articles(articles, week_start, week_end, 'ai')
        
        # 合并去重，并识别交叉研究
        all_articles = []
        seen_ids = set()
        ferro_set = set()
        ai_set = set()
        
        # 先建立集合以便快速查找
        for article in ferro_articles:
            article_id = article.get('id') or article.get('link', '')
            ferro_set.add(article_id)
        
        for article in ai_articles:
            article_id = article.get('id') or article.get('link', '')
            ai_set.add(article_id)
        
        # 合并所有文章
        for article in ferro_articles + ai_articles:
            article_id = article.get('id') or article.get('link', '')
            if article_id not in seen_ids:
                all_articles.append(article)
                seen_ids.add(article_id)
        
        if not all_articles:
            return self._empty_summary(week_start, week_end)
        
        # 增强摘要：为所有文章爬取完整摘要并翻译（并行处理）
        print(f"\n📄 正在增强 {len(all_articles)} 篇文章的摘要...")
        
        def enhance_single_article(article_data):
            """增强单篇文章的摘要"""
            i, article = article_data
            link = article.get('link', '')
            current_abstract = article.get('abstract', '')
            enhanced = False
            
            # 检查是否需要爬取摘要
            if not self.abstract_scraper.is_abstract_valid(current_abstract) and link:
                new_abstract, status = self.abstract_scraper.scrape_abstract(link)
                if new_abstract:
                    article['abstract'] = new_abstract
                    # 翻译摘要
                    try:
                        article['abstract_zh'] = translate_text(new_abstract)
                    except Exception as e:
                        article['abstract_zh'] = ""
                    enhanced = True
                    return (i, True, len(new_abstract), None)
                else:
                    return (i, False, 0, status)
            elif current_abstract and not article.get('abstract_zh'):
                # 如果有摘要但没有翻译，进行翻译
                try:
                    article['abstract_zh'] = translate_text(current_abstract)
                except Exception as e:
                    article['abstract_zh'] = ""
            return (i, False, 0, None)
        
        # 并行处理摘要增强（最多5个线程）
        enhanced_count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(enhance_single_article, (i+1, article)): article 
                      for i, article in enumerate(all_articles)}
            
            for future in as_completed(futures):
                try:
                    i, enhanced, length, status = future.result()
                    if enhanced:
                        enhanced_count += 1
                        print(f"  [{i}/{len(all_articles)}] ✅ 成功获取摘要 ({length} 字符)")
                    elif status:
                        print(f"  [{i}/{len(all_articles)}] ⚠️ 无法获取摘要: {status}")
                except Exception as e:
                    print(f"  ⚠️ 处理失败: {e}")
        
        if enhanced_count > 0:
            print(f"📊 共增强 {enhanced_count} 篇文章的摘要")
        
        # 并行处理AI分析（如果启用）
        skip_ai = os.environ.get('SKIP_AI_ANALYSIS', '').lower() == '1'
        if self.provider and not skip_ai:
            print(f"\n🤖 正在并行分析 {len(all_articles)} 篇文章...")
            
            def analyze_article(article_data):
                """分析单篇文章"""
                idx, article = article_data
                title = article.get('title_zh') or article.get('title', '')
                if article.get('ai_analysis'):
                    return (idx, True, None)  # 已有分析
                try:
                    analysis = self._analyze_single_article(article)
                    if analysis:
                        article['ai_analysis'] = analysis
                        return (idx, True, None)
                    return (idx, False, "无分析结果")
                except Exception as e:
                    return (idx, False, str(e))
            
            # 并行处理（最多3个线程，避免API限流）
            analyzed_count = 0
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(analyze_article, (i+1, article)): article 
                          for i, article in enumerate(all_articles)}
                
                for future in as_completed(futures):
                    try:
                        idx, success, error = future.result()
                        if success:
                            analyzed_count += 1
                            if analyzed_count % 5 == 0:
                                print(f"  ✅ 已分析 {analyzed_count}/{len(all_articles)} 篇")
                        elif error:
                            print(f"  [{idx}] ⚠️ 分析失败: {error}")
                    except Exception as e:
                        print(f"  ⚠️ 处理失败: {e}")
            
            print(f"📊 共完成 {analyzed_count} 篇文章的AI分析")
        
        # 按期刊分组
        by_journal = {}
        for article in all_articles:
            journal = article.get('journal', '其他')
            if journal not in by_journal:
                by_journal[journal] = []
            by_journal[journal].append(article)
        
        # 使用AI生成总结（如果可用）
        if self.provider:
            try:
                summary = self._generate_ai_summary(all_articles, ferro_articles, ai_articles, 
                                                   week_start, week_end, by_journal)
                return summary
            except Exception as e:
                print(f"❌ AI生成失败: {e}")
                return self._fallback_summary(all_articles, ferro_articles, ai_articles,
                                             week_start, week_end, by_journal)
        else:
            return self._fallback_summary(all_articles, ferro_articles, ai_articles,
                                         week_start, week_end, by_journal)
    
    def _generate_ai_summary(self, all_articles: List[Dict], ferro_articles: List[Dict], 
                            ai_articles: List[Dict], week_start: str, week_end: str, 
                            by_journal: Dict) -> Dict:
        """使用AI生成周报"""
        
        # 构建提示词 - 使用all_articles包含所有文献
        articles_text = []
        for i, article in enumerate(all_articles, 1):
            title = article.get('title_zh') or article.get('title', '')
            journal = article.get('journal', '')
            link = article.get('link', '')
            abstract = (article.get('abstract_zh') or article.get('abstract', ''))[:400]
            
            # 标记文献类型
            tags = []
            if article in ferro_articles:
                tags.append('铁电')
            if article in ai_articles:
                tags.append('AI/机器学习')
            tag_str = f"[{'/'.join(tags)}]" if tags else ""
            
            articles_text.append(f"""
{i}. {tag_str}【{journal}】{title}
   链接: {link}
   摘要: {abstract}...
""")
        
        articles_str = '\n'.join(articles_text)
        
        prompt = f"""你是一位专业的凝聚态物理/材料科学研究助手。请分析以下{week_start}至{week_end}这一周内，Nature/Science系列期刊发表的{len(all_articles)}篇磁性/铁电/AI相关文献，生成一份专业的周报。

本周共有{len(all_articles)}篇文献，其中：
- 铁电/磁性相关: {len(ferro_articles)}篇
- AI/机器学习相关: {len(ai_articles)}篇

文献列表:
{articles_str}

请按以下格式输出（使用JSON格式）:
{{
    "overview": "本周总览：文献总数、主要研究方向、重要发现（3-4句话）",
    "article_summaries": [
        {{
            "title": "文献标题",
            "link": "原文链接",
            "one_sentence": "一句话总结（30-50字，突出核心创新点）"
        }}
    ],
    "highlights": [
        {{
            "title": "文献标题",
            "journal": "期刊名",
            "link": "原文链接",
            "material": "研究材料体系（如BaTiO3、BiFeO3等）",
            "property": "研究性质（如铁电性、磁性、多铁性等）",
            "method": "研究方法（如第一性原理、实验、机器学习等）",
            "innovation": "核心创新点（50字以内）",
            "significance": "研究意义（30字以内）"
        }}
    ],
    "by_topic": {{
        "铁电材料": ["文献链接1", "文献链接2"],
        "磁性材料": ["文献链接1", "文献链接2"],
        "多铁性材料": ["文献链接1", "文献链接2"],
        "方法学创新": ["文献链接1", "文献链接2"]
    }},
    "trends": "本周研究趋势和热点分析（4-5句话）",
    "outlook": "未来研究方向展望（2-3句话）"
}}

要求:
1. highlights选择5-8篇最重要的文献，优先选择Nature/Science正刊
2. innovation要突出与以往研究的不同之处
3. 使用专业术语，但保持可读性
4. 确保所有链接都是原始文献链接
5. 使用中文输出"""
        
        response = self.provider.call_api(prompt)
        
        # 解析响应
        import re
        json_match = re.search(r'\{[\s\S]*\}', response)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError("无法解析JSON")
        
        # 给每篇文章添加类型标记，并计算统计
        ferro_only = []
        ai_only = []
        both = []
        
        for article in all_articles:
            is_ferro = any(
                a.get('id') == article.get('id') or a.get('link') == article.get('link')
                for a in ferro_articles
            )
            is_ai = any(
                a.get('id') == article.get('id') or a.get('link') == article.get('link')
                for a in ai_articles
            )
            
            article['is_ferro'] = is_ferro
            article['is_ai'] = is_ai
            
            # 分类统计
            if is_ferro and is_ai:
                both.append(article)
            elif is_ferro:
                ferro_only.append(article)
            elif is_ai:
                ai_only.append(article)
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': len(all_articles),
            'ferro_count': len(ferro_articles),
            'ai_count': len(ai_articles),
            'both_count': len(both),
            'overview': data.get('overview', ''),
            'article_summaries': data.get('article_summaries', []),  # 每篇文章的一句话总结
            'highlights': data.get('highlights', []),
            'by_topic': data.get('by_topic', {}),
            'by_journal': by_journal,
            'trends': data.get('trends', ''),
            'outlook': data.get('outlook', ''),
            'all_articles': all_articles,  # 保存所有文献
            'ferro_articles': ferro_only,  # 保存铁电文献（排除交叉）
            'ai_articles': ai_only,  # 保存AI文献（排除交叉）
            'both_articles': both,  # 保存交叉研究文献
            'generated_by': 'gemini'
        }
    
    def _fallback_summary(self, all_articles: List[Dict], ferro_articles: List[Dict], 
                         ai_articles: List[Dict], week_start: str, week_end: str, 
                         by_journal: Dict) -> Dict:
        """降级周报（无AI）- 展示所有文献"""
        
        # 按期刊排序，Nature/Science正刊优先
        def sort_key(a):
            j = a.get('journal', '')
            if j == 'Nature':
                return 0
            elif j == 'Science':
                return 1
            elif 'Nature' in j:
                return 2
            elif 'Science' in j:
                return 3
            elif 'Phys. Rev. Lett.' in j or j == 'PRL':
                return 4
            else:
                return 5
        
        sorted_articles = sorted(all_articles, key=sort_key)
        
        # 统计期刊分布
        journal_stats = {j: len(arts) for j, arts in by_journal.items()}
        journal_list = ', '.join([f"{j}({n}篇)" for j, n in sorted(journal_stats.items(), key=lambda x: -x[1])[:5]])
        
        # 判断文献类别（使用精确匹配方法）
        def get_category(article):
            text = ' '.join([
                article.get('title', ''),
                article.get('title_zh', ''),
                article.get('abstract', ''),
                article.get('abstract_zh', '')
            ])
            
            is_ferro = self._matches_ferro_keywords(text)
            is_ai = self._matches_ai_keywords(text)
            
            if is_ferro and is_ai:
                return 'both'
            elif is_ferro:
                return 'ferro'
            elif is_ai:
                return 'ai'
            else:
                return 'other'
        
        # 分类文献
        ferro_only = []
        ai_only = []
        both = []
        
        for article in sorted_articles:
            cat = get_category(article)
            if cat == 'both':
                both.append(article)
            elif cat == 'ferro':
                ferro_only.append(article)
            elif cat == 'ai':
                ai_only.append(article)
        
        # 给每篇文章添加类型标记
        ferro_set = set(id(a) for a in ferro_articles)  # 使用id来比较，因为可能是不同的对象引用
        ai_set = set(id(a) for a in ai_articles)
        
        for article in sorted_articles:
            article_id = id(article)
            article['is_ferro'] = article_id in ferro_set or any(
                a.get('id') == article.get('id') or a.get('link') == article.get('link')
                for a in ferro_articles
            )
            article['is_ai'] = article_id in ai_set or any(
                a.get('id') == article.get('id') or a.get('link') == article.get('link')
                for a in ai_articles
            )
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': len(all_articles),
            'ferro_count': len(ferro_articles),
            'ai_count': len(ai_articles),
            'both_count': len(both),
            'overview': f"本周({week_start}至{week_end})共收录{len(all_articles)}篇相关文献，其中磁性/铁电相关{len(ferro_articles)}篇，AI/机器学习相关{len(ai_articles)}篇，交叉研究{len(both)}篇。主要发表在{journal_list}。",
            'trends': '（AI分析暂不可用）',
            'ferro_articles': ferro_only,
            'ai_articles': ai_only,
            'both_articles': both,
            'by_journal': by_journal,
            'all_articles': sorted_articles,
            'generated_by': 'fallback'
        }
    
    def _empty_summary(self, week_start: str, week_end: str) -> Dict:
        """空周报"""
        return {
            'week_start': week_start,
            'week_end': week_end,
            'total': 0,
            'overview': f"本周({week_start}至{week_end})暂无符合条件的文献。",
            'highlights': [],
            'by_topic': {},
            'by_journal': {},
            'trends': '',
            'outlook': '',
            'articles': [],
            'generated_by': 'empty'
        }
    
    def _generate_all_articles_section(self, summary: Dict) -> str:
        """生成所有文献列表的HTML"""
        # 获取所有文章，优先使用 all_articles，否则使用 articles
        all_articles = summary.get('all_articles', summary.get('articles', []))
        
        if not all_articles:
            return ''
        
        # 按期刊分组
        by_journal = {}
        for article in all_articles:
            journal = article.get('journal', 'Unknown')
            if journal not in by_journal:
                by_journal[journal] = []
            by_journal[journal].append(article)
        
        # 生成HTML
        articles_html = ''
        total_articles = sum(len(arts) for arts in by_journal.values())
        processed = 0
        
        for journal, articles in sorted(by_journal.items(), key=lambda x: -len(x[1])):
            articles_html += f'<h3 class="journal-group-title">{journal} ({len(articles)}篇)</h3>'
            articles_html += '<div class="article-list">'
            
            for idx, article in enumerate(articles, 1):
                processed += 1
                title_zh = article.get('title_zh', '')
                title_en = article.get('title', '')
                title = title_zh or title_en
                link = article.get('link', '#')
                date = article.get('pub_date', article.get('date', ''))
                journal = article.get('journal', journal)  # 使用分组中的期刊，如果没有则使用分组名
                
                # 获取摘要
                abstract_zh = article.get('abstract_zh', '')
                abstract_en = article.get('abstract', '')
                
                # 获取作者
                authors = article.get('authors', [])
                authors_str = ''
                if authors:
                    if isinstance(authors, list):
                        if len(authors) <= 3:
                            authors_str = ', '.join(authors)
                        else:
                            authors_str = ', '.join(authors[:3]) + f' 等{len(authors)}位作者'
                    else:
                        authors_str = str(authors)
                
                # 确定文章类型标签
                tags = []
                if article.get('is_ferro'):
                    tags.append('<span class="article-type-tag ferro-tag">⚡ 磁性/铁电</span>')
                if article.get('is_ai'):
                    tags.append('<span class="article-type-tag ai-tag">🤖 AI/机器学习</span>')
                
                tags_html = ''.join(tags) if tags else ''
                
                # 生成AI简要分析（使用缓存避免重复调用）
                # 可以通过环境变量 SKIP_AI_ANALYSIS=1 来跳过AI分析以加快生成速度
                ai_analysis = article.get('ai_analysis', '')
                skip_ai = os.environ.get('SKIP_AI_ANALYSIS', '').lower() == '1'
                
                if not ai_analysis and self.provider and not skip_ai:
                    print(f"  [{processed}/{total_articles}] 分析文章: {title[:50]}...")
                    try:
                        ai_analysis = self._analyze_single_article(article)
                        if ai_analysis:
                            article['ai_analysis'] = ai_analysis
                            # 保存到文章数据中（如果可能）
                            article_id = article.get('id')
                            if article_id:
                                # 这里可以保存到数据库或文件，暂时只保存在内存中
                                pass
                    except Exception as e:
                        print(f"    ⚠️ 分析失败: {e}")
                        ai_analysis = ""
                elif skip_ai:
                    # 跳过AI分析时，使用摘要的前100字作为简要介绍
                    if abstract_zh or abstract_en:
                        preview = (abstract_zh or abstract_en)[:100]
                        ai_analysis = preview + "..." if len(preview) == 100 else preview
                
                # 构建HTML - 添加展开/折叠功能
                article_id = f"article-{article.get('id', processed)}"
                has_abstract_zh = bool(abstract_zh and abstract_en)  # 有中英文摘要才显示展开按钮
                
                # 先构建按钮HTML，避免在f-string表达式内使用反斜杠
                toggle_btn = f'<button class="toggle-abstract-btn" onclick="toggleAbstract(\'{article_id}\')">📖 查看完整摘要</button>' if has_abstract_zh else ''
                
                article_html = f'''
                <div class="article-card" id="{article_id}">
                    <div class="article-header">
                        <div class="article-number">{idx}</div>
                        <div class="article-title-wrapper">
                            <h4 class="article-title">
                                <a href="{link}" target="_blank">{title}</a>
                            </h4>
                            {f'<p class="article-title-en">{title_en}</p>' if title_en and title_zh else ''}
                            {f'<div class="article-journal">📚 {journal}</div>' if journal else ''}
                        </div>
                    </div>
                    <div class="article-body">
                        {f'<div class="article-authors">👤 {authors_str}</div>' if authors_str else ''}
                        {f'<div class="article-ai-analysis">{ai_analysis}</div>' if ai_analysis else ''}
                        {f'<div class="article-abstract-preview">{abstract_zh[:150] if abstract_zh else (abstract_en[:150] if abstract_en else "")}...</div>' if (abstract_zh or abstract_en) else ''}
                        {toggle_btn}
                        <div class="article-abstract-full" id="{article_id}-abstract" style="display: none;">
                            {f'<div class="abstract-section"><strong>中文摘要：</strong><p>{abstract_zh}</p></div>' if abstract_zh else ''}
                            {f'<div class="abstract-section"><strong>English Abstract：</strong><p class="abstract-en">{abstract_en}</p></div>' if abstract_en else ''}
                        </div>
                    </div>
                    <div class="article-footer">
                        <div class="article-tags">
                            {tags_html}
                        </div>
                        {f'<div class="article-date">📅 {date}</div>' if date else ''}
                        <a href="{link}" target="_blank" class="article-link">阅读原文 →</a>
                    </div>
                </div>
                '''
                articles_html += article_html
            
            articles_html += '</div>'
        
        return f'''
        <div class="section all-articles-section">
            <h2>📋 本周所有文献</h2>
            <p class="section-description">本周共收录 {len(all_articles)} 篇文献，按期刊分类如下：</p>
            {articles_html}
        </div>
        '''
    
    def _generate_overview_article_list(self, summary: Dict) -> str:
        """生成总览部分的文章列表（每篇文章一句话总结，带链接）"""
        article_summaries = summary.get('article_summaries', [])
        all_articles = summary.get('all_articles', [])
        
        if not article_summaries and not all_articles:
            return ''
        
        # 如果没有AI生成的总结，从all_articles生成
        if not article_summaries:
            article_summaries = []
            for article in all_articles:
                title = article.get('title_zh') or article.get('title', '')
                link = article.get('link', '')
                # 使用AI分析或摘要前50字作为一句话总结
                one_sentence = article.get('ai_analysis', '')
                if not one_sentence:
                    abstract = article.get('abstract_zh') or article.get('abstract', '')
                    one_sentence = abstract[:50] + '...' if abstract else title[:50]
                article_summaries.append({
                    'title': title,
                    'link': link,
                    'one_sentence': one_sentence[:80]  # 限制长度
                })
        
        # 按类型分组
        ferro_articles = summary.get('ferro_articles', [])
        ai_articles = summary.get('ai_articles', [])
        both_articles = summary.get('both_articles', [])
        
        # 建立文章链接到文章对象的映射
        article_map = {}
        for article in all_articles:
            link = article.get('link', '')
            article_id = article.get('id') or link
            article_map[link] = article
        
        # 分类文章总结
        ferro_summaries = []
        ai_summaries = []
        both_summaries = []
        
        for summary_item in article_summaries:
            link = summary_item.get('link', '')
            article = article_map.get(link)
            
            if not article:
                continue
            
            # 生成文章ID用于锚点
            article_id = f"article-{_safe_id(article.get('id', hash(link) % 100000))}"
            
            # 判断类型
            is_ferro = article.get('is_ferro', False)
            is_ai = article.get('is_ai', False)
            
            summary_with_id = {
                **summary_item,
                'article_id': article_id,
                'journal': article.get('journal', '')
            }
            
            if is_ferro and is_ai:
                both_summaries.append(summary_with_id)
            elif is_ferro:
                ferro_summaries.append(summary_with_id)
            elif is_ai:
                ai_summaries.append(summary_with_id)
        
        # 生成HTML
        html = '<div class="overview-article-list">'
        
        if both_summaries:
            html += '<div class="overview-group both-group">'
            html += f'<h3 class="overview-group-title">🔀 交叉研究 ({len(both_summaries)}篇)</h3>'
            html += '<ul class="overview-list">'
            for item in both_summaries:
                journal_escaped = _safe_text(item.get('journal', ''))
                one_sentence_escaped = _safe_text(item.get('one_sentence', ''))
                html += f'''
                <li class="overview-item">
                    <a href="#{item['article_id']}" class="overview-link">
                        <span class="overview-journal">[{journal_escaped}]</span>
                        {one_sentence_escaped}
                    </a>
                </li>'''
            html += '</ul></div>'
        
        if ferro_summaries:
            html += '<div class="overview-group ferro-group">'
            html += f'<h3 class="overview-group-title">⚡ 磁性/铁电材料 ({len(ferro_summaries)}篇)</h3>'
            html += '<ul class="overview-list">'
            for item in ferro_summaries:
                journal_escaped = _safe_text(item.get('journal', ''))
                one_sentence_escaped = _safe_text(item.get('one_sentence', ''))
                html += f'''
                <li class="overview-item">
                    <a href="#{item['article_id']}" class="overview-link">
                        <span class="overview-journal">[{journal_escaped}]</span>
                        {one_sentence_escaped}
                    </a>
                </li>'''
            html += '</ul></div>'
        
        if ai_summaries:
            html += '<div class="overview-group ai-group">'
            html += f'<h3 class="overview-group-title">🤖 AI/机器学习 ({len(ai_summaries)}篇)</h3>'
            html += '<ul class="overview-list">'
            for item in ai_summaries:
                journal_escaped = _safe_text(item.get('journal', ''))
                one_sentence_escaped = _safe_text(item.get('one_sentence', ''))
                html += f'''
                <li class="overview-item">
                    <a href="#{item['article_id']}" class="overview-link">
                        <span class="overview-journal">[{journal_escaped}]</span>
                        {one_sentence_escaped}
                    </a>
                </li>'''
            html += '</ul></div>'
        
        html += '</div>'
        return html
    

    def save_summary_html(self, summary: Dict, output_dir: str = 'docs/weekly') -> str:
        # 保存周报为HTML（资讯周报风格）
        week_start = str(summary['week_start'])
        week_end = str(summary.get('week_end') or '')
        os.makedirs(output_dir, exist_ok=True)

        filepath = os.path.join(output_dir, f"{week_start}.html")

        def shorten_text(value, limit: int = 160) -> str:
            compact = ' '.join(str(value or '').split())
            if len(compact) <= limit:
                return compact
            return compact[: max(0, limit - 1)].rstrip() + '…'

        def article_key(article: Dict, fallback: str) -> str:
            raw = article.get('link') or article.get('id') or article.get('title_zh') or article.get('title') or fallback
            return str(raw)

        def article_anchor(article: Dict, fallback: str) -> str:
            raw = article.get('id') or article.get('link') or article.get('title_zh') or article.get('title') or fallback
            raw_str = str(raw)
            if raw_str.startswith('article-'):
                raw_str = raw_str[8:]
            return f"article-{_safe_id(raw_str)}"

        def authors_label(article: Dict) -> str:
            authors = article.get('authors')
            if isinstance(authors, list):
                cleaned = [str(item).strip() for item in authors if str(item).strip()]
                if len(cleaned) > 4:
                    return ', '.join(cleaned[:4]) + f' 等{len(cleaned)}位作者'
                return ', '.join(cleaned)
            return str(authors or '').strip()

        def article_teaser(article: Dict, limit: int = 180) -> str:
            for key in ('ai_analysis', 'abstract_zh', 'abstract', 'title_zh', 'title'):
                value = str(article.get(key) or '').strip()
                if value:
                    return shorten_text(value, limit)
            return ''

        both_articles = list(summary.get('both_articles') or [])
        ferro_articles = list(summary.get('ferro_articles') or [])
        ai_articles = list(summary.get('ai_articles') or [])
        all_articles = list(summary.get('all_articles') or summary.get('articles') or [])

        if not all_articles:
            deduped = []
            seen_all = set()
            for index, article in enumerate(both_articles + ferro_articles + ai_articles, 1):
                key = article_key(article, f'all-{index}')
                if key in seen_all:
                    continue
                seen_all.add(key)
                deduped.append(article)
            all_articles = deduped

        if not week_end and week_start:
            try:
                week_end = (datetime.strptime(week_start, '%Y-%m-%d') + timedelta(days=6)).strftime('%Y-%m-%d')
            except Exception:
                week_end = ''

        displayed_keys = set()
        for index, article in enumerate(both_articles + ferro_articles + ai_articles, 1):
            displayed_keys.add(article_key(article, f'display-{index}'))

        other_articles = []
        seen_other = set()
        for index, article in enumerate(all_articles, 1):
            key = article_key(article, f'other-{index}')
            if key in displayed_keys or key in seen_other:
                continue
            seen_other.add(key)
            other_articles.append(article)

        raw_by_journal = summary.get('by_journal') or {}
        by_journal = {}
        if isinstance(raw_by_journal, dict) and raw_by_journal:
            has_article_lists = any(isinstance(value, list) for value in raw_by_journal.values())
            if has_article_lists:
                by_journal = raw_by_journal

        if not by_journal:
            for article in all_articles:
                journal = str(article.get('journal') or '其他来源').strip() or '其他来源'
                by_journal.setdefault(journal, []).append(article)

        def journal_item_count(value) -> int:
            if isinstance(value, list):
                return len(value)
            if isinstance(value, tuple):
                return len(value)
            try:
                return int(value)
            except Exception:
                return len(value or [])

        journal_items = sorted(by_journal.items(), key=lambda item: (-journal_item_count(item[1]), str(item[0])))
        journal_count = len(journal_items)
        arxiv_count = sum(
            1
            for article in all_articles
            if 'arxiv' in str(article.get('journal') or '').lower() or 'arxiv' in str(article.get('link') or '').lower()
        )
        top_journal_text = '、'.join(
            f"{str(journal).strip() or '其他来源'} {journal_item_count(items)}篇"
            for journal, items in journal_items[:4]
        )

        hero_quote_raw = (
            str(summary.get('trends') or '').strip()
            or str(summary.get('outlook') or '').strip()
            or str(summary.get('overview') or '').strip()
            or '覆盖 AI × 物理 / 化学 / 材料交叉研究的一周重点，并保留全文速览入口。'
        )
        hero_quote = _safe_text(shorten_text(hero_quote_raw, 180))

        tag_labels = ['本周总览', '交叉研究', '磁性/铁电', 'AI/机器学习', '期刊分布']
        if other_articles:
            tag_labels.append('其他相关文献')
        if arxiv_count:
            tag_labels.append('含 arXiv 预印本')
        tags_html = ''.join(f'<span class="insight-tag">{_safe_text(tag)}</span>' for tag in tag_labels)

        def render_overview_bucket(title: str, icon: str, articles: List[Dict], tone_class: str, limit: int = 4) -> str:
            if not articles:
                return ''
            item_html = []
            for idx, article in enumerate(articles[:limit], 1):
                journal = _safe_text(str(article.get('journal') or '来源').strip() or '来源')
                teaser = _safe_text(article_teaser(article, 82))
                anchor = article_anchor(article, f'{tone_class}-{idx}')
                item_html.append(
                    f'<li class="weekly-digest-item"><a href="#{anchor}"><span class="weekly-digest-journal">[{journal}]</span>{teaser}</a></li>'
                )
            more_html = ''
            if len(articles) > limit:
                more_html = f'<div class="weekly-digest-more">+ {len(articles) - limit} 篇继续下拉查看</div>'
            title_html = _safe_text(title)
            icon_html = _safe_text(icon)
            return f'''
            <div class="weekly-digest-card {tone_class}">
                <div class="weekly-digest-title"><span>{icon_html} {title_html}</span><span>{len(articles)} 篇</span></div>
                <ul class="weekly-digest-list">{''.join(item_html)}</ul>
                {more_html}
            </div>
            '''

        def render_article_cards(articles: List[Dict], tone_class: str) -> str:
            if not articles:
                return '<div class="insight-empty">本栏目本周暂无相关文献。</div>'

            cards = []
            for idx, article in enumerate(articles, 1):
                raw_title_zh = str(article.get('title_zh') or '').strip()
                raw_title_en = str(article.get('title') or '').strip()
                raw_title = raw_title_zh or raw_title_en or '未命名文献'
                raw_journal = str(article.get('journal') or '').strip()
                raw_link = str(article.get('link') or '#').strip()
                raw_date = str(article.get('pub_date') or article.get('date') or '').strip()
                raw_authors = authors_label(article)
                raw_ai_analysis = str(article.get('ai_analysis') or '').strip()
                raw_abstract_zh = str(article.get('abstract_zh') or '').strip()
                raw_abstract_en = str(article.get('abstract') or '').strip()

                title = _safe_text(raw_title)
                title_en = _safe_text(raw_title_en)
                journal = _safe_text(raw_journal)
                link = _safe_url(raw_link)
                date = _safe_text(raw_date)
                authors = _safe_text(raw_authors)
                abstract_zh = _safe_multiline(raw_abstract_zh)
                abstract_en = _safe_multiline(raw_abstract_en)
                anchor = article_anchor(article, f'{tone_class}-{idx}')

                title_en_block = f'<div class="weekly-paper-title-en">{title_en}</div>' if raw_title_en and raw_title_zh else ''

                meta_parts = []
                if raw_journal:
                    meta_parts.append(f'<span class="weekly-chip weekly-chip-journal">📚 {journal}</span>')
                if raw_authors:
                    meta_parts.append(f'<span class="weekly-chip weekly-chip-authors">👤 {authors}</span>')
                if raw_date:
                    meta_parts.append(f'<span class="weekly-chip">📅 {date}</span>')
                if article.get('is_ferro'):
                    meta_parts.append('<span class="weekly-chip weekly-chip-ferro">⚡ 磁性/铁电</span>')
                if article.get('is_ai'):
                    meta_parts.append('<span class="weekly-chip weekly-chip-ai">🤖 AI/机器学习</span>')
                meta_html = ''.join(meta_parts)

                note_raw = raw_ai_analysis or article_teaser(article, 180)
                note_label = 'AI 解读' if raw_ai_analysis else '核心摘录'
                note_html = ''
                if note_raw:
                    note_html = f'<div class="weekly-paper-summary"><strong>{_safe_text(note_label)}：</strong>{_safe_multiline(note_raw)}</div>'

                preview_raw = ''
                if raw_abstract_zh or raw_abstract_en:
                    preview_source = raw_abstract_zh or raw_abstract_en
                    preview_raw = shorten_text(preview_source, 220)
                preview_html = ''
                if preview_raw and preview_raw != note_raw:
                    preview_html = f'<div class="weekly-paper-preview">{_safe_text(preview_raw)}</div>'

                has_full_abstract = bool(raw_abstract_zh or raw_abstract_en)
                toggle_html = ''
                abstract_html = ''
                if has_full_abstract:
                    abstract_blocks = []
                    if raw_abstract_zh:
                        abstract_blocks.append(
                            f'<div class="weekly-abstract-block"><div class="weekly-abstract-label">中文摘要</div><p>{abstract_zh}</p></div>'
                        )
                    if raw_abstract_en:
                        abstract_blocks.append(
                            f'<div class="weekly-abstract-block"><div class="weekly-abstract-label">English Abstract</div><p class="weekly-abstract-en">{abstract_en}</p></div>'
                        )
                    toggle_html = f'<button class="toggle-abstract-btn" onclick="toggleAbstract(\'{anchor}\', this)">📖 查看完整摘要</button>'
                    abstract_html = f'<div class="weekly-paper-abstract" id="{anchor}-abstract" style="display:none;">{"".join(abstract_blocks)}</div>'

                cards.append(f'''
                <article class="weekly-paper-card {tone_class}" id="{anchor}">
                    <div class="weekly-paper-head">
                        <span class="weekly-paper-number">{idx:02d}</span>
                        <div class="weekly-paper-titles">
                            <h3 class="weekly-paper-title-zh"><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
                            {title_en_block}
                        </div>
                    </div>
                    <div class="weekly-paper-meta">{meta_html}</div>
                    {note_html}
                    {preview_html}
                    <div class="weekly-paper-actions">
                        {toggle_html}
                        <a class="insight-btn insight-btn-secondary" href="{link}" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a>
                    </div>
                    {abstract_html}
                </article>
                ''')
            return f'<div class="weekly-paper-list">{"".join(cards)}</div>'

        def render_journal_stats() -> str:
            if not journal_items:
                return '<div class="insight-empty">暂无期刊统计。</div>'
            items_html = []
            for journal, items in journal_items:
                count = journal_item_count(items)
                items_html.append(
                    f'<div class="weekly-journal-item"><div class="weekly-journal-name">{_safe_text(str(journal) or "其他来源")}</div><div class="weekly-journal-count">{count} 篇</div></div>'
                )
            return f'<div class="weekly-journal-list">{"".join(items_html)}</div>'

        overview_cards = [
            f'''
            <div class="weekly-summary-card">
                <div class="weekly-summary-title">整体概览</div>
                <p>{_safe_multiline(summary.get('overview', '本周暂无周报概览。'))}</p>
            </div>
            '''
        ]

        secondary_title = '趋势观察'
        secondary_text = str(summary.get('trends') or '').strip()
        if not secondary_text:
            secondary_title = '来源分布'
            secondary_text = f'本周主要来源包括：{top_journal_text}。' if top_journal_text else '本周来源结构将在新数据写入后自动更新。'
        overview_cards.append(
            f'''
            <div class="weekly-summary-card">
                <div class="weekly-summary-title">{_safe_text(secondary_title)}</div>
                <p>{_safe_multiline(secondary_text)}</p>
            </div>
            '''
        )

        outlook_text = str(summary.get('outlook') or '').strip()
        if outlook_text:
            overview_cards.append(
                f'''
                <div class="weekly-summary-card">
                    <div class="weekly-summary-title">后续展望</div>
                    <p>{_safe_multiline(outlook_text)}</p>
                </div>
                '''
            )
        else:
            overview_cards.append(
                '''
                <div class="weekly-summary-card">
                    <div class="weekly-summary-title">阅读提示</div>
                    <p>先看交叉研究，再按磁性/铁电与 AI 专题分区深读；所有卡片均保留中英标题、期刊、作者与摘要入口。</p>
                </div>
                '''
            )

        digest_cards = [
            render_overview_bucket('交叉研究', '🔀', both_articles, 'cross'),
            render_overview_bucket('磁性/铁电', '⚡', ferro_articles, 'ferro'),
            render_overview_bucket('AI / 机器学习', '🤖', ai_articles, 'ai'),
            render_overview_bucket('其他相关文献', '🧩', other_articles, 'other', limit=3),
        ]
        digest_cards = [card for card in digest_cards if card]
        overview_body = f'<div class="weekly-summary-grid">{"".join(overview_cards)}</div>'
        if digest_cards:
            overview_body += f'<div class="weekly-digest-grid">{"".join(digest_cards)}</div>'

        sections = []
        toc_links = []
        section_counter = {'value': 1}

        def add_section(section_id: str, title: str, subtitle: str, body_html: str, count_text: str = '') -> None:
            number = section_counter['value']
            num_text = f'{number:02d}'
            title_html = _safe_text(title)
            subtitle_html = _safe_text(subtitle)
            count_block = f'<span class="weekly-toc-meta">{_safe_text(count_text)}</span>' if count_text else f'<span class="weekly-toc-meta">{num_text}</span>'
            sections.append(f'''
            <section id="{section_id}" class="insight-panel weekly-report-section">
                <div class="weekly-section-head">
                    <span class="weekly-section-index">{num_text}</span>
                    <div class="weekly-section-copy">
                        <h2 class="insight-panel-title">{title_html}</h2>
                        <p class="insight-panel-subtitle">{subtitle_html}</p>
                    </div>
                </div>
                {body_html}
            </section>
            ''')
            toc_links.append(f'<a class="weekly-toc-link" href="#{section_id}"><span>{title_html}</span>{count_block}</a>')
            section_counter['value'] += 1

        add_section(
            'overview',
            '本周总览',
            '先把握一周的主线，再进入交叉重点与专题全文速览。',
            overview_body,
            f'{len(all_articles)} 篇文献' if all_articles else '总览',
        )

        if both_articles:
            add_section(
                'cross',
                '交叉研究',
                '优先覆盖 AI × 物理 / 化学 / 材料的直接交叉工作。',
                render_article_cards(both_articles, 'cross'),
                f'{len(both_articles)} 篇',
            )
        if ferro_articles:
            add_section(
                'ferro',
                '磁性 / 铁电专题',
                '聚焦自旋、铁电、多铁与相关功能材料研究。',
                render_article_cards(ferro_articles, 'ferro'),
                f'{len(ferro_articles)} 篇',
            )
        if ai_articles:
            add_section(
                'ai',
                'AI / 机器学习专题',
                '覆盖模型、方法与 AI for Science 应用工作。',
                render_article_cards(ai_articles, 'ai'),
                f'{len(ai_articles)} 篇',
            )
        if other_articles:
            add_section(
                'other',
                '其他相关文献',
                '补充未落入前三个专题但仍与本周主题相关的工作。',
                render_article_cards(other_articles, 'other'),
                f'{len(other_articles)} 篇',
            )
        if journal_items:
            add_section(
                'journals',
                '期刊分布',
                '按来源快速判断本周成果主要集中在哪些期刊或预印本平台。',
                render_journal_stats(),
                f'{journal_count} 个来源',
            )

        sidebar_facts = [
            ('交叉研究', len(both_articles)),
            ('磁性/铁电', len(ferro_articles)),
            ('AI/机器学习', len(ai_articles)),
        ]
        if other_articles:
            sidebar_facts.append(('其他相关', len(other_articles)))
        sidebar_stats_html = ''.join(
            f'<div class="weekly-sidebar-fact"><span>{_safe_text(label)}</span><strong>{value}</strong></div>'
            for label, value in sidebar_facts
        )

        generated_by = _safe_text(summary.get('generated_by', 'AI'))
        generated_at = datetime.now().strftime('%Y-%m-%d %H:%M')
        section_count = max(section_counter['value'] - 1, 1)

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI × Science 周报 - {week_start} 至 {week_end}</title>
    <link rel="stylesheet" href="../style.css">
    <style>
        body {{
            background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(248, 250, 252, 0.85) 240px), var(--bg-primary);
        }}

        .weekly-report-main {{
            min-width: 0;
        }}

        .weekly-report-hero {{
            position: relative;
            overflow: hidden;
        }}

        .weekly-report-hero::after {{
            content: '';
            position: absolute;
            inset: auto -80px -110px auto;
            width: 240px;
            height: 240px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.22), transparent 70%);
            pointer-events: none;
        }}

        .weekly-report-quote {{
            margin: 18px 0 0;
            padding: 16px 18px;
            border-left: 4px solid var(--accent-primary);
            border-radius: 16px;
            background: rgba(99, 102, 241, 0.08);
            color: var(--text-secondary);
            line-height: 1.8;
        }}

        .weekly-hero-actions {{
            margin-top: 18px;
        }}

        .weekly-report-section + .weekly-report-section {{
            margin-top: 20px;
        }}

        .weekly-section-head {{
            display: flex;
            gap: 14px;
            align-items: flex-start;
            margin-bottom: 18px;
        }}

        .weekly-section-copy {{
            min-width: 0;
        }}

        .weekly-section-copy .insight-panel-title {{
            margin-bottom: 6px;
        }}

        .weekly-section-index {{
            width: 42px;
            height: 42px;
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            color: white;
            background: var(--gradient-accent);
            box-shadow: var(--shadow-sm);
            flex-shrink: 0;
        }}

        .weekly-summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
        }}

        .weekly-summary-card,
        .weekly-digest-card,
        .weekly-paper-card,
        .weekly-journal-item,
        .weekly-sidebar-fact,
        .weekly-toc-link {{
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 247, 255, 0.96));
            border: 1px solid var(--border-color);
            box-shadow: var(--shadow-sm);
        }}

        [data-theme="dark"] .weekly-summary-card,
        [data-theme="dark"] .weekly-digest-card,
        [data-theme="dark"] .weekly-paper-card,
        [data-theme="dark"] .weekly-journal-item,
        [data-theme="dark"] .weekly-sidebar-fact,
        [data-theme="dark"] .weekly-toc-link {{
            background: linear-gradient(180deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92));
        }}

        .weekly-summary-card {{
            padding: 18px 20px;
            border-radius: 20px;
            line-height: 1.8;
        }}

        .weekly-summary-title {{
            font-size: 0.9rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: var(--accent-primary);
            margin-bottom: 10px;
        }}

        .weekly-digest-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 18px;
        }}

        .weekly-digest-card {{
            padding: 18px;
            border-radius: 20px;
        }}

        .weekly-digest-card.cross {{
            border-top: 3px solid #8b5cf6;
        }}

        .weekly-digest-card.ferro {{
            border-top: 3px solid #f59e0b;
        }}

        .weekly-digest-card.ai {{
            border-top: 3px solid #10b981;
        }}

        .weekly-digest-card.other {{
            border-top: 3px solid #64748b;
        }}

        .weekly-digest-title {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            font-weight: 700;
            margin-bottom: 12px;
        }}

        .weekly-digest-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: grid;
            gap: 10px;
        }}

        .weekly-digest-item a {{
            color: var(--text-primary);
            text-decoration: none;
            line-height: 1.7;
        }}

        .weekly-digest-item a:hover {{
            color: var(--accent-primary);
        }}

        .weekly-digest-journal {{
            color: var(--accent-primary);
            font-weight: 700;
            margin-right: 8px;
        }}

        .weekly-digest-more {{
            margin-top: 12px;
            color: var(--text-muted);
            font-size: 0.92rem;
        }}

        .weekly-paper-list {{
            display: grid;
            gap: 16px;
        }}

        .weekly-paper-card {{
            border-radius: 22px;
            padding: 20px;
            position: relative;
            overflow: hidden;
            transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
        }}

        .weekly-paper-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--gradient-accent);
            opacity: 0;
            transition: opacity var(--transition-fast);
        }}

        .weekly-paper-card.cross::before {{
            background: linear-gradient(180deg, #8b5cf6 0%, #6366f1 100%);
        }}

        .weekly-paper-card.ferro::before {{
            background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
        }}

        .weekly-paper-card.ai::before {{
            background: linear-gradient(180deg, #10b981 0%, #059669 100%);
        }}

        .weekly-paper-card.other::before {{
            background: linear-gradient(180deg, #64748b 0%, #334155 100%);
        }}

        .weekly-paper-card:hover {{
            transform: translateY(-3px);
            box-shadow: var(--shadow-lg);
            border-color: var(--accent-primary);
        }}

        .weekly-paper-card:hover::before {{
            opacity: 1;
        }}

        .weekly-paper-head {{
            display: flex;
            align-items: flex-start;
            gap: 16px;
        }}

        .weekly-paper-number {{
            width: 42px;
            height: 42px;
            border-radius: 14px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            font-weight: 800;
            color: white;
            background: var(--gradient-accent);
            box-shadow: var(--shadow-sm);
        }}

        .weekly-paper-titles {{
            min-width: 0;
        }}

        .weekly-paper-title-zh {{
            margin: 0;
            font-size: 1.14rem;
            line-height: 1.6;
        }}

        .weekly-paper-title-zh a {{
            color: var(--text-primary);
            text-decoration: none;
        }}

        .weekly-paper-title-zh a:hover {{
            color: var(--accent-primary);
        }}

        .weekly-paper-title-en {{
            margin-top: 8px;
            color: var(--text-secondary);
            font-size: 0.96rem;
            line-height: 1.7;
        }}

        .weekly-paper-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 14px;
        }}

        .weekly-chip {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 7px 12px;
            border-radius: 999px;
            font-size: 0.88rem;
            color: var(--text-secondary);
            background: rgba(99, 102, 241, 0.08);
        }}

        .weekly-chip-authors {{
            background: rgba(16, 185, 129, 0.08);
        }}

        .weekly-chip-journal {{
            background: rgba(99, 102, 241, 0.12);
        }}

        .weekly-chip-ferro {{
            color: #92400e;
            background: rgba(245, 158, 11, 0.16);
        }}

        .weekly-chip-ai {{
            color: #065f46;
            background: rgba(16, 185, 129, 0.16);
        }}

        [data-theme="dark"] .weekly-chip-ferro {{
            color: #fcd34d;
            background: rgba(245, 158, 11, 0.18);
        }}

        [data-theme="dark"] .weekly-chip-ai {{
            color: #6ee7b7;
            background: rgba(16, 185, 129, 0.18);
        }}

        .weekly-paper-summary {{
            margin-top: 14px;
            line-height: 1.85;
            color: var(--text-primary);
        }}

        .weekly-paper-summary strong {{
            color: var(--accent-primary);
        }}

        .weekly-paper-preview {{
            margin-top: 12px;
            color: var(--text-secondary);
            line-height: 1.8;
        }}

        .weekly-paper-actions {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 16px;
        }}

        .toggle-abstract-btn {{
            appearance: none;
            border: none;
            border-radius: 14px;
            padding: 10px 16px;
            background: var(--gradient-accent);
            color: white;
            font-weight: 600;
            cursor: pointer;
            box-shadow: var(--shadow-sm);
            transition: transform var(--transition-fast), box-shadow var(--transition-fast);
        }}

        .toggle-abstract-btn:hover {{
            transform: translateY(-2px);
        }}

        .weekly-paper-abstract {{
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid var(--border-color);
            display: grid;
            gap: 14px;
        }}

        .weekly-abstract-block {{
            line-height: 1.8;
        }}

        .weekly-abstract-label {{
            font-size: 0.9rem;
            font-weight: 800;
            color: var(--accent-primary);
            margin-bottom: 6px;
        }}

        .weekly-abstract-en {{
            color: var(--text-secondary);
            font-style: italic;
        }}

        .weekly-journal-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 14px;
        }}

        .weekly-journal-item {{
            padding: 16px 18px;
            border-radius: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 14px;
        }}

        .weekly-journal-name {{
            font-weight: 700;
        }}

        .weekly-journal-count {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 78px;
            padding: 8px 12px;
            border-radius: 999px;
            background: var(--gradient-accent);
            color: white;
            font-weight: 700;
        }}

        .weekly-report-sidebar {{
            position: sticky;
            top: 24px;
        }}

        .weekly-toc-list,
        .weekly-sidebar-stats {{
            display: grid;
            gap: 10px;
        }}

        .weekly-toc-link {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
            padding: 12px 14px;
            border-radius: 16px;
            color: var(--text-primary);
            text-decoration: none;
        }}

        .weekly-toc-link:hover {{
            color: var(--accent-primary);
            border-color: rgba(99, 102, 241, 0.22);
        }}

        .weekly-toc-meta {{
            color: var(--text-muted);
            font-size: 0.88rem;
            white-space: nowrap;
        }}

        .weekly-sidebar-block + .weekly-sidebar-block {{
            margin-top: 18px;
        }}

        .weekly-sidebar-heading {{
            font-size: 0.9rem;
            font-weight: 800;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 10px;
        }}

        .weekly-sidebar-fact {{
            padding: 12px 14px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }}

        .weekly-sidebar-fact strong {{
            font-size: 1.05rem;
        }}

        .weekly-report-footer {{
            margin-top: 22px;
            padding: 18px 0 0;
            border-top: 1px solid var(--border-color);
            color: var(--text-muted);
            font-size: 0.94rem;
            line-height: 1.8;
        }}

        @media (max-width: 980px) {{
            .weekly-report-sidebar {{
                position: static;
            }}
        }}

        @media (max-width: 720px) {{
            .weekly-section-head,
            .weekly-paper-head {{
                flex-direction: column;
            }}

            .weekly-paper-actions {{
                flex-direction: column;
                align-items: stretch;
            }}

            .toggle-abstract-btn,
            .weekly-paper-actions .insight-btn {{
                width: 100%;
                justify-content: center;
            }}

            .weekly-journal-item {{
                align-items: flex-start;
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="insight-shell">
        <div class="insight-topbar">
            <div class="insight-topbar-left">
                <a href="../index.html" class="insight-back-link">← 返回主页</a>
                <span class="insight-mini-chip">AI × Science Weekly</span>
            </div>
            <div class="insight-topbar-right">
                <span class="insight-mini-chip">{_safe_text(week_start)} → {_safe_text(week_end)}</span>
                <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="切换主题">🌙</button>
            </div>
        </div>

        <div class="insight-layout">
            <main class="weekly-report-main">
                <section class="insight-page-hero weekly-report-hero">
                    <div class="insight-kicker">AI 科学周报</div>
                    <h1 class="insight-title">AI × Science 周报 {_safe_text(week_start)} → {_safe_text(week_end)}</h1>
                    <p class="insight-subtitle">参考 CloudFlare-AI-Insight-Daily 的资讯编排，将一周内 AI × 物理 / 化学 / 材料交叉文献整理为总览、交叉重点、专题速览与期刊分布。</p>
                    <blockquote class="weekly-report-quote">{hero_quote}</blockquote>
                    <div class="insight-tags">{tags_html}</div>
                    <div class="insight-stat-grid">
                        <div class="insight-stat">
                            <div class="insight-stat-label">收录文献</div>
                            <div class="insight-stat-value">{len(all_articles)}</div>
                        </div>
                        <div class="insight-stat">
                            <div class="insight-stat-label">期刊 / 来源</div>
                            <div class="insight-stat-value">{journal_count}</div>
                        </div>
                        <div class="insight-stat">
                            <div class="insight-stat-label">arXiv / 预印本</div>
                            <div class="insight-stat-value">{arxiv_count}</div>
                        </div>
                        <div class="insight-stat">
                            <div class="insight-stat-label">专题版块</div>
                            <div class="insight-stat-value">{section_count}</div>
                        </div>
                    </div>
                    <div class="insight-action-row weekly-hero-actions">
                        <a class="insight-btn insight-btn-primary" href="./index.html">周报归档</a>
                        <a class="insight-btn insight-btn-secondary" href="../daily/">查看日报</a>
                    </div>
                </section>

                {''.join(sections)}

                <div class="weekly-report-footer">
                    本页由文献追踪系统自动生成，保留中英标题、期刊、作者与摘要入口，便于按周追踪 AI × 物理 / 化学 / 材料交叉研究。<br>
                    生成方式：{generated_by} ｜ 更新时间：{generated_at}
                </div>
            </main>

            <aside class="insight-sidebar-card weekly-report-sidebar">
                <h3 class="insight-sidebar-title">快速导航</h3>
                <div class="weekly-toc-list">{''.join(toc_links)}</div>

                <div class="weekly-sidebar-block">
                    <div class="weekly-sidebar-heading">本页分区</div>
                    <div class="weekly-sidebar-stats">{sidebar_stats_html}</div>
                </div>

                <div class="weekly-sidebar-block">
                    <div class="weekly-sidebar-heading">阅读建议</div>
                    <ul class="insight-note-list">
                        <li class="insight-note-item">先读本周总览，再看交叉研究，最后按磁性/铁电与 AI 分区深挖。</li>
                        <li class="insight-note-item">期刊分布适合快速判断本周成果主要来自顶刊还是预印本平台。</li>
                        <li class="insight-note-item">若需要长期追踪某条研究线，可回到归档页连续浏览多周内容。</li>
                    </ul>
                </div>
            </aside>
        </div>
    </div>

    <script>
        const THEME_KEY = 'literature_theme';

        function initTheme() {{
            const theme = localStorage.getItem(THEME_KEY) || 'light';
            document.documentElement.setAttribute('data-theme', theme);
            updateThemeButton();
        }}

        function toggleTheme() {{
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'light' ? 'dark' : 'light';
            localStorage.setItem(THEME_KEY, next);
            document.documentElement.setAttribute('data-theme', next);
            updateThemeButton();
        }}

        function updateThemeButton() {{
            const btn = document.getElementById('themeToggle');
            const theme = document.documentElement.getAttribute('data-theme') || 'light';
            if (btn) btn.textContent = theme === 'light' ? '🌙' : '☀️';
        }}

        function toggleAbstract(articleId, button) {{
            const abstractDiv = document.getElementById(articleId + '-abstract');
            if (!abstractDiv) return;
            const trigger = button || window.event?.target;
            const isHidden = abstractDiv.style.display === 'none' || !abstractDiv.style.display;
            abstractDiv.style.display = isHidden ? 'grid' : 'none';
            if (trigger) {{
                trigger.textContent = isHidden ? '📖 收起摘要' : '📖 查看完整摘要';
            }}
        }}

        initTheme();
    </script>
</body>
</html>'''

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"✅ 周报已保存: {filepath}")

        self._update_weekly_index(output_dir)

        return filepath

    def _update_weekly_index(self, weekly_dir: str = 'docs/weekly'):
        """更新周报索引（根据 weekly_dir 下已有 HTML 重写 index.json）"""
        n = _write_weekly_index_file(weekly_dir)
        print(f"✅ 周报索引已更新: {n} 个周报")
        enhanced = enhance_weekly_archive(os.path.join(weekly_dir, 'index.json'))
        print(f"🧭 Enhanced weekly navigation/TOC for {enhanced} page(s)")


def _write_weekly_index_file(weekly_dir: str = 'docs/weekly') -> int:
    """
    根据 weekly_dir 下已有 YYYY-MM-DD.html 文件重写 index.json。
    返回写入的周报条数。不依赖 WeeklySummarizer 实例，供 sync_weekly_index 使用。
    """
    import glob
    index_file = os.path.join(weekly_dir, 'index.json')
    weekly_files = glob.glob(os.path.join(weekly_dir, '????-??-??.html'))
    weeklies = []
    for f in sorted(weekly_files, reverse=True):
        filename = os.path.basename(f)
        date_str = filename.replace('.html', '')
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            end_date = date_obj + timedelta(days=6)
            weeklies.append({
                'week_start': date_str,
                'week_end': end_date.strftime('%Y-%m-%d'),
                'file': filename
            })
        except ValueError:
            continue
    os.makedirs(weekly_dir, exist_ok=True)
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump({'weeklies': weeklies, 'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
    return len(weeklies)


def generate_weekly_summary(week_start: str = None, api_key: str = None) -> Optional[str]:
    """
    便捷函数：生成周报
    
    Args:
        week_start: 周开始日期 (YYYY-MM-DD)，默认为本周一
        api_key: API密钥
        
    Returns:
        输出文件路径
    """
    # 加载文献数据
    try:
        with open('docs/data/index.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        articles = data.get('articles', [])
    except FileNotFoundError:
        print("❌ 未找到数据文件")
        return None
    
    # 确定周开始日期
    if not week_start:
        today = datetime.now()
        # 计算本周一
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        week_start = monday.strftime('%Y-%m-%d')
    
    # 生成周报
    summarizer = WeeklySummarizer(api_key)
    summary = summarizer.generate_weekly_summary(articles, week_start)
    
    if summary['total'] == 0:
        print(f"📭 {week_start} 这周没有符合条件的文献")
        return None
    
    return summarizer.save_summary_html(summary)


def sync_weekly_index(weekly_dir: str = 'docs/weekly') -> int:
    """
    根据 docs/weekly 下已有 HTML 文件刷新 index.json，确保周报列表页与文件一致。
    不依赖 API 或 WeeklySummarizer 实例，可在 CI 或本地安全调用。
    返回写入的周报条数。
    """
    n = _write_weekly_index_file(weekly_dir)
    try:
        print(f"✅ 周报索引已同步: {n} 个周报")
    except UnicodeEncodeError:
        print(f"[OK] weekly index synced: {n} entries")
    return n


if __name__ == '__main__':
    import sys
    
    # 使用命令行参数
    week_start = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        generate_weekly_summary(week_start)
    finally:
        # 每次运行结束都刷新索引，确保周报列表页能显示所有已存在的 HTML（含本次新生成的）
        sync_weekly_index()
