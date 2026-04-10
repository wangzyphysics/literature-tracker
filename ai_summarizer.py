#!/usr/bin/env python3
"""
AI摘要生成器 - 使用免费AI API生成每日文献摘要
支持: Gemini, OpenRouter (OpenAI-compatible)
修复: 解决 AI 在长列表中容易将链接与文章标题搞混的问题
"""

import os
import json
import time
import re
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from abc import ABC, abstractmethod
from urllib.parse import urlsplit, urlunsplit

try:
    from config import AI_CONFIG as DEFAULT_AI_CONFIG
except ImportError:
    DEFAULT_AI_CONFIG = {}

try:
    from json_repair import repair_json
except ImportError:
    repair_json = None


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
        wait_max_seconds = int(os.environ.get("AI_WAIT_MAX_SECONDS", "0") or "0")
        wait_base_seconds = float(os.environ.get("AI_WAIT_BASE_SECONDS", "10") or "10")
        wait_max_sleep_seconds = float(os.environ.get("AI_WAIT_MAX_SLEEP_SECONDS", "300") or "300")

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

        start = time.monotonic()
        attempt = 0
        last_err: Optional[Exception] = None

        while True:
            attempt += 1
            try:
                response = requests.post(url, headers=headers, json=data, timeout=120)
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' not in result or not result['candidates']:
                        raise Exception("Gemini API返回空响应")
                    return result['candidates'][0]['content']['parts'][0]['text']

                # Retryable
                if response.status_code in (429, 500, 502, 503, 504):
                    last_err = Exception(f"Gemini API错误 ({response.status_code}): {response.text}")
                else:
                    raise Exception(f"Gemini API错误 ({response.status_code}): {response.text}")
            except Exception as e:
                last_err = e

            elapsed = time.monotonic() - start
            if wait_max_seconds > 0:
                if elapsed >= wait_max_seconds:
                    raise last_err or Exception("Gemini API failed")
            else:
                if attempt >= self.max_retries:
                    raise last_err or Exception("Gemini API failed")

            sleep_s = min(wait_base_seconds * (2 ** max(0, attempt - 1)), wait_max_sleep_seconds)
            # Keep a bit of jitterless wait to reduce flakiness in CI.
            time.sleep(min(sleep_s, max(1.0, (wait_max_seconds - elapsed) if wait_max_seconds > 0 else sleep_s)))

