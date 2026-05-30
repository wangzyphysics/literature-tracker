"""编排：拉 APS → 精读 → 海报 → 分类 → 写 feed.json。所有步骤失败静默降级。"""
import os, json, glob, datetime
from concurrent.futures import ThreadPoolExecutor

from aps_client import ApsClient
from ai_summarizer import build_provider
from deep_reader import deep_read
from poster_generator import generate_poster
from auto_classifier import classify
from image_provider import generate_and_save
from feed_builder import build_feed, write_feed_json

def _enrich_one(meta, client, provider, out_dir):
    md = client.fetch_markdown(meta)
    rec = dict(meta)
    rec["source"] = "APS"
    rec["category"] = classify(meta, provider=provider)
    rec["deep_analysis"] = deep_read(meta, md, provider=provider) if md else ""
    rec["poster"] = generate_poster(meta, md, provider=provider, out_dir=out_dir) if md else None
    return rec

def process_date(date, client, provider, out_dir="docs/images/posters", max_workers=3):
    metas = client.fetch_metadata(date)
    full = [m for m in metas if m.get("has_full_text")]
    if not full:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_enrich_one, m, client, provider, out_dir) for m in full]
        for f in futs:
            try: results.append(f.result())
            except Exception as e: print(f"⚠️ enrich failed: {e}")
    return results

def prune_images(window_days=60, today=None, dirs=("docs/images/posters", "docs/images/cards")):
    today = today or datetime.date.today()
    if isinstance(today, str):
        today = datetime.date.fromisoformat(today)
    cutoff = today - datetime.timedelta(days=window_days)
    for d in dirs:
        for p in glob.glob(os.path.join(d, "*.webp")):
            try:
                mtime = datetime.date.fromtimestamp(os.path.getmtime(p))
                if mtime < cutoff:
                    os.remove(p)
            except Exception:
                pass

def _load_arxiv_core(date):
    path = f"data/arxiv_core_{date}.json"
    if os.path.exists(path):
        try: return json.load(open(path, encoding="utf-8"))
        except Exception: return []
    return []

def _save_aps_index(date, aps):
    os.makedirs("data", exist_ok=True)
    with open(f"data/aps_{date}.json", "w", encoding="utf-8") as f:
        json.dump(aps, f, ensure_ascii=False)

def _load_existing_feeds():
    feeds = []
    for p in sorted(glob.glob("data/aps_*.json")):
        date = os.path.basename(p)[4:-5]
        try: aps = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        feeds.append(build_feed(aps, _load_arxiv_core(date), date=date))
    return feeds

def main():
    provider = build_provider(os.environ.get("AI_PROVIDER", "aigw"),
                              os.environ.get("AI_API_KEY", ""),
                              os.environ.get("AI_MODEL", "gpt-5.5"))
    client = ApsClient()
    window = int(os.environ.get("DEEP_WINDOW_DAYS", "3"))
    dates = client.list_dates(window_days=window)
    for d in dates:
        aps = process_date(d, client, provider)
        _save_aps_index(d, aps)
    write_feed_json(_load_existing_feeds(), window_days=60)
    prune_images(window_days=60)

if __name__ == "__main__":
    main()
