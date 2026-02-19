#!/usr/bin/env python3
"""
AI摘要生成器 - 使用免费AI API生成每日文献摘要
支持: Gemini, SiliconFlow, Groq, DeepSeek
修复: 解决 AI 在长列表中容易将链接与文章标题搞混的问题
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
        self.model = model or os.environ.get('GEMINI_MODEL', 'gemini-3-flash-preview')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.max_retries = 3
    
    def call_api(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2, # 降低随机性，减少幻觉
                "maxOutputTokens": 8192,
                "topP": 0.95,
                "topK": 40,
                "responseMimeType": "application/json"
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, headers=headers, json=data, timeout=120)
                if response.status_code == 429:
                    import time
                    time.sleep((attempt + 1) * 10)
                    continue
                
                if response.status_code != 200:
                    raise Exception(f"Gemini API错误 ({response.status_code}): {response.text}")
                
                result = response.json()
                if 'candidates' not in result or not result['candidates']:
                    raise Exception("Gemini API返回空响应")
                
                return result['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                if attempt == self.max_retries - 1: raise e
                import time
                time.sleep(5)
        return ""


class AISummarizer:
    """AI摘要生成器"""
    
    def __init__(self, api_provider: str, api_key: str):
        if api_provider == 'gemini':
            self.provider = GeminiProvider(api_key)
        else:
            # Placeholder for other providers if needed
            self.provider = GeminiProvider(api_key) 
        self.provider_name = api_provider
    
    def generate_daily_summary(self, articles: List[Dict], date: str) -> Dict:
        if not articles:
            return self.fallback_summary(articles, date)
        
        # 限制处理数量，防止 context overflow 或 AI 乱序
        articles_to_process = articles[:80]
        
        try:
            prompt = self._build_prompt(articles_to_process, date)
            response = self.provider.call_api(prompt)
            
            # 解析AI响应
            summary = self._parse_response(response, articles_to_process, date)
            return summary
            
        except Exception as e:
            print(f"❌ AI API调用失败: {e}")
            return self.fallback_summary(articles, date)
    
    def _build_prompt(self, articles: List[Dict], date: str) -> str:
        """构建提示词，增加序列号锚点防止链接错位"""
        
        articles_text = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Unknown Title')
            abstract = (article.get('abstract', ''))[:300]
            # 不在提示词里给链接，防止 AI 试图复述链接导致出错
            # 仅给序号、标题、摘要
            articles_text.append(f"[{i}] Title: {title}\nAbstract: {abstract}\n")
        
        articles_str = '\n'.join(articles_text)
        
        return f"""你是一位专业的计算材料科学文献分析助手。请分析以下{date}的{len(articles)}篇文献，生成报告。

文献列表 (格式为 [序号] 标题 - 摘要):
{articles_str}

请输出以下 JSON 格式（必须严格遵循序号对应，确保每一篇都被总结）：
{{
    "overview": "今日文献总览（中文，2-3句）",
    "trends": "研究热点分析（中文，3-5句）",
    "summaries": [
        {{
            "index": 1,
            "title_zh": "中文标题",
            "one_sentence_summary": "一句话中文总结"
        }},
        ... (直到序号 {len(articles)})
    ],
    "highlights": [
        {{
            "index": 序号,
            "reason": "推荐理由（中文，20字以内）"
        }}
    ]
}}

要求：
1. summaries 必须包含输入的所有文献，且 index 必须与输入的 [序号] 严格一致。
2. title_zh 和 one_sentence_summary 必须使用中文。
3. 不要输出任何链接，链接将由 Python 程序根据序号自动补全。
"""

    def _parse_response(self, response: str, original_articles: List[Dict], date: str) -> Dict:
        """解析响应并与原始文章精准合并链接"""
        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if not json_match: raise ValueError("Invalid JSON response")
            data = json.loads(json_match.group())
            
            # 建立序号到原始文章的映射 (1-based index)
            # original_articles 是按顺序传入的
            
            full_list = []
            summaries_map = {item['index']: item for item in data.get('summaries', [])}
            
            for i, article in enumerate(original_articles, 1):
                ai_info = summaries_map.get(i, {})
                full_list.append({
                    "title_en": article.get('title'),
                    "title_zh": ai_info.get('title_zh') or article.get('title_zh') or "标题翻译失败",
                    "summary": ai_info.get('one_sentence_summary') or "总结生成失败",
                    "link": article.get('link') # 核心：直接使用 Python 里的原始链接
                })
            
            # 处理 highlights
            ml_highlights = []
            ferro_highlights = []
            for h in data.get('highlights', []):
                idx = h.get('index')
                if idx and 1 <= idx <= len(original_articles):
                    art = original_articles[idx-1]
                    info = summaries_map.get(idx, {})
                    h_item = {
                        "title_en": art.get('title'),
                        "title_zh": info.get('title_zh'),
                        "link": art.get('link'),
                        "summary": info.get('one_sentence_summary'),
                        "reason": h.get('reason')
                    }
                    # 简单分类（也可以让 AI 返回分类）
                    if self._is_ml_related(art): ml_highlights.append(h_item)
                    elif self._is_ferro_related(art): ferro_highlights.append(h_item)
            
            return {
                'date': date,
                'total': len(original_articles),
                'overview': data.get('overview', ''),
                'trends': data.get('trends', ''),
                'full_list': full_list,
                'ml_highlights': ml_highlights,
                'ferro_highlights': ferro_highlights,
                'generated_by': self.provider_name
            }
        except Exception as e:
            print(f"解析响应并映射链接失败: {e}")
            return self.fallback_summary(original_articles, date)

    def _is_ml_related(self, article: Dict) -> bool:
        text = (article.get('title', '') + article.get('abstract', '')).lower()
        return any(kw in text for kw in ['machine learn', 'deep learn', 'neural network', 'gnn', 'mlip', 'ml potential'])

    def _is_ferro_related(self, article: Dict) -> bool:
        text = (article.get('title', '') + article.get('abstract', '')).lower()
        return any(kw in text for kw in ['ferroelectric', 'ferromagnet', 'multiferroic', 'piezoelectric', 'antiferromagnet'])

    def fallback_summary(self, articles: List[Dict], date: str) -> Dict:
        return {
            'date': date,
            'total': len(articles),
            'overview': f"今日共收录{len(articles)}篇文献（由于AI总结繁忙，仅提供列表）。",
            'full_list': [
                {
                    "title_en": a.get('title'),
                    "title_zh": a.get('title_zh') or "待翻译",
                    "summary": "请查阅原文了解详情",
                    "link": a.get('link')
                } for a in articles
            ],
            'generated_by': 'fallback'
        }
