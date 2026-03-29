#!/usr/bin/env python3
"""Utilities for repairing mojibake and common LaTeX-style text artifacts."""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any, Dict, Iterable, List

SUSPICIOUS_MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "ä¸",
    "æ",
    "ç",
    "ï¼",
    "å",
    "è¯",
    "æ",
)

LATEX_SPECIAL_MAP = {
    r"\ss": "ß",
    r"\ae": "æ",
    r"\AE": "Æ",
    r"\oe": "œ",
    r"\OE": "Œ",
    r"\aa": "å",
    r"\AA": "Å",
    r"\o": "ø",
    r"\O": "Ø",
    r"\l": "ł",
    r"\L": "Ł",
    r"\i": "i",
    r"\j": "j",
    r"\&": "&",
    r"\%": "%",
    r"\_": "_",
    r"\$": "$",
    r"\#": "#",
}

LATEX_COMMAND_TEXT_MAP = {
    r"\alpha": "α",
    r"\beta": "β",
    r"\gamma": "γ",
    r"\delta": "δ",
    r"\epsilon": "ϵ",
    r"\varepsilon": "ε",
    r"\zeta": "ζ",
    r"\eta": "η",
    r"\theta": "θ",
    r"\vartheta": "ϑ",
    r"\iota": "ι",
    r"\kappa": "κ",
    r"\lambda": "λ",
    r"\mu": "μ",
    r"\nu": "ν",
    r"\xi": "ξ",
    r"\pi": "π",
    r"\varpi": "ϖ",
    r"\rho": "ρ",
    r"\sigma": "σ",
    r"\tau": "τ",
    r"\upsilon": "υ",
    r"\phi": "φ",
    r"\varphi": "ϕ",
    r"\chi": "χ",
    r"\psi": "ψ",
    r"\omega": "ω",
    r"\Gamma": "Γ",
    r"\Delta": "Δ",
    r"\Theta": "Θ",
    r"\Lambda": "Λ",
    r"\Xi": "Ξ",
    r"\Pi": "Π",
    r"\Sigma": "Σ",
    r"\Phi": "Φ",
    r"\Psi": "Ψ",
    r"\Omega": "Ω",
    r"\times": "×",
    r"\cdot": "·",
    r"\pm": "±",
    r"\to": "→",
    r"\rightarrow": "→",
    r"\leftarrow": "←",
    r"\leftrightarrow": "↔",
    r"\geq": "≥",
    r"\leq": "≤",
    r"\neq": "≠",
}

LATEX_WRAPPER_COMMANDS = (
    "mathrm",
    "mathit",
    "mathbf",
    "mathcal",
    "mathbb",
    "text",
    "textrm",
    "textit",
    "textbf",
    "operatorname",
)

ACCENT_COMBINING = {
    "'": "\u0301",
    '"': "\u0308",
    "`": "\u0300",
    "^": "\u0302",
    "~": "\u0303",
    "=": "\u0304",
    ".": "\u0307",
    "c": "\u0327",
    "v": "\u030c",
    "u": "\u0306",
    "H": "\u030b",
    "r": "\u030a",
}

SUBSCRIPT_MAP = str.maketrans({
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
    "+": "₊",
    "-": "₋",
    "=": "₌",
    "(": "₍",
    ")": "₎",
    "a": "ₐ",
    "e": "ₑ",
    "h": "ₕ",
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "l": "ₗ",
    "m": "ₘ",
    "n": "ₙ",
    "o": "ₒ",
    "p": "ₚ",
    "r": "ᵣ",
    "s": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
})

SUPERSCRIPT_MAP = str.maketrans({
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "+": "⁺",
    "-": "⁻",
    "=": "⁼",
    "(": "⁽",
    ")": "⁾",
    "i": "ⁱ",
    "n": "ⁿ",
})

ACCENT_RE = re.compile(r"\\(?P<cmd>['\"`^~=\.Hcuvr])\s*(?:\{(?P<braced>[A-Za-z])\}|(?P<bare>[A-Za-z]))")
WRAPPER_RE = re.compile(r"\\(?P<cmd>" + "|".join(LATEX_WRAPPER_COMMANDS) + r")\{(?P<body>[^{}]+)\}")
SUBSCRIPT_RE = re.compile(r"_\{(?P<body>[^{}]+)\}|_(?P<single>[0-9aehijklmnoprstuvx+\-=()]+)")
SUPERSCRIPT_RE = re.compile(r"\^\{(?P<body>[^{}]+)\}|\^(?P<single>[0-9in+\-=()]+)")
LATEX_ARTIFACT_RE = re.compile(r"\\(?:[A-Za-z]+|['\"`^~=\.Hcuvr])")


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff"


