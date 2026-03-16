#!/usr/bin/env python3
"""
One-shot full backfill for Chinese fields:
- Fill `title_zh` and `abstract_zh` for ALL articles in `data/index.json`.
- Write the updated file to both `data/index.json` and `docs/data/index.json`.

Run in GitHub Actions (recommended) with secrets:
  AI_PROVIDER=openrouter
  AI_MODEL=stepfun/step-3.5-flash:free
  AI_API_KEY=...
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List

from zh_enricher import enrich_articles_zh


def load_index(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) or {}


def save_index(path: str, articles: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)


def count_missing(articles: List[Dict[str, Any]]) -> int:
    n = 0
    for a in articles:
        if not (a.get("title_zh") or "").strip():
            n += 1
            continue
        if not (a.get("abstract_zh") or "").strip():
            n += 1
            continue
    return n


def main() -> int:
    index_path = os.environ.get("BACKFILL_INDEX_PATH") or "data/index.json"
    out_docs_path = os.environ.get("BACKFILL_DOCS_PATH") or "docs/data/index.json"

    data = load_index(index_path)
    articles = data.get("articles", []) or []
    if not articles:
        print("No articles found; abort.")
        return 1

    ai_key = (os.environ.get("AI_API_KEY") or "").strip()
    ai_provider = (os.environ.get("AI_PROVIDER") or "openrouter").strip()
    ai_model = (os.environ.get("AI_MODEL") or "").strip() or None

    batch_size = int(os.environ.get("AI_ZH_BATCH_SIZE", "16"))
    max_passes = int(os.environ.get("AI_ZH_MAX_PASSES", "20"))
    sleep_s = float(os.environ.get("AI_ZH_PASS_SLEEP_SECONDS", "1.0"))

    missing_before = count_missing(articles)
    print(f"[backfill] total={len(articles)} missing_before={missing_before}")
    if missing_before == 0:
        print("[backfill] already complete; nothing to do.")
        return 0

    for p in range(1, max_passes + 1):
        missing = count_missing(articles)
        if missing == 0:
            break

        updated = enrich_articles_zh(
            articles,
            provider_name=ai_provider,
            api_key=ai_key,
            model=ai_model,
            max_items=len(articles),
            batch_size=batch_size,
        )
        missing_after = count_missing(articles)
        print(f"[backfill] pass={p} updated={updated} missing_after={missing_after}")

        if updated == 0:
            # Avoid infinite loop: either API is failing or remaining items have no usable inputs.
            time.sleep(sleep_s * 5)
        else:
            time.sleep(sleep_s)

    missing_final = count_missing(articles)
    print(f"[backfill] missing_final={missing_final}")

    # Persist
    save_index(index_path, articles)
    save_index(out_docs_path, articles)
    print(f"[backfill] wrote {index_path} and {out_docs_path}")

    # Non-zero exit if still missing (so Actions can alert)
    return 0 if missing_final == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

