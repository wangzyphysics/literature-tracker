#!/usr/bin/env python3
"""
AI摘要生成器 - 使用免费AI API生成每日文献摘要
支持: Gemini, OpenRouter (OpenAI-compatible)
修复: 解决 AI 在长列表中容易将链接与文章标题搞混的问题
"""

import os
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any
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

class OpenRouterProvider(AIProvider):
    """
    OpenRouter (OpenAI-compatible) chat completions API.

    Docs: https://openrouter.ai/docs
    """

    def __init__(self, api_key: str, model: str = None):
        self.api_key = (api_key or "").strip()
        self.model = (
            model
            or os.environ.get("AI_MODEL")
            or os.environ.get("OPENROUTER_MODEL")
            or (DEFAULT_AI_CONFIG.get("model") if isinstance(DEFAULT_AI_CONFIG, dict) else None)
            or "stepfun/step-3.5-flash:free"
        )
        self.base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.max_retries = int(os.environ.get("AI_MAX_RETRIES", "3"))
        self.timeout = int(os.environ.get("AI_TIMEOUT_SECONDS", "120"))

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        # Optional attribution headers; keep configurable.
        def _sanitize(v: Optional[str]) -> str:
            v = (v or "").strip()
            if "\r" in v or "\n" in v:
                return ""
            return v

        http_referer = _sanitize(os.environ.get("OPENROUTER_HTTP_REFERER") or os.environ.get("HTTP_REFERER"))
        x_title = _sanitize(os.environ.get("OPENROUTER_X_TITLE") or os.environ.get("X_TITLE"))
        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if x_title:
            headers["X-Title"] = x_title
        return headers

    def call_api(self, prompt: str) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter api_key is empty (set AI_API_KEY).")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": int(os.environ.get("AI_MAX_TOKENS", "4096")),
        }

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.base_url, headers=self._headers(), json=payload, timeout=self.timeout
                )
                if response.status_code in (429, 502, 503, 504):
                    import time
                    time.sleep((attempt + 1) * 10)
                    continue

                if response.status_code != 200:
                    raise Exception(f"OpenRouter API错误 ({response.status_code}): {response.text}")

                data = response.json()
                choices = data.get("choices") or []
                if not choices:
                    raise Exception("OpenRouter API返回空 choices")
                msg = (choices[0] or {}).get("message") or {}
                content = msg.get("content")
                if not content:
                    raise Exception("OpenRouter API返回空 content")
                return content
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                import time
                time.sleep(5)
        return ""


def build_provider(api_provider: str, api_key: str, model: str = None) -> AIProvider:
    """Factory for AI providers."""
    name = (api_provider or "").strip().lower()
    if name in ("openrouter", "open-router", "or"):
        return OpenRouterProvider(api_key=api_key, model=model)
    # default: gemini
    gemini_model = model if model and "/" not in model else None
    return GeminiProvider(api_key=api_key, model=gemini_model)