class OpenRouterProvider(AIProvider):
    """
    OpenAI-compatible chat completions API.

    Docs: https://openrouter.ai/docs
    """

    def __init__(self, api_key: str, model: str = None):
        self.api_key = (api_key or "").strip()
        self.model = (
            model
            or os.environ.get("AI_MODEL")
            or os.environ.get("OPENROUTER_MODEL")
            or (DEFAULT_AI_CONFIG.get("model") if isinstance(DEFAULT_AI_CONFIG, dict) else None)
            or "gpt-5.4(auto)"
        )
        raw_base_url = (
            os.environ.get("AI_BASE_URL")
            or os.environ.get("OPENROUTER_BASE_URL")
            or (DEFAULT_AI_CONFIG.get("base_url") if isinstance(DEFAULT_AI_CONFIG, dict) else None)
            or "https://supercodex.space/v1"
        )
        self.base_url = normalize_chat_completions_url(raw_base_url)
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

        wait_max_seconds = int(os.environ.get("AI_WAIT_MAX_SECONDS", "0") or "0")
        wait_base_seconds = float(os.environ.get("AI_WAIT_BASE_SECONDS", "10") or "10")
        wait_max_sleep_seconds = float(os.environ.get("AI_WAIT_MAX_SLEEP_SECONDS", "300") or "300")
        json_mode_enabled = (os.environ.get("AI_RESPONSE_JSON", "") or "").strip().lower() in ("1", "true", "yes")

        start = time.monotonic()
        attempt = 0
        last_err: Optional[Exception] = None

        while True:
            attempt += 1
            response = None
            try:
                payload: Dict[str, Any] = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": int(os.environ.get("AI_MAX_TOKENS", "4096")),
                }
                # Optional JSON mode. Some models do not support `response_format`.
                if json_mode_enabled:
                    payload["response_format"] = {"type": "json_object"}

                response = requests.post(
                    self.base_url, headers=self._headers(), json=payload, timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices") or []
                    if not choices:
                        raise Exception("OpenRouter API返回空 choices")
                    msg = (choices[0] or {}).get("message") or {}
                    content = msg.get("content")
                    if not content:
                        raise Exception("OpenRouter API返回空 content")
                    return content

                if (
                    response.status_code == 400
                    and json_mode_enabled
                    and any(
                        token in response.text.lower()
                        for token in ("response_format", "json_object", "structured output", "not support")
                    )
                ):
                    print("⚠️ OpenRouter JSON mode unsupported by current model, retrying without response_format")
                    json_mode_enabled = False
                    attempt -= 1
                    continue

                # Retryable server / rate limit errors
                if response.status_code in (429, 500, 502, 503, 504):
                    last_err = Exception(f"OpenRouter API错误 ({response.status_code}): {response.text}")
                else:
                    raise Exception(f"OpenRouter API错误 ({response.status_code}): {response.text}")
            except Exception as e:
                last_err = e

            elapsed = time.monotonic() - start
            if wait_max_seconds > 0:
                if elapsed >= wait_max_seconds:
                    raise last_err or Exception("OpenRouter API failed")
            else:
                if attempt >= self.max_retries:
                    raise last_err or Exception("OpenRouter API failed")

            retry_after = 0.0
            if response is not None:
                try:
                    ra = (response.headers.get("Retry-After") or "").strip()
                    if ra:
                        retry_after = float(ra)
                except Exception:
                    retry_after = 0.0

            sleep_s = min(wait_base_seconds * (2 ** max(0, attempt - 1)), wait_max_sleep_seconds)
            if retry_after > 0:
                sleep_s = max(sleep_s, retry_after)

            if wait_max_seconds > 0:
                remaining = max(0.0, wait_max_seconds - elapsed)
                sleep_s = min(sleep_s, max(1.0, remaining))
            time.sleep(sleep_s)


def normalize_chat_completions_url(raw_url: Optional[str]) -> str:
    """
    Accept either a root OpenAI-compatible base URL (e.g. https://host/v1)
    or a full chat-completions endpoint, and normalize to the latter.
    """
    default_url = "https://openrouter.ai/api/v1/chat/completions"
    candidate = (raw_url or "").strip()
    if not candidate:
        return default_url

    parsed = urlsplit(candidate)
    if not parsed.scheme or not parsed.netloc:
        return default_url

    normalized_path = parsed.path.rstrip("/")
    if not normalized_path:
        normalized_path = "/chat/completions"
    elif not (
        normalized_path.endswith("/chat/completions")
        or normalized_path.endswith("/completions")
    ):
        normalized_path = f"{normalized_path}/chat/completions"

    return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, parsed.query, parsed.fragment))


