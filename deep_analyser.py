import os
import json
from typing import Dict, Any, Optional

try:
    from config import AI_CONFIG as DEFAULT_AI_CONFIG
except ImportError:
    DEFAULT_AI_CONFIG = {}

from ai_summarizer import build_provider


class DeepAnalyser:
    """
    Deep relevance analyser for newly fetched papers.

    This module must use the same AI configuration path as the rest of the system:
    - env: AI_API_KEY / AI_PROVIDER / AI_MODEL
    - or config.AI_CONFIG
    """

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None, model: Optional[str] = None):
        self.api_key = (
            (api_key or "").strip()
            or (os.environ.get("AI_API_KEY") or "").strip()
            or (DEFAULT_AI_CONFIG.get("api_key") if isinstance(DEFAULT_AI_CONFIG, dict) else "")  # type: ignore[arg-type]
            or (os.environ.get("GEMINI_API_KEY") or "").strip()  # legacy fallback
        )
        self.provider_name = (
            (provider or "").strip()
            or (os.environ.get("AI_PROVIDER") or "").strip()
            or (DEFAULT_AI_CONFIG.get("provider") if isinstance(DEFAULT_AI_CONFIG, dict) else "gemini")  # type: ignore[arg-type]
            or "gemini"
        ).lower()
        self.model = (
            (model or "").strip()
            or (os.environ.get("AI_MODEL") or "").strip()
            or (DEFAULT_AI_CONFIG.get("model") if isinstance(DEFAULT_AI_CONFIG, dict) else "")  # type: ignore[arg-type]
        ) or None

        self.provider = build_provider(self.provider_name, self.api_key, model=self.model)

    def analyze_relevance(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze an article's relevance and generate a detailed explanation.
        Returns:
          {
            'is_relevant': bool,
            'score': int (0-10),
            'explanation': str (zh),
            'detailed_summary': str (zh)
          }
        """
        title = article.get("title", "")
        abstract = article.get("abstract", "")

        prompt = f"""
As a research assistant specializing in AI-driven science (AI4Science) and Condensed Matter Physics, analyze the following paper for relevance to the user's research interests.

User's PRIMARY Research Interests (High Priority):
1. Interdisciplinary AI: Applications of Machine Learning / AI in Physics, Chemistry, and Materials Science (e.g., MLIP, GNN, automated discovery).
2. Ferroic Physics: Research on Ferroelectric, Ferromagnetic, Antiferromagnetic, Multiferroic, and Altermagnetic (交错磁/Altermagnetism) materials, even without AI components. Focus on magnetoelectric coupling, spin textures, and symmetry.

Paper to analyze:
Title: {title}
Abstract: {abstract}

Provide your analysis in JSON format. All fields EXCEPT \"is_relevant\" and \"score\" MUST be in Chinese (简体中文):
{{
  \"is_relevant\": true/false,
  \"score\": 0-10,
  \"explanation\": \"简短理由（1-2句），说明该研究如何符合AI交叉或铁性材料/磁性物理的方向。\",\n  \"detailed_summary\": \"详细中文总结（3-4句），包含核心研究对象、方法（AI或物理方法）、核心发现及科研启发。\"\n}}
"""

        if not self.api_key:
            return {
                "is_relevant": False,
                "score": 0,
                "explanation": "未配置 AI_API_KEY，跳过深度分析",
                "detailed_summary": "",
            }

        try:
            text = self.provider.call_api(prompt)
            data = self._extract_json(text)
            if not isinstance(data, dict):
                raise ValueError("AI returned non-dict JSON")
            # Basic validation + defaults
            return {
                "is_relevant": bool(data.get("is_relevant", False)),
                "score": int(data.get("score", 0) or 0),
                "explanation": str(data.get("explanation", "") or ""),
                "detailed_summary": str(data.get("detailed_summary", "") or ""),
            }
        except Exception as e:
            return {
                "is_relevant": False,
                "score": 0,
                "explanation": f"AI 调用失败: {type(e).__name__}: {e}",
                "detailed_summary": "",
            }

    @staticmethod
    def _extract_json(text: str) -> Any:
        import re

        m = re.search(r"\{[\s\S]*\}", text or "")
        if not m:
            raise ValueError("No JSON object found in response")
        return json.loads(m.group())


if __name__ == "__main__":
    analyser = DeepAnalyser()
    test_article = {
        "title": "Deep Learning of Ferroelectric Domain Walls",
        "abstract": "We apply graph neural networks to study the dynamics of domain walls in ferroelectric perovskites...",
    }
    print(analyser.analyze_relevance(test_article))

