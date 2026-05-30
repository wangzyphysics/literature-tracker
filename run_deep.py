"""编排：拉 APS → 精读 → 海报 → 分类 → 写 feed.json。所有步骤失败静默降级。

幂等：已在 data/aps_<date>.json 里带 deep_analysis 的论文直接复用，不重复调用 gpt-5.5。
默认只处理最近 1 天（DEEP_WINDOW_DAYS=1），手动 dispatch 可传更大窗口做增量回填。
"""
import os, json, glob, datetime, hashlib
from concurrent.futures import ThreadPoolExecutor

from aps_client import ApsClient
from ai_summarizer import build_provider
from deep_reader import deep_read
from poster_generator import generate_poster
from auto_classifier import classify
from image_provider import generate_and_save
from feed_builder import build_feed, write_feed_json


def _deep_complete(text):
    """深读是否完整：苏格拉底 prompt 第五部分为「创新评估」，截断会缺它。"""
    return bool(text) and ("创新" in text) and len(text) >= 5000


def _enrich_one(meta, client, provider, out_dir, cached=None):
    # 幂等复用：只有已生成完整深读(含第五部分创新评估)的论文才算完成、直接复用
    if cached and _deep_complete(cached.get("deep_analysis")):
        return cached
    md = client.fetch_markdown(meta)
    rec = dict(meta)
    rec["source"] = "APS"
    rec["category"] = (cached or {}).get("category") or classify(meta, provider=provider)
    rec["deep_analysis"] = deep_read(meta, md, provider=provider) if md else ""
    # 复用已有海报，避免重复图像生成；缺失才生成
    rec["poster"] = (cached or {}).get("poster") or (
        generate_poster(meta, md, provider=provider, out_dir=out_dir) if md else None)
    return rec


def process_date(date, client, provider, out_dir="docs/images/posters", max_workers=5,
                 cache=None, max_new=None):
    """处理某天的全文论文。cache 命中(已带深读)直接复用；max_new 限制本轮新生成的论文数
    （超出预算的新论文本轮跳过，下轮再处理，靠幂等累积回填）。返回 (records, new_used)。"""
    metas = client.fetch_metadata(date)
    full = [m for m in metas if m.get("has_full_text")]
    if not full:
        return [], 0
    cache = cache or {}
    cached, fresh = [], []
    for m in full:
        c = cache.get(m.get("doc_id") or m.get("paper_id"))
        # 只有带完整深读才算完成；缺深读或被截断(缺第五部分)的要重试(走 fresh，复用海报)
        (cached if (c and _deep_complete(c.get("deep_analysis"))) else fresh).append((m, c))
    if max_new is not None:
        fresh = fresh[:max(0, max_new)]
    results = [c for (_m, c) in cached]  # 复用缓存，零成本
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_enrich_one, m, client, provider, out_dir, c) for (m, c) in fresh]
        for f in futs:
            try: results.append(f.result())
            except Exception as e: print(f"⚠️ enrich failed: {e}")
    return results, len(fresh)


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


def _enrich_arxiv_one(a, provider, out_dir):
    rec = dict(a)
    rec["source"] = "arxiv"
    rec["category"] = classify(a, provider=provider)
    # 幂等：已有 image 的不重复生成
    if a.get("image"):
        return rec
    h = hashlib.sha1((a.get("link") or a.get("title", "")).encode("utf-8")).hexdigest()[:16]
    prompt = ("Flat vector minimalist scientific illustration, single clear concept, "
              "clean lines, off-white background, deep blue + teal accents, no text. "
              f"Concept: {a.get('title','')[:120]}")
    saved = generate_and_save(prompt, os.path.join(out_dir, f"{h}.webp"), max_edge=768)
    rec["image"] = (saved or "").replace("docs/", "") or None
    return rec


def enrich_arxiv_core(items, provider=None, out_dir="docs/images/cards", max_workers=5):
    items = items or []
    out = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_enrich_arxiv_one, a, provider, out_dir) for a in items]
        for f in futs:
            try: out.append(f.result())
            except Exception as e: print(f"⚠️ arxiv enrich failed: {e}")
    return out


def _load_arxiv_core(date):
    path = f"data/arxiv_core_{date}.json"
    if os.path.exists(path):
        try: return json.load(open(path, encoding="utf-8"))
        except Exception: return []
    return []


def _load_aps_cache(date):
    """已生成的 aps_<date>.json → {doc_id: rec} 供幂等复用。"""
    path = f"data/aps_{date}.json"
    if not os.path.exists(path):
        return {}
    try:
        recs = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    return {(r.get("doc_id") or r.get("paper_id")): r for r in recs if isinstance(r, dict)}


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
    # APS data lags ~1-2 days, so window must cover it (default 4 days).
    window = int(os.environ.get("DEEP_WINDOW_DAYS", "4"))
    workers = int(os.environ.get("DEEP_WORKERS", "5"))
    # Per-run budget of NEW papers to deep-read (prevents 90-min timeout on first backfill;
    # idempotent cache lets repeated/scheduled runs finish the rest).
    budget = int(os.environ.get("DEEP_MAX_NEW_PER_RUN", "14"))
    arxiv_images = (os.environ.get("DEEP_ENABLE_ARXIV_IMAGES", "") or "").lower() in ("1", "true", "yes")
    dates = client.list_dates(window_days=window)
    print(f"📚 APS dates to process (window={window}, new-budget={budget}): {dates}")
    # newest first so the freshest papers get processed within budget
    for d in sorted(dates, reverse=True):
        cache = _load_aps_cache(d)
        aps, used = process_date(d, client, provider, max_workers=workers,
                                 cache=cache, max_new=budget)
        budget -= used
        enriched = sum(1 for a in aps if a.get("deep_analysis"))
        print(f"  {d}: {len(aps)} papers ({enriched} with deep_analysis), {used} new this run")
        if aps:
            _save_aps_index(d, aps)
        if arxiv_images:
            try:
                core = _load_arxiv_core(d)
                if core:
                    out = enrich_arxiv_core(core, provider=provider, max_workers=workers)
                    with open(f"data/arxiv_core_{d}.json", "w", encoding="utf-8") as f:
                        json.dump(out, f, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ arxiv core enrich failed for {d}: {e}")
    write_feed_json(_load_existing_feeds(), window_days=60)
    prune_images(window_days=60)
    print("✅ run_deep done; feed.json written")


if __name__ == "__main__":
    main()