class AISummarizer:
    """AI摘要生成器"""
    
    def __init__(self, api_provider: str, api_key: str, model: str = None):
        model = (
            model
            or os.environ.get("AI_MODEL")
            or (DEFAULT_AI_CONFIG.get("model") if isinstance(DEFAULT_AI_CONFIG, dict) else None)
        )
        self.provider = build_provider(api_provider, api_key, model=model)
        self.provider_name = (api_provider or "gemini").strip().lower()
    
    def generate_daily_summary(self, articles: List[Dict], date: str) -> Dict:
        if not articles:
            return self.fallback_summary(articles, date)
        
        try:
            max_per_call = int(os.environ.get("AI_DAILY_MAX_PER_CALL", "40"))
            if len(articles) <= max_per_call:
                prompt = self._build_prompt(articles, date)
                response = self.provider.call_api(prompt)
                summary = self._parse_response(response, articles, date)
                # compat alias (some callers expect `summaries`)
                if "summaries" not in summary:
                    summary["summaries"] = summary.get("full_list", [])
                return summary

            # Chunking to avoid context overflow and missing items.
            chunks = [articles[i:i + max_per_call] for i in range(0, len(articles), max_per_call)]
            merged_full_list: List[Dict] = []
            merged_ml: List[Dict] = []
            merged_ferro: List[Dict] = []

            for chunk in chunks:
                prompt = self._build_prompt(chunk, date)
                response = self.provider.call_api(prompt)
                part = self._parse_response(response, chunk, date)
                merged_full_list.extend(part.get("full_list", []))
                merged_ml.extend(part.get("ml_highlights", []))
                merged_ferro.extend(part.get("ferro_highlights", []))

            # Overview/trends: second-pass with titles only (cheap prompt).
            overview, trends = self._build_overview_trends(articles, date)

            summary = {
                "date": date,
                "total": len(articles),
                "overview": overview,
                "trends": trends,
                "full_list": merged_full_list,
                "ml_highlights": merged_ml[:20],
                "ferro_highlights": merged_ferro[:20],
                "generated_by": self.provider_name,
            }
            summary["summaries"] = summary.get("full_list", [])
            return summary
            
        except Exception as e:
            print(f"❌ AI API调用失败: {e}")
            return self.fallback_summary(articles, date)

    def _build_overview_trends(self, articles: List[Dict], date: str) -> (str, str):
        titles = []
        for i, a in enumerate(articles[:200], 1):  # cap to keep prompt bounded
            t = a.get("title") or "Unknown Title"
            titles.append(f"[{i}] {t}")
        titles_str = "\n".join(titles)

        prompt = f"""你是一位专业的计算材料科学文献分析助手。\n请基于以下 {date} 的文献标题列表，输出今日文献总览与研究热点分析。\n\n标题列表:\n{titles_str}\n\n请严格输出 JSON：\n{{\n  \"overview\": \"今日文献总览（中文，2-3句）\",\n  \"trends\": \"研究热点分析（中文，3-5句）\"\n}}\n不要输出除 JSON 以外的任何内容。"""
        try:
            response = self.provider.call_api(prompt)
            import re
            m = re.search(r'\{[\s\S]*\}', response)
            if not m:
                return "", ""
            data = json.loads(m.group())
            return data.get("overview", ""), data.get("trends", "")
        except Exception:
            return "", ""
    
    def _build_prompt(self, articles: List[Dict], date: str) -> str:
        """构建提示词，增加序列号锚点防止链接错位"""
        
        articles_text = []
        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Unknown Title')
            journal = article.get("journal", "")
            authors = article.get("authors", [])
            if isinstance(authors, list):
                authors = ", ".join([str(a) for a in authors[:6]]) + (" 等" if len(authors) > 6 else "")
            else:
                authors = str(authors or "")

            abstract = (article.get('abstract', ''))[:300]
            # 不在提示词里给链接，防止 AI 试图复述链接导致出错
            # 仅给序号、标题、期刊、作者、摘要
            articles_text.append(
                f"[{i}] Title: {title}\nJournal: {journal}\nAuthors: {authors}\nAbstract: {abstract}\n"
            )
        
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
            summaries_map = {}
            for item in data.get("summaries", []) or []:
                if not isinstance(item, dict):
                    continue
                try:
                    idx = int(item.get("index"))
                except Exception:
                    continue
                summaries_map[idx] = item
            
            for i, article in enumerate(original_articles, 1):
                ai_info = summaries_map.get(i, {})
                full_list.append({
                    "title_en": article.get('title'),
                    "title_zh": ai_info.get('title_zh') or article.get('title_zh') or "标题翻译失败",
                    "summary": ai_info.get('one_sentence_summary') or "总结生成失败",
                    "link": article.get('link'),  # 核心：直接使用 Python 里的原始链接
                    "journal": article.get("journal", ""),
                    "authors": article.get("authors", []),
                    "pub_date": article.get("pub_date", ""),
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
        data = {
            'date': date,
            'total': len(articles),
            'overview': f"今日共收录{len(articles)}篇文献（由于AI总结繁忙，仅提供列表）。",
            'full_list': [
                {
                    "title_en": a.get('title'),
                    "title_zh": a.get('title_zh') or "待翻译",
                    "summary": "请查阅原文了解详情",
                    "link": a.get('link'),
                    "journal": a.get("journal", ""),
                    "authors": a.get("authors", []),
                    "pub_date": a.get("pub_date", ""),
                } for a in articles
            ],
            'generated_by': 'fallback'
        }
        data["summaries"] = data.get("full_list", [])
        return data


def generate_daily_summary(
    articles: List[Dict],
    *,
    date: str,
    api_provider: str,
    api_key: str,
    model: str = None,
) -> Dict:
    """
    Backward-compatible wrapper for legacy callers (e.g. `main.py`).

    Note: this function only returns the JSON summary. Rendering HTML pages is handled by
    `generate_daily_pages.py` in the current GitHub Pages pipeline.
    """
    day_articles = [a for a in articles if (a.get("pub_date") or "").startswith(date)]
    summarizer = AISummarizer(api_provider, api_key, model=model)
    return summarizer.generate_daily_summary(day_articles, date)
