"""规则优先 + gpt-5.5 兜底 的文章分类。"""
from focus_core import classify_taxonomy, TAXONOMY

# Valid category names, sorted longest-first to prevent substring false-matches
_VALID = sorted(set(TAXONOMY.keys()) | {"其他"}, key=len, reverse=True)


def classify(article, provider=None):
    rule = classify_taxonomy(article)
    if rule != "其他":
        return rule
    if provider is None:
        return "其他"
    cats = "、".join(TAXONOMY.keys())
    prompt = (f"把下面这篇论文归入且仅归入这些类别之一（只输出类别名，不要解释）：{cats}、其他。\n"
              f"标题：{article.get('title','')}\n摘要：{(article.get('summary') or article.get('abstract') or '')[:600]}")
    try:
        ans = (provider.call_api(prompt) or "").strip()
    except Exception:
        return "其他"
    for c in _VALID:
        if c in ans:
            return c
    return "其他"
