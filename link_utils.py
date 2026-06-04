"""链接归一化工具：裸 DOI → https://doi.org/...；http(s) 链接原样返回。

从 feed_builder 迁出，作为单一来源被 generate_daily_pages / feed_builder 复用。
"""


def normalize_link(link):
    s = (link or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    return f"https://doi.org/{s}"
