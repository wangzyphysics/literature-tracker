#!/usr/bin/env python3
"""Core-focus classifier: ML × ferro/凝聚态 方向判定，纯函数，无外部依赖。"""

from typing import Any, Mapping, Tuple

# —— 方法侧（AI/ML/势函数/哈密顿量）——
CORE_METHOD_TERMS: Tuple[str, ...] = (
    # 机器学习主流术语
    "machine learning", "deep learning", "neural network", "neural networks",
    "graph neural", "gnn", "transformer", "diffusion model", "generative model",
    "foundation model", "large language model", "llm", "reinforcement learning",
    "active learning", "surrogate model", "data-driven", "ai-driven",
    "artificial intelligence", "message passing", "equivariant neural",
    "equivariant gnn", "equivariant network",
    # 势函数 / Hamiltonian
    "ml potential", "mlip", "interatomic potential", "neural network potential",
    "nnp", "ml hamiltonian", "learnable hamiltonian", "symmetry-adapted",
    "equivariant force field", "mace", "nequip", "allegro", "schnet",
    "hamiltonian", "effective hamiltonian", "spin hamiltonian",
    # 中文
    "机器学习", "深度学习", "神经网络", "大语言模型", "人工智能",
    "哈密顿量", "神经网络势", "机器学习势",
)

# —— ferro/磁/凝聚态侧 ——
CORE_FERRO_TERMS: Tuple[str, ...] = (
    "ferroelectric", "ferromagnet", "ferromagnetic", "antiferromagnet",
    "antiferromagnetic", "altermagnet", "altermagnetic", "multiferroic",
    "piezoelectric", "magnetoelectric", "skyrmion", "magnon", "spin hall",
    "moire magnet", "moiré magnet", "spintronic", "spintronics",
    "spin current", "topological magnon", "spin wave", "spin texture",
    "magnetic order", "magnetic anisotropy", "exchange interaction",
    # 中文
    "铁电", "铁磁", "反铁磁", "交错磁", "多铁", "压电", "磁电",
    "斯格明子", "磁振子", "自旋霍尔", "自旋流", "磁性", "拓扑磁",
    "自旋波", "磁各向异性", "交换相互作用",
)

# —— 高分期刊（用于 score 加成，不是判定必要条件）——
_CURATED_HIGH_HINTS: Tuple[str, ...] = (
    "nature", "science", "phys. rev. lett", "physical review letters",
    "phys. rev. x", "physical review x", "nature materials", "nature physics",
    "nature communications", "npj comput", "npj quantum",
    "j. am. chem. soc", "nano letters",
)


def _normalize(text: Any) -> str:
    return " ".join(str(text or "").replace("\xa0", " ").replace("\n", " ").split()).lower()


def _item_fulltext(item: Mapping[str, Any]) -> str:
    parts = [
        item.get("title") or item.get("title_en") or "",
        item.get("title_zh") or "",
        item.get("abstract") or "",
        item.get("abstract_zh") or "",
    ]
    return _normalize(" ".join(parts))


def _item_title_text(item: Mapping[str, Any]) -> str:
    return _normalize(
        " ".join([item.get("title") or item.get("title_en") or "", item.get("title_zh") or ""])
    )


def _has_any(text: str, terms: Tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def is_core_focus(item: Mapping[str, Any]) -> bool:
    """核心关注 = 同时命中方法侧与 ferro/凝聚态侧。"""
    text = _item_fulltext(item)
    return _has_any(text, CORE_METHOD_TERMS) and _has_any(text, CORE_FERRO_TERMS)


def core_score(item: Mapping[str, Any]) -> float:
    """0.0 ~ 1.0；未命中核心关注时返回 0.0。"""
    if not is_core_focus(item):
        return 0.0
    title = _item_title_text(item)
    score = 0.5
    if _has_any(title, CORE_METHOD_TERMS):
        score += 0.15
    if _has_any(title, CORE_FERRO_TERMS):
        score += 0.15
    text = _item_fulltext(item)
    # Hamiltonian + 磁/铁 组合加成
    if ("hamiltonian" in text) and _has_any(text, ("ferro", "magnet", "铁", "磁")):
        score += 0.10
    # arXiv cond-mat 加成
    src = _normalize(item.get("source_url") or item.get("arxiv_category") or "")
    if "cond-mat" in src:
        score += 0.05
    # 高分期刊加成
    journal = _normalize(item.get("journal") or "")
    if any(hint in journal for hint in _CURATED_HIGH_HINTS):
        score += 0.05
    return min(1.0, round(score, 3))
