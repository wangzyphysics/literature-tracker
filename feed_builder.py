"""聚合 APS 精读 + arXiv 核心 → docs/data/feed.json，含 60 天滚动裁剪。"""
import os, json, datetime

def _item_from_aps(a):
    poster = a.get("poster") or {}
    return {"source": "APS", "journal": a.get("journal", ""),
            "title_en": a.get("title", ""), "title_zh": a.get("title_zh", ""),
            "summary": a.get("summary", ""), "category": a.get("category", "其他"),
            "link": a.get("link") or a.get("doi", ""), "doc_id": a.get("doc_id", ""),
            "image": poster.get("image"), "poster_elements": poster.get("elements"),
            "deep_analysis": a.get("deep_analysis", ""), "enriched": True}

def _item_from_arxiv(a):
    return {"source": "arxiv", "journal": a.get("journal", "arXiv"),
            "title_en": a.get("title", ""), "title_zh": a.get("title_zh", ""),
            "summary": a.get("summary", ""), "category": a.get("category", "其他"),
            "link": a.get("link", ""), "image": a.get("image"),
            "poster_elements": None, "deep_analysis": "", "enriched": bool(a.get("image"))}

def build_feed(aps_items, arxiv_items, date):
    items = [_item_from_aps(a) for a in (aps_items or [])] + \
            [_item_from_arxiv(a) for a in (arxiv_items or [])]
    return {"date": date, "items": items}

def prune_window(feeds, today=None, window_days=60):
    today = today or datetime.date.today().isoformat()
    cutoff = (datetime.date.fromisoformat(today) - datetime.timedelta(days=window_days)).isoformat()
    return [f for f in feeds if f.get("date", "") >= cutoff]

def write_feed_json(per_day_feeds, path="docs/data/feed.json", today=None, window_days=60):
    kept = prune_window(sorted(per_day_feeds, key=lambda f: f["date"], reverse=True),
                        today=today, window_days=window_days)
    flat = []
    for f in kept:
        for it in f["items"]:
            flat.append({**it, "date": f["date"]})
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump({"generated": today, "items": flat}, fp, ensure_ascii=False)
    return path