def build_provider(api_provider: str, api_key: str, model: str = None) -> AIProvider:
    """Factory for AI providers."""
    name = (api_provider or "").strip().lower()
    if name in ("openrouter", "open-router", "or", "kimi"):
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

        wait_max_seconds = int(os.environ.get("AI_DAILY_WAIT_MAX_SECONDS") or os.environ.get("AI_WAIT_MAX_SECONDS", "0") or "0")
        wait_base_seconds = float(os.environ.get("AI_DAILY_WAIT_BASE_SECONDS") or os.environ.get("AI_WAIT_BASE_SECONDS", "10") or "10")
        wait_max_sleep_seconds = float(os.environ.get("AI_DAILY_WAIT_MAX_SLEEP_SECONDS") or os.environ.get("AI_WAIT_MAX_SLEEP_SECONDS", "300") or "300")
        no_fallback = (os.environ.get("AI_DAILY_NO_FALLBACK") or os.environ.get("AI_NO_FALLBACK") or "").strip().lower() in ("1", "true", "yes")

        start = time.monotonic()
        attempt = 0
        last_err: Optional[Exception] = None

        while True:
            attempt += 1
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
                last_err = e
                print(f"❌ AI 摘要生成失败 (attempt={attempt}): {e}")

                # Fatal errors: waiting won't help (e.g., missing/invalid API key).
                msg_lower = str(e).lower()
                is_fatal = (
                    isinstance(e, ValueError)
                    and ("api_key is empty" in msg_lower or "api key is empty" in msg_lower)
                ) or ("401" in msg_lower) or ("403" in msg_lower)

                if is_fatal:
                    if no_fallback:
                        raise last_err
                    return self.fallback_summary(articles, date)

                elapsed = time.monotonic() - start
                if wait_max_seconds > 0 and elapsed < wait_max_seconds:
                    sleep_s = min(wait_base_seconds * (2 ** max(0, attempt - 1)), wait_max_sleep_seconds)
                    remaining = max(0.0, wait_max_seconds - elapsed)
                    sleep_s = min(sleep_s, max(1.0, remaining))
                    print(f"⏳ 等待 {sleep_s:.0f}s 后重试（已等待 {elapsed:.0f}s / {wait_max_seconds}s）")
                    time.sleep(sleep_s)
                    continue

                if no_fallback:
                    raise last_err

                return self.fallback_summary(articles, date)

    def _build_overview_trends(self, articles: List[Dict], date: str) -> Tuple[str, str]:
        titles = []
        for i, a in enumerate(articles[:200], 1):  # cap to keep prompt bounded
            t = a.get("title") or "Unknown Title"
            titles.append(f"[{i}] {t}")
        titles_str = "\n".join(titles)

        prompt = f"""你是一位专业的计算材料科学文献分析助手。\n请基于以下 {date} 的文献标题列表，输出今日文献总览与研究热点分析。\n\n标题列表:\n{titles_str}\n\n请严格输出 JSON：\n{{\n  \"overview\": \"今日文献总览（中文，2-3句）\",\n  \"trends\": \"研究热点分析（中文，3-5句）\"\n}}\n不要输出除 JSON 以外的任何内容。"""
        wait_max_seconds = int(os.environ.get("AI_DAILY_WAIT_MAX_SECONDS") or os.environ.get("AI_WAIT_MAX_SECONDS", "0") or "0")
        wait_base_seconds = float(os.environ.get("AI_DAILY_WAIT_BASE_SECONDS") or os.environ.get("AI_WAIT_BASE_SECONDS", "10") or "10")
        wait_max_sleep_seconds = float(os.environ.get("AI_DAILY_WAIT_MAX_SLEEP_SECONDS") or os.environ.get("AI_WAIT_MAX_SLEEP_SECONDS", "300") or "300")

        start = time.monotonic()
        attempt = 0

        while True:
            attempt += 1
            try:
                response = self.provider.call_api(prompt)
                data = self._load_json_lenient(response, context="overview/trends")
                if not isinstance(data, dict):
                    raise ValueError("overview/trends: response is not an object")
                return data.get("overview", ""), data.get("trends", "")
            except Exception:
                if wait_max_seconds <= 0:
                    return "", ""
                elapsed = time.monotonic() - start
                if elapsed >= wait_max_seconds:
                    return "", ""
                sleep_s = min(wait_base_seconds * (2 ** max(0, attempt - 1)), wait_max_sleep_seconds)
                remaining = max(0.0, wait_max_seconds - elapsed)
                time.sleep(min(sleep_s, max(1.0, remaining)))
    
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
            "title_zh": "中文标题（翻译原标题）",
            "abstract_zh": "摘要中文翻译（100字以内）",
            "one_sentence_summary": "一句话中文总结（突出研究亮点）"
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
2. title_zh、abstract_zh 和 one_sentence_summary 必须使用中文。
3. 不要输出任何链接，链接将由 Python 程序根据序号自动补全。
"""

    def _build_missing_summaries_prompt(self, original_articles: List[Dict], missing_indices: List[int], date: str) -> str:
        articles_text = []
        for idx in missing_indices:
            # 边界检查：防止索引越界
            if idx < 1 or idx > len(original_articles):
                print(f"⚠️ 跳过无效索引 {idx} (有效范围: 1-{len(original_articles)})")
                continue
            article = original_articles[idx - 1]
            title = article.get('title', 'Unknown Title')
            journal = article.get("journal", "")
            authors = article.get("authors", [])
            if isinstance(authors, list):
                authors = ", ".join([str(a) for a in authors[:6]]) + (" 等" if len(authors) > 6 else "")
            else:
                authors = str(authors or "")
            abstract = (article.get('abstract', ''))[:300]
            articles_text.append(
                f"[{idx}] Title: {title}\nJournal: {journal}\nAuthors: {authors}\nAbstract: {abstract}\n"
            )

        articles_str = "\n".join(articles_text)
        return f"""你是一位专业的计算材料科学文献分析助手。请只补全以下 {date} 缺失的文献条目。

