#!/usr/bin/env python3
"""
AI摘要生成器 - 使用免费AI API生成每日文献摘要
支持: Gemini, SiliconFlow, Groq, DeepSeek
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

try:
    from config import AI_CONFIG as DEFAULT_AI_CONFIG
except ImportError:
    DEFAULT_AI_CONFIG = {}


class AIProvider(ABC):
    """AI提供商基类"""
    
    @abstractmethod
    def call_api(self, prompt: str) -> str:
        pass


class GeminiProvider(AIProvider):
    """Google Gemini API"""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        # 支持从环境变量读取模型，默认使用 gemini-3.0-flash
        self.model = model or os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.max_retries = 3
    
    def call_api(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,
                "topP": 0.95,
                "topK": 40,
                "responseMimeType": "application/json"
            },
            # 使用 BLOCK_ONLY_HIGH 更稳定，BLOCK_NONE 在某些区域可能不支持
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=data,
                    timeout=120
                )
                
                if response.status_code == 429:
                    # 速率限制，等待后重试
                    import time
                    wait_time = (attempt + 1) * 10
                    print(f"⏳ API速率限制，等待{wait_time}秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_msg = error_data['error'].get('message', error_msg)
                    except:
                        pass
                    raise Exception(f"Gemini API错误 ({response.status_code}): {error_msg}")
                
                result = response.json()
                
                # 检查是否有候选响应
                if 'candidates' not in result or len(result['candidates']) == 0:
                    # 检查是否有 promptFeedback 说明被阻止的原因
                    if 'promptFeedback' in result:
                        block_reason = result['promptFeedback'].get('blockReason', '未知原因')
                        raise Exception(f"请求被阻止: {block_reason}")
                    raise Exception("Gemini API返回空响应")
                
                candidate = result['candidates'][0]
                
                # 检查是否被安全过滤
                finish_reason = candidate.get('finishReason', '')
                if finish_reason == 'SAFETY':
                    safety_ratings = candidate.get('safetyRatings', [])
                    raise Exception(f"响应被安全过滤器阻止: {safety_ratings}")
                
                # 提取文本
                if 'content' not in candidate or 'parts' not in candidate['content']:
                    raise Exception(f"响应格式异常，finishReason: {finish_reason}")
                
                return candidate['content']['parts'][0]['text']
                
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                print(f"⚠️ 请求超时，重试 {attempt + 1}/{self.max_retries}")
                continue
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误: {e}"
                print(f"⚠️ 连接错误，重试 {attempt + 1}/{self.max_retries}")
                import time
                time.sleep(5)
                continue
            except Exception as e:
                # 非网络错误，直接抛出
                raise
        
        raise Exception(f"API调用失败，已重试{self.max_retries}次: {last_error}")


class SiliconFlowProvider(AIProvider):
    """SiliconFlow API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
    
    def call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