def _mojibake_score(text: str) -> int:
    cjk_count = sum(1 for ch in text if _is_cjk(ch))
    suspicious_count = sum(text.count(marker) for marker in SUSPICIOUS_MOJIBAKE_MARKERS)
    replacement_count = text.count("�")
    control_count = sum(1 for ch in text if "\u0080" <= ch <= "\u009f")
    latin1_noise = sum(1 for ch in text if "\u00c0" <= ch <= "\u00ff")
    return cjk_count * 3 - suspicious_count * 2 - replacement_count * 4 - control_count * 3 - latin1_noise


def _fix_mojibake_once(text: str) -> str:
    if not text:
        return text
    try:
        candidate = text.encode("latin1").decode("utf-8")
    except Exception:
        return text
    return candidate if _mojibake_score(candidate) > _mojibake_score(text) else text


def _fix_mojibake(text: str) -> str:
    best = text
    for _ in range(3):
        fixed = _fix_mojibake_once(best)
        if fixed == best:
            break
        best = fixed
    return best


def _replace_latex_accent(match: re.Match[str]) -> str:
    cmd = match.group("cmd")
    base = match.group("braced") or match.group("bare") or ""
    if not base:
        return match.group(0)
    return unicodedata.normalize("NFC", base + ACCENT_COMBINING[cmd])


def _convert_script_token(token: str, table: Dict[int, str]) -> str:
    converted = token.translate(table)
    return converted if converted != token else token


def _decode_latex(text: str) -> str:
    updated = text
    for raw, replacement in LATEX_SPECIAL_MAP.items():
        updated = updated.replace(raw, replacement)
        updated = updated.replace("{" + raw + "}", replacement)

    updated = ACCENT_RE.sub(_replace_latex_accent, updated)

    for raw, replacement in LATEX_COMMAND_TEXT_MAP.items():
        updated = updated.replace(raw, replacement)

    updated = WRAPPER_RE.sub(lambda m: m.group("body"), updated)

    updated = updated.replace("$", "")
    updated = SUBSCRIPT_RE.sub(
        lambda m: _convert_script_token((m.group("body") or m.group("single") or ""), SUBSCRIPT_MAP),
        updated,
    )
    updated = SUPERSCRIPT_RE.sub(
        lambda m: _convert_script_token((m.group("body") or m.group("single") or ""), SUPERSCRIPT_MAP),
        updated,
    )

    updated = re.sub(r"\{([^\{\}\\]{1,40})\}", r"\1", updated)
    updated = updated.replace("\\", "")
    return updated


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""

    updated = _fix_mojibake(text)
    updated = html.unescape(updated)
    updated = _fix_mojibake(updated)
    for _ in range(2):
        decoded = _decode_latex(updated)
        decoded = _fix_mojibake(decoded)
        if decoded == updated:
            break
        updated = decoded
    updated = updated.replace("\u00a0", " ")
    updated = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", updated)
    return updated


def is_suspicious_text(value: Any) -> bool:
    text = str(value or "")
    if not text.strip():
        return False
    if any(marker in text for marker in SUSPICIOUS_MOJIBAKE_MARKERS):
        return True
    if any("\u0080" <= ch <= "\u009f" for ch in text):
        return True
    if "�" in text:
        return True
    return bool(LATEX_ARTIFACT_RE.search(text))


ARTICLE_TEXT_FIELDS = (
    "title",
    "title_en",
    "title_zh",
    "abstract",
    "abstract_zh",
    "summary",
    "one_sentence_summary",
    "one_sentence",
    "overview",
    "trends",
    "reason",
    "ai_explanation",
    "ai_detailed_summary",
    "journal",
)


def normalize_article_inplace(article: Dict[str, Any]) -> bool:
    changed = False
    for key in ARTICLE_TEXT_FIELDS:
        if key not in article:
            continue
        old_value = article.get(key)
        new_value = normalize_text(old_value)
        if new_value != old_value:
            article[key] = new_value
            changed = True

    authors = article.get("authors")
    if isinstance(authors, list):
        new_authors = [normalize_text(item) for item in authors]
        if new_authors != authors:
            article["authors"] = new_authors
            changed = True
    elif isinstance(authors, str):
        new_authors = normalize_text(authors)
        if new_authors != authors:
            article["authors"] = new_authors
            changed = True

    return changed


def normalize_articles_inplace(articles: Iterable[Dict[str, Any]]) -> int:
    changed = 0
    for article in articles:
        if isinstance(article, dict) and normalize_article_inplace(article):
            changed += 1
    return changed
