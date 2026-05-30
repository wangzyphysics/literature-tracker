"""概念海报：gpt-5.5 抽 5 要素 + gpt-image-2 生成纯视觉背景。"""
import os, re, json
from string import Template
from image_provider import generate_and_save

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "poster_elements.txt")
_KEYS = ["研究问题", "创新方法", "工作流程", "关键结果", "应用价值"]

def _load_template():
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def _parse_json(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not all(k in d for k in _KEYS):
        return None
    return {k: str(d.get(k, "")) for k in _KEYS}

def extract_elements(meta, markdown, provider, language="中文", max_chars=40000):
    if not markdown or provider is None:
        return None
    ctx = markdown[:max_chars]
    prompt = Template(_load_template()).safe_substitute(
        language=language, title=str(meta.get("title", "")), context=ctx)
    try:
        return _parse_json(provider.call_api(prompt))
    except Exception as e:
        print(f"⚠️ extract_elements failed: {e}"); return None

def build_background_prompt(elements):
    hint = "; ".join(f"{k}: {(elements or {}).get(k,'')[:60]}" for k in _KEYS)
    return (
        "Generate a Modern Minimalist Tech Infographic poster background, "
        "flat vector illustration with subtle isometric elements, high-quality "
        "corporate Memphis design style, clean lines and geometric shapes. "
        "Left-to-right process flow with 5 implied node areas. "
        "Background solid off-white #F5F5F7, no clutter. "
        "Palette: deep academic blue and slate grey, vibrant orange/teal accents, "
        "high contrast. 16:9 aspect ratio, 4K, high quality. "
        "IMPORTANT: render NO text / NO words / NO letters in the image — "
        "purely visual icons and shapes (text will be overlaid separately). "
        "No photorealism, no messy sketches, no chaotic background. "
        f"Visual theme hints (do not render as text): {hint}")

def generate_poster(meta, markdown, provider, out_dir="docs/images/posters",
                    api_key=None, base=None):
    elements = extract_elements(meta, markdown, provider)
    if not elements:
        return None
    doc_id = meta.get("doc_id") or meta.get("paper_id") or "unknown"
    out_path = os.path.join(out_dir, f"{doc_id}.webp")
    prompt = build_background_prompt(elements)
    saved = generate_and_save(prompt, out_path, max_edge=1024,
                              api_key=api_key, base=base)
    return {"elements": elements,
            "image": (saved or "").replace("docs/", "") or None,
            "doc_id": doc_id}