class GroqProvider(AIProvider):
    """Groq API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


class DeepSeekProvider(AIProvider):
    """DeepSeek API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
    
    def call_api(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 4096
        }
        
        response = requests.post(
            self.base_url,
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


class AISummarizer:
    """AI摘要生成器"""
    
    PROVIDERS = {
        'gemini': GeminiProvider,
        'siliconflow': SiliconFlowProvider,
        'groq': GroqProvider,
        'deepseek': DeepSeekProvider
    }
    
    def __init__(self, api_provider: str, api_key: str):
        """
        初始化AI摘要生成器
        
        Args:
            api_provider: 'gemini' | 'siliconflow' | 'groq' | 'deepseek'
            api_key: API密钥
        """
        if api_provider not in self.PROVIDERS:
            raise ValueError(f"不支持的API提供商: {api_provider}")
        
        self.provider = self.PROVIDERS[api_provider](api_key)
        self.provider_name = api_provider
    
    def generate_daily_summary(self, articles: List[Dict], date: str) -> Dict:
        """
        生成每日摘要
        
        Args:
            articles: 当日文献列表
            date: 日期 (YYYY-MM-DD)
            
        Returns:
            摘要数据字典
        """
        if not articles:
            return self.fallback_summary(articles, date)
        
        try:
            prompt = self._build_prompt(articles, date)
            response = self.provider.call_api(prompt)
            
            # 解析AI响应
            summary = self._parse_response(response, articles, date)
            return summary
            
        except Exception as e:
            print(f"❌ AI API调用失败: {e}")
            return self.fallback_summary(articles, date)
    
    def _build_prompt(self, articles: List[Dict], date: str) -> str:
        """构建提示词"""
        
        # 准备文献信息
        articles_text = []
        for i, article in enumerate(articles[:30], 1):  # 限制数量避免超长
            title = article.get('title_zh') or article.get('title', '')
            journal = article.get('journal', '未知期刊')
            link = article.get('link', '')
            abstract = (article.get('abstract_zh') or article.get('abstract', ''))[:300]
            
            articles_text.append(f"""
{i}. 标题: {title}
   期刊: {journal}
   链接: {link}
   摘要: {abstract}...
""")
        
        articles_str = '\n'.join(articles_text)
        
        return f"""你是一位专业的计算材料科学文献分析助手。请分析以下{date}的{len(articles)}篇新文献，生成一份结构化的每日摘要报告。

**重点关注领域**（请优先分析和推荐）：
1. 机器学习/深度学习在材料科学中的应用（ML势函数、性能预测、材料设计等）
2. 铁性材料研究（铁电ferroelectric、铁磁ferromagnetic、多铁multiferroic、压电piezoelectric等）
3. 上述两个领域的交叉研究（如ML预测铁电性能、神经网络势函数模拟铁性材料等）

文献列表:
{articles_str}

请按以下格式输出（使用JSON格式）:
{{
    "overview": "今日文献总览，包括总数、主要研究方向，特别指出ML和铁性相关文献数量（2-3句话）",
    "trends": "研究热点和趋势分析，重点关注ML和铁性领域的最新进展（3-5句话）",
    "ml_highlights": [
        {{
            "title": "文献标题",
            "journal": "期刊名",
            "link": "原文链接",
            "method": "具体ML方法（如GNN/Transformer/MLIP等）",
            "summary": "核心创新点（不超过50字）",
            "reason": "推荐理由（不超过30字）"
        }}
    ],
    "ferro_highlights": [
        {{
            "title": "文献标题",
            "journal": "期刊名",
            "link": "原文链接",
            "material": "研究材料体系",
            "summary": "核心发现（不超过50字）",
            "reason": "推荐理由（不超过30字）"
        }}
    ],
    "other_highlights": [
        {{
            "title": "文献标题",
            "journal": "期刊名",
            "link": "原文链接",
            "summary": "核心要点（不超过50字）",
            "reason": "推荐理由（不超过30字）"
        }}
    ],
    "by_method": {{
        "机器学习": ["文献链接1", "文献链接2"],
        "第一性原理": ["文献链接1", "文献链接2"],
        "分子动力学": ["文献链接1", "文献链接2"],
        "其他": ["文献链接1", "文献链接2"]
    }}
}}

选择highlights的标准：
1. ml_highlights: 选择3-5篇机器学习相关的重要文献
2. ferro_highlights: 选择3-5篇铁性材料相关的重要文献（如有ML+铁性交叉研究，同时放入两个列表）
3. other_highlights: 选择2-3篇其他值得关注的文献
4. 优先推荐方法创新性强、解决重要问题、来自高影响力期刊的文献

要求:
1. 如果某类文献数量不足，可以减少该类highlights数量
2. summary要突出创新点，不要简单复述摘要
3. 确保所有链接都是原始文献链接
4. 使用中文输出"""
    
    def _parse_response(self, response: str, articles: List[Dict], date: str) -> Dict:
        """解析AI响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError("无法解析JSON")
            
            # 补充完整信息 - 支持新格式（ml_highlights, ferro_highlights, other_highlights）
            return {
                'date': date,
                'total': len(articles),
                'ai_related': sum(1 for a in articles if self._is_ml_related(a)),
                'ferro_related': sum(1 for a in articles if self._is_ferro_related(a)),
                'overview': data.get('overview', ''),
                'trends': data.get('trends', ''),
                # 新格式字段
                'ml_highlights': data.get('ml_highlights', []),
                'ferro_highlights': data.get('ferro_highlights', []),
                'other_highlights': data.get('other_highlights', []),
                'by_method': data.get('by_method', {}),
                # 兼容旧格式
                'highlights': data.get('highlights', []),
                'by_topic': data.get('by_topic', {}),
                'articles': articles,
                'generated_by': self.provider_name
            }
            
        except Exception as e:
            print(f"解析响应失败: {e}")
            return self.fallback_summary(articles, date)
    
    def _is_ml_related(self, article: Dict) -> bool:
        """判断是否机器学习相关"""
        text = ' '.join([
            article.get('title', ''),
            article.get('title_zh', ''),
            article.get('abstract', ''),
            article.get('abstract_zh', '')
        ]).lower()
        
        ml_keywords = [
            'machine learn', 'deep learn', 'neural network', 'graph neural',
            'transformer', 'gnn', 'mlip', 'ml potential', 'machine-learn',
            'artificial intelligence', 'ai-driven', 'data-driven',
            '机器学习', '深度学习', '神经网络', '人工智能'
        ]
        return any(kw in text for kw in ml_keywords)
    
    def _is_ferro_related(self, article: Dict) -> bool:
        """判断是否铁性材料相关"""
        text = ' '.join([
            article.get('title', ''),
            article.get('title_zh', ''),
            article.get('abstract', ''),
            article.get('abstract_zh', '')
        ]).lower()
        
        ferro_keywords = [
            'ferroelectric', 'ferromagnet', 'multiferroic', 'piezoelectric',
            'antiferroelectric', 'antiferromagnet', 'magnetoelectric',
            'polarization switch', 'domain wall', 'perovskite',
            '铁电', '铁磁', '多铁', '压电', '反铁电', '反铁磁', '磁电'
        ]
        return any(kw in text for kw in ferro_keywords)
    
    def _is_ai_related(self, article: Dict) -> bool:
        """判断是否AI相关（兼容旧方法）"""
        return self._is_ml_related(article)
    
    def fallback_summary(self, articles: List[Dict], date: str) -> Dict:
        """API失败时的降级摘要"""
        ml_articles = [a for a in articles if self._is_ml_related(a)]
        ferro_articles = [a for a in articles if self._is_ferro_related(a)]
        other_articles = [a for a in articles if not self._is_ml_related(a) and not self._is_ferro_related(a)]
        
        # 按期刊分组
        by_journal = {}
        for article in articles:
            journal = article.get('journal', '其他')
            if journal not in by_journal:
                by_journal[journal] = []
            by_journal[journal].append({
                'title': article.get('title_zh') or article.get('title', ''),
                'link': article.get('link', '')
            })
        
        # 生成ML亮点
        ml_highlights = [
            {
                'title': a.get('title_zh') or a.get('title', ''),
                'journal': a.get('journal', ''),
                'link': a.get('link', ''),
                'method': 'ML方法',
                'summary': (a.get('abstract_zh') or a.get('abstract', ''))[:80] + '...',
                'reason': '机器学习相关研究'
            }
            for a in ml_articles[:5]
        ]
        
        # 生成铁性材料亮点
        ferro_highlights = [
            {
                'title': a.get('title_zh') or a.get('title', ''),
                'journal': a.get('journal', ''),
                'link': a.get('link', ''),
                'material': '铁性材料',
                'summary': (a.get('abstract_zh') or a.get('abstract', ''))[:80] + '...',
                'reason': '铁性材料相关研究'
            }
            for a in ferro_articles[:5]
        ]
        
        # 生成其他亮点
        other_highlights = [
            {
                'title': a.get('title_zh') or a.get('title', ''),
                'journal': a.get('journal', ''),
                'link': a.get('link', ''),
                'summary': (a.get('abstract_zh') or a.get('abstract', ''))[:80] + '...',
                'reason': '新发表文献'
            }
            for a in other_articles[:3]
        ]
        
        return {
            'date': date,
            'total': len(articles),
            'ai_related': len(ml_articles),
            'ferro_related': len(ferro_articles),
            'overview': f"今日共收录{len(articles)}篇文献，其中机器学习相关{len(ml_articles)}篇，铁性材料相关{len(ferro_articles)}篇。",
            'trends': '（AI分析暂不可用，显示基于关键词的自动分类）',
            'ml_highlights': ml_highlights,
            'ferro_highlights': ferro_highlights,
            'other_highlights': other_highlights,
            # 兼容旧格式
            'highlights': ml_highlights + ferro_highlights + other_highlights,
            'by_journal': by_journal,
            'articles': articles,
            'generated_by': 'fallback'
        }
    
    def save_summary_html(self, summary: Dict, output_dir: str = 'docs/daily') -> str:
        """
        保存摘要为HTML文件
        
        Args:
            summary: 摘要数据
            output_dir: 输出目录
            
        Returns:
            输出文件路径
        """
        date = summary['date']
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, f"{date}.html")
        
        # 生成ML文献HTML
        def generate_highlight_cards(highlights, category_icon="⭐"):
            html = ''
            for h in highlights:
                method_or_material = h.get('method', '') or h.get('material', '')
                extra_info = f'<span class="highlight-tag">{method_or_material}</span>' if method_or_material else ''
                html += f'''
            <div class="highlight-card">
                <h4><a href="{h.get('link', '#')}" target="_blank">{h.get('title', '')}</a></h4>
                <div class="highlight-meta">📚 {h.get('journal', '')} {extra_info}</div>
                <p class="highlight-summary">{h.get('summary', '')}</p>
                <div class="highlight-reason">💡 {h.get('reason', '')}</div>
            </div>
            '''
            return html
        
        # 兼容旧格式和新格式
        ml_highlights = summary.get('ml_highlights', [])
        ferro_highlights = summary.get('ferro_highlights', [])
        other_highlights = summary.get('other_highlights', [])
        old_highlights = summary.get('highlights', [])
        
        # 如果是旧格式，使用旧的highlights
        if not ml_highlights and not ferro_highlights and old_highlights:
            ml_html = generate_highlight_cards(old_highlights)
            ferro_html = ''
            other_html = ''
        else:
            ml_html = generate_highlight_cards(ml_highlights)
            ferro_html = generate_highlight_cards(ferro_highlights)
            other_html = generate_highlight_cards(other_highlights)
        
        # 计算各类文献数量 - 使用summary中的统计数据
        ml_count = summary.get('ai_related', 0)
        ferro_count = summary.get('ferro_related', 0)
        
        # 生成完整HTML
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>每日摘要 - {date}</title>
    <link rel="stylesheet" href="../style.css">
    <style>
        .summary-container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }}
        .summary-header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .summary-stats {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: var(--bg-card);
            padding: 15px 25px;
            border-radius: 10px;
            text-align: center;
        }}
        .stat-box.ml {{
            border-left: 4px solid #10b981;
        }}
        .stat-box.ferro {{
            border-left: 4px solid #f59e0b;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: var(--accent-primary);
        }}
        .stat-label {{
            color: var(--text-muted);
            font-size: 0.9em;
        }}
        .section {{
            background: var(--bg-card);
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: var(--shadow-md);
        }}
        .section h3 {{
            margin-bottom: 15px;
            color: var(--text-primary);
        }}
        .section.ml-section {{
            border-left: 4px solid #10b981;
        }}
        .section.ferro-section {{
            border-left: 4px solid #f59e0b;
        }}
        .highlight-card {{
            border-left: 4px solid var(--accent-primary);
            padding: 15px;
            margin-bottom: 15px;
            background: var(--bg-primary);
            border-radius: 0 8px 8px 0;
        }}
        .highlight-card h4 {{
            margin: 0 0 8px 0;
        }}
        .highlight-card h4 a {{
            color: var(--text-primary);
            text-decoration: none;
        }}
        .highlight-card h4 a:hover {{
            color: var(--accent-primary);
        }}
        .highlight-meta {{
            font-size: 0.85em;
            color: var(--text-muted);
            margin-bottom: 8px;
        }}
        .highlight-tag {{
            background: var(--accent-primary);
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 8px;
        }}
        .highlight-summary {{
            color: var(--text-secondary);
            margin: 8px 0;
        }}
        .highlight-reason {{
            font-size: 0.85em;
            color: var(--color-ai-tag);
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            color: var(--accent-primary);
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
        .generated-by {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.85em;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="summary-container">
        <a href="../index.html" class="back-link">← 返回主页</a>
        
        <div class="summary-header">
            <h1>📰 每日文献摘要</h1>
            <h2>{date}</h2>
        </div>
        
        <div class="summary-stats">
            <div class="stat-box">
                <div class="stat-value">{summary.get('total', 0)}</div>
                <div class="stat-label">总文献数</div>
            </div>
            <div class="stat-box ml">
                <div class="stat-value">{ml_count}</div>
                <div class="stat-label">🤖 ML相关</div>
            </div>
            <div class="stat-box ferro">
                <div class="stat-value">{ferro_count}</div>
                <div class="stat-label">⚡ 铁性相关</div>
            </div>
        </div>
        
        <div class="section">
            <h3>📊 今日总览</h3>
            <p>{summary.get('overview', '')}</p>
        </div>
        
        <div class="section">
            <h3>🔥 研究趋势</h3>
            <p>{summary.get('trends', '')}</p>
        </div>
        
        {'<div class="section ml-section"><h3>🤖 机器学习亮点</h3>' + ml_html + '</div>' if ml_html else ''}
        
        {'<div class="section ferro-section"><h3>⚡ 铁性材料亮点</h3>' + ferro_html + '</div>' if ferro_html else ''}
        
        {'<div class="section"><h3>📚 其他推荐</h3>' + other_html + '</div>' if other_html else ''}
        
        <div class="generated-by">
            由 {summary.get('generated_by', 'AI')} 生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
    </div>
    
    <script>
        // 主题支持
        const theme = localStorage.getItem('literature_theme') || 'light';
        document.documentElement.setAttribute('data-theme', theme);
    </script>
</body>
</html>'''
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ 每日摘要已保存: {filepath}")
        
        # 更新摘要索引
        self._update_summary_index(date)
        
        return filepath
    
    def _update_summary_index(self, date: str):
        """更新每日摘要索引文件"""
        import glob
        
        daily_dir = 'docs/daily'
        index_file = os.path.join(daily_dir, 'summaries.json')
        
        # 扫描所有摘要文件
        summary_files = glob.glob(os.path.join(daily_dir, '????-??-??.html'))
        summaries = []
        
        for f in sorted(summary_files, reverse=True):
            filename = os.path.basename(f)
            date_str = filename.replace('.html', '')
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                summaries.append({
                    'date': date_str,
                    'weekday': date_obj.strftime('%A'),
                    'file': filename
                })
            except ValueError:
                continue
        
        # 保存索引
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump({'summaries': summaries, 'updated': datetime.now().isoformat()}, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 摘要索引已更新: {len(summaries)} 个摘要")


def generate_daily_summary(articles: List[Dict], date: str = None, 
                          api_provider: str = None, api_key: str = None) -> Optional[str]:
    """
    便捷函数：生成每日摘要
    
    Args:
        articles: 文献列表
        date: 日期，默认今天
        api_provider: API提供商
        api_key: API密钥
        
    Returns:
        输出文件路径
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # 筛选当日文献
    print(f"\n📅 筛选 {date} 的文献...")
    print(f"   总文献数: {len(articles)}")
    
    # 检查日期字段格式
    date_formats = {}
    for a in articles[:10]:  # 只检查前10篇作为样本
        pub_date = a.get('pub_date', '')
        if pub_date:
            date_len = len(pub_date.split()[0]) if ' ' in pub_date else len(pub_date)
            date_formats[date_len] = date_formats.get(date_len, 0) + 1
    
    if date_formats:
        print(f"   日期字段格式样本: {dict(date_formats)}")
    
    today_articles = [
        a for a in articles 
        if a.get('pub_date', '').startswith(date)
    ]
    
    print(f"   匹配日期 {date} 的文献数: {len(today_articles)}")
    
    if not today_articles:
        print(f"📭 {date} 没有新文献")
        # 显示最近几天的文献数量，帮助调试
        from collections import Counter
        date_counts = Counter()
        for a in articles:
            pub_date = a.get('pub_date', '')
            if pub_date:
                date_part = pub_date.split()[0] if ' ' in pub_date else pub_date[:10]
                if len(date_part) >= 10:
                    date_counts[date_part[:10]] += 1
        if date_counts:
            print(f"   最近几天的文献分布:")
            for d, count in date_counts.most_common(5):
                print(f"     {d}: {count} 篇")
        return None
    
    # 获取API配置
    if not api_provider:
        api_provider = (
            os.environ.get('AI_PROVIDER')
            or DEFAULT_AI_CONFIG.get('provider')
            or 'gemini'
        )
    if not api_key:
        api_key = os.environ.get('AI_API_KEY', '') or DEFAULT_AI_CONFIG.get('api_key', '')
    
    if not api_key:
        print("⚠️ 未配置AI API密钥，使用降级摘要")
        summarizer = AISummarizer.__new__(AISummarizer)
        summarizer.provider_name = 'fallback'
        summary = summarizer.fallback_summary(today_articles, date)
    else:
        summarizer = AISummarizer(api_provider, api_key)
        summary = summarizer.generate_daily_summary(today_articles, date)
    
    return summarizer.save_summary_html(summary)


if __name__ == '__main__':
    import sys
    
    # 测试
    try:
        with open('docs/data/index.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        articles = data.get('articles', [])
        
        # 使用命令行参数或环境变量
        date = sys.argv[1] if len(sys.argv) > 1 else None
        generate_daily_summary(articles, date)
        
    except FileNotFoundError:
        print("未找到数据文件，请先运行抓取脚本")
