#!/usr/bin/env python3
"""Helpers for normalizing inconsistent author metadata."""

from __future__ import annotations

import re
from typing import Any, List

from text_normalizer import normalize_text


def _compact_text(value: Any) -> str:
    return " ".join(normalize_text(value).replace("\u00a0", " ").split())


def _looks_like_character_stream(items: List[str]) -> bool:
    meaningful = [item for item in items if str(item)]
    if len(meaningful) < 8:
        return False
    short_count = sum(1 for item in meaningful if len(str(item).strip()) <= 1)
    return short_count / max(1, len(meaningful)) >= 0.85


def normalize_author_names(authors: Any) -> List[str]:
    if not authors:
        return []

    if isinstance(authors, list):
        raw_items = [str(item) for item in authors if str(item)]
        if _looks_like_character_stream(raw_items):
            merged = _compact_text("".join(raw_items))
            return [part.strip() for part in re.split(r"\s*,\s*", merged) if part.strip()]

        cleaned = [_compact_text(item) for item in raw_items]
        return [item for item in cleaned if item]

    text = _compact_text(authors)
    return [text] if text else []


def authors_label(authors: Any, *, max_names: int = 6) -> str:
    cleaned = normalize_author_names(authors)
    if not cleaned:
        return ""
    if len(cleaned) > max_names:
        return ", ".join(cleaned[:max_names]) + f" 等{len(cleaned)}位作者"
    return ", ".join(cleaned)
