"""
Batch relevance analyser for AI×Physics/Chemistry/Materials interdisciplinary focus.

Design goals:
- High recall: prefer including borderline cases rather than missing relevant papers.
- Batch API calls to keep GitHub Actions runtime reasonable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from ai_summarizer import build_provider


def _extract_json(text: str) -> Any:
    import re

    m = re.search(r"\{[\s\S]*\}", text or "")
    if not m:
        raise ValueError("No JSON object found")
    return json.loads(m.group())


def batch_analyze_relevance(
    articles: List[Dict[str, Any]],
    *,
    provider_name: str,
    api_key: str,
    model: Optional[str] = None,
    batch_size: int = 16,
) -> List[Dict[str, Any]]:
    """
    Returns a list of analysis dicts aligned with the input order.

    Each result:
      {
        "is_relevant": bool,
        "score": int (0-10),
        "explanation": str (zh),
        "detailed_summary": str (zh)
      }
    """

    provider_name = (provider_name or "").strip().lower() or "gemini"
    api_key = (api_key or "").strip()
    model = (model or "").strip() or None

    if not api_key:
        return [
            {
                "is_relevant": False,
                "score": 0,
                "explanation": "未配置 AI_API_KEY，跳过相关性分析",
                "detailed_summary": "",
            }
            for _ in articles
        ]

    provider = build_provider(provider_name, api_key, model=model)

    results: List[Dict[str, Any]] = []
    for start in range(0, len(articles), batch_size):
        batch = articles[start : start + batch_size]
        prompt = _build_prompt(batch)
        try:
            text = provider.call_api(prompt)
            data = _extract_json(text)
            mapping = _parse_items(data)
        except Exception:
            mapping = {}

        for i in range(1, len(batch) + 1):
            item = mapping.get(i)
            if not item:
                results.append(
                    {
                        "is_relevant": True,  # recall-first fallback
                        "score": 5,
                        "explanation": "AI 返回不完整，按高召回策略暂时纳入",
                        "detailed_summary": "",
                    }
                )
                continue
            results.append(item)

    return results


def _build_prompt(batch: List[Dict[str, Any]]) -> str:
    lines = []
    for i, a in enumerate(batch, 1):
        title = (a.get("title") or "").strip()
        journal = (a.get("journal") or "").strip()
        authors = a.get("authors") or []
        if isinstance(authors, list):
            authors_str = ", ".join([str(x) for x in authors[:6]]) + (" 等" if len(authors) > 6 else "")
        else:
            authors_str = str(authors or "")
        abstract = (a.get("abstract") or "").strip()
        abstract = abstract[:600]
        lines.append(f"[{i}] Title: {title}\nJournal: {journal}\nAuthors: {authors_str}\nAbstract: {abstract}\n")

    joined = "\n".join(lines)

    return f"""你是一位研究助理，专注于 AI 与物理/化学/材料科学交叉学科（AI4Science）。\n\n请逐条判断以下论文是否与“AI×物理/化学/材料/计算科学”相关。\n\n高召回要求：\n- 宁可多收录，也不要漏掉潜在相关论文。\n- 只要论文可能涉及：机器学习/深度学习/生成模型/图网络/大模型在物理、化学、材料、计算模拟、自动化发现中的应用；或 AI 用于实验/计算数据驱动；或与材料/凝聚态/化学计算强相关且可能与 AI 方法结合，都应判为相关。\n- 只有在明显与上述方向无关（如纯临床医学、生态、社会科学等）时才判为不相关。\n\n输入列表：\n{joined}\n\n请严格输出 JSON（不要 markdown，不要多余解释），并且 items 必须覆盖全部输入序号：\n{{\n  \"items\": [\n    {{\n      \"index\": 1,\n      \"is_relevant\": true,\n      \"score\": 0,\n      \"explanation\": \"中文1-2句，说明为何相关/不相关\",\n      \"detailed_summary\": \"中文3-4句，总结研究对象、方法（AI或物理/化学/材料方法）、主要发现与启发\"\n    }}\n  ]\n}}\n\n注意：除 is_relevant/score 外，其余字段必须是简体中文。"""


def _parse_items(data: Any) -> Dict[int, Dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        items = data["items"]
    else:
        raise ValueError("Unexpected JSON schema")

    mapping: Dict[int, Dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("index"))
        except Exception:
            continue
        mapping[idx] = {
            "is_relevant": bool(item.get("is_relevant", False)),
            "score": int(item.get("score", 0) or 0),
            "explanation": str(item.get("explanation", "") or ""),
            "detailed_summary": str(item.get("detailed_summary", "") or ""),
        }
    return mapping