文献列表:
{articles_str}

请严格输出 JSON：
{{
  "summaries": [
    {{
      "index": 1,
      "title_zh": "中文标题（翻译原标题）",
      "abstract_zh": "摘要中文翻译（100字以内）",
      "one_sentence_summary": "一句话中文总结（突出研究亮点）"
    }}
  ]
}}

要求：
1. 只返回上面给出的缺失 index。
2. 每个 index 都必须返回 title_zh、abstract_zh 和 one_sentence_summary，且都使用中文。
3. 不要输出 JSON 以外的任何内容。
"""

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        value = (text or "").strip()
        if not value.startswith("```"):
            return value
        lines = value.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @classmethod
    def _extract_json_object(cls, text: str) -> str:
        value = cls._strip_code_fence(text)
        start = value.find("{")
        if start < 0:
            raise ValueError("No JSON object found in model response")

        depth = 0
        in_string = False
        escape = False

        for idx in range(start, len(value)):
            ch = value[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return value[start:idx + 1]

        return value[start:].strip()

    @classmethod
    def _candidate_json_strings(cls, response: str) -> List[str]:
        raw = response or ""
        stripped = raw.strip()
        candidates = [raw, stripped, cls._strip_code_fence(stripped)]
        try:
            candidates.append(cls._extract_json_object(stripped))
        except Exception:
            pass

        normalized_candidates: List[str] = []
        seen = set()
        for candidate in candidates:
            candidate = (candidate or "").strip()
            if not candidate or candidate in seen:
                continue
            normalized_candidates.append(candidate)
            seen.add(candidate)
        return normalized_candidates

    @staticmethod
    def _normalize_json_string(raw: str) -> str:
        return (
            (raw or "")
            .replace("\ufeff", "")
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
        )

    @classmethod
    def _load_json_lenient(cls, response: str, *, context: str = "response") -> Any:
        last_error: Optional[Exception] = None
        for candidate in cls._candidate_json_strings(response):
            for attempt_text in (
                candidate,
                cls._normalize_json_string(candidate),
                re.sub(r",\s*([}\]])", r"\1", cls._normalize_json_string(candidate)),
            ):
                try:
                    return json.loads(attempt_text)
                except Exception as exc:
                    last_error = exc

            if repair_json is not None:
                try:
                    return repair_json(candidate, return_objects=True)
                except Exception as exc:
                    last_error = exc

        raise ValueError(f"{context}: failed to parse model JSON ({last_error})")

    @staticmethod
    def _summary_fields_missing(item: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(item, dict):
            return True
        # 检查关键字段：中文标题、摘要翻译、一句话总结
        has_title_zh = bool(str(item.get("title_zh") or "").strip())
        has_abstract_zh = bool(str(item.get("abstract_zh") or "").strip())
        has_summary = bool(str(item.get("one_sentence_summary") or "").strip())
        return not (has_title_zh and has_abstract_zh and has_summary)

    def _fill_missing_summaries(
        self,
        summaries_map: Dict[int, Dict[str, Any]],
        original_articles: List[Dict],
        date: str,
    ) -> Dict[int, Dict[str, Any]]:
        missing_indices = [
            idx
            for idx in range(1, len(original_articles) + 1)
            if self._summary_fields_missing(summaries_map.get(idx))
        ]
        if not missing_indices:
            return summaries_map

        print(f"⚠️ AI summaries incomplete for {len(missing_indices)} article(s); requesting targeted refill")
        try:
            prompt = self._build_missing_summaries_prompt(original_articles, missing_indices, date)
            response = self.provider.call_api(prompt)
            data = self._load_json_lenient(response, context="missing summaries")
            if not isinstance(data, dict):
                return summaries_map
            for item in data.get("summaries", []) or []:
                if not isinstance(item, dict):
                    continue
                try:
                    idx = int(item.get("index"))
                except Exception:
                    continue
                if idx not in missing_indices:
                    continue
                current = dict(summaries_map.get(idx) or {})
                current.update(item)
                summaries_map[idx] = current
        except Exception as exc:
            print(f"⚠️ Failed to refill missing summaries: {exc}")
        return summaries_map

    def _parse_response(self, response: str, original_articles: List[Dict], date: str) -> Dict:
        """解析响应并与原始文章精准合并链接"""
        try:
            data = self._load_json_lenient(response, context="daily summary")
            if not isinstance(data, dict):
                raise ValueError("Invalid JSON response: root is not an object")
            
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

            summaries_map = self._fill_missing_summaries(summaries_map, original_articles, date)
            
            for i, article in enumerate(original_articles, 1):
                ai_info = summaries_map.get(i, {})
                full_list.append({
                    "title_en": article.get('title'),
                    "title_zh": ai_info.get('title_zh') or article.get('title_zh') or "标题翻译失败",
                    "abstract_zh": ai_info.get('abstract_zh') or "",  # 摘要中文翻译
                    "summary": ai_info.get('one_sentence_summary') or "总结生成失败",
                    "link": article.get('link'),  # 核心：直接使用 Python 里的原始链接
                    "journal": article.get("journal", ""),
                    "authors": article.get("authors", []),
                    "pub_date": article.get("pub_date", ""),
                    "ai_score": article.get("ai_score"),
                    "source_url": article.get("source_url", ""),
                    "arxiv_category": article.get("arxiv_category", ""),
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
                        "abstract_zh": info.get('abstract_zh') or "",  # 摘要中文翻译
                        "link": art.get('link'),
                        "summary": info.get('one_sentence_summary'),
                        "reason": h.get('reason'),
                        "journal": art.get("journal", ""),
                        "authors": art.get("authors", []),
                        "pub_date": art.get("pub_date", ""),
                        "ai_score": art.get("ai_score"),
                        "source_url": art.get("source_url", ""),
                        "arxiv_category": art.get("arxiv_category", ""),
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
            raise

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
            'overview': f"今日共收录{len(articles)}篇文献。",
            'trends': "",
            'full_list': [
                {
                    "title_en": a.get('title'),
                    "title_zh": a.get('title_zh') or "待翻译",
                    "abstract_zh": "",  # 摘要中文翻译
                    "summary": "请查阅原文了解详情",
                    "link": a.get('link'),
                    "journal": a.get("journal", ""),
                    "authors": a.get("authors", []),
                    "pub_date": a.get("pub_date", ""),
                    "ai_score": a.get("ai_score"),
                    "source_url": a.get("source_url", ""),
                    "arxiv_category": a.get("arxiv_category", ""),
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
