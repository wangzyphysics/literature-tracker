"""
翻译模块

优先使用项目的 AI Provider（OpenRouter / Gemini 等）进行翻译与摘要式翻译；
当未配置 AI_API_KEY 时，降级使用 GoogleTranslator（deep-translator）。
"""

from __future__ import annotations

import os
from deep_translator import GoogleTranslator
import time
import re

from ai_summarizer import build_provider

try:
    from config import AI_CONFIG as _DEFAULT_AI_CONFIG
except Exception:
    _DEFAULT_AI_CONFIG = {}

class Translator:
    def __init__(self):
        self.translator = GoogleTranslator(source='en', target='zh-CN')
        self._ai_provider = None
        # 配置优先级与 config.py 一致：环境变量 > config.local.py(经 config.AI_CONFIG)
        _cfg = _DEFAULT_AI_CONFIG if isinstance(_DEFAULT_AI_CONFIG, dict) else {}
        self._ai_provider_name = (
            os.environ.get("AI_PROVIDER") or _cfg.get("provider") or "openrouter"
        ).strip()
        self._ai_key = (
            os.environ.get("AI_API_KEY") or _cfg.get("api_key") or ""
        ).strip()
        self._ai_model = (
            (os.environ.get("AI_MODEL") or _cfg.get("model") or "").strip() or None
        )
    
    def translate(self, text: str) -> str:
        """翻译文本到中文"""
        if not text or not text.strip():
            return ""

        try:
            # 清理HTML标签
            clean_text = re.sub(r'<[^>]+>', '', text)
            clean_text = clean_text.strip()
            
            if not clean_text:
                return ""

            # Prefer AI provider when configured
            if self._ai_key:
                if self._ai_provider is None:
                    self._ai_provider = build_provider(self._ai_provider_name, self._ai_key, model=self._ai_model)

                # Keep translation prompt simple to reduce hallucination.
                prompt = (
                    "你是专业的学术翻译助手。请将下面英文翻译为简体中文，保持术语准确，"
                    "只输出译文，不要解释：\n\n"
                    f"{clean_text}\n"
                )
                resp = self._ai_provider.call_api(prompt)
                return (resp or "").strip() or clean_text
            
            # deep-translator有字符限制，需要分段翻译
            if len(clean_text) > 4500:
                chunks = self._split_text(clean_text, 4500)
                translated_chunks = []
                for chunk in chunks:
                    translated = self.translator.translate(chunk)
                    translated_chunks.append(translated)
                    time.sleep(0.5)  # 避免请求过快
                return ''.join(translated_chunks)
            
            return self.translator.translate(clean_text)
        except Exception as e:
            print(f"翻译失败: {e}")
            return text  # 翻译失败时返回原文
    
    def _split_text(self, text: str, max_length: int) -> list:
        """将长文本分割成小块"""
        chunks = []
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_length:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks


# 单例实例
translator = Translator()


def translate_text(text: str) -> str:
    """翻译文本的便捷函数"""
    return translator.translate(text)
