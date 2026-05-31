"""APS 全文 → 苏格拉底式深度精读（gpt-5.5）。失败返回空串。"""
import os, ast
from string import Template

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "deep_read.txt")

def _load_template():
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def _fmt_authors(raw):
    if isinstance(raw, list):
        return ", ".join(map(str, raw))
    try:
        v = ast.literal_eval(raw) if isinstance(raw, str) and raw.strip().startswith("[") else raw
        return ", ".join(map(str, v)) if isinstance(v, list) else str(raw)
    except Exception:
        return str(raw)

def build_deep_prompt(title, authors, year, context, max_chars=40000):
    ctx = (context or "")
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars] + "\n\n[内容过长已截断]"
    tmpl = Template(_load_template())
    return tmpl.safe_substitute(title=str(title or ""),
                                authors=_fmt_authors(authors),
                                year=str(year or ""), context=ctx)

def deep_read(meta, markdown, provider):
    if not markdown or provider is None:
        return ""
    try:
        prompt = build_deep_prompt(meta.get("title"), meta.get("authors"),
                                   meta.get("year"), markdown)
        return (provider.call_api(prompt) or "").strip()
    except Exception as e:
        print(f"⚠️ deep_read failed for {meta.get('doc_id')}: {e}")
        return ""

_ABS_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "abstract_analysis.txt")

def _load_abs_template():
    with open(_ABS_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def build_abstract_prompt(title, authors, abstract, max_chars=6000):
    abs_txt = (abstract or "")[:max_chars]
    return Template(_load_abs_template()).safe_substitute(
        title=str(title or ""), authors=_fmt_authors(authors), abstract=abs_txt)

def abstract_read(meta, abstract, provider):
    if not abstract or provider is None:
        return ""
    try:
        prompt = build_abstract_prompt(meta.get("title"), meta.get("authors"), abstract)
        return (provider.call_api(prompt) or "").strip()
    except Exception as e:
        print(f"⚠️ abstract_read failed for {meta.get('doc_id') or meta.get('link')}: {e}")
        return ""
