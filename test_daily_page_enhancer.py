#!/usr/bin/env python3
"""Deterministic sanity test for daily page post-enhancement UI."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from daily_page_enhancer import enhance_daily_archive
from generate_daily_pages import render_daily_html


def _sample_summary(title_en: str, title_zh: str, link: str) -> dict:
    items = []
    for idx in range(7):
        items.append(
            {
                "title_en": f"{title_en} {idx + 1}",
                "title_zh": f"{title_zh} {idx + 1}",
                "summary": "测试中文一句话总结",
                "link": f"{link}/{idx + 1}",
                "journal": "arXiv",
                "authors": ["Alice", "Bob"],
            }
        )
    return {
        "overview": "总览测试",
        "trends": "热点测试",
        "full_list": items,
    }


def main() -> int:
    with TemporaryDirectory() as tmpdir:
        daily_dir = Path(tmpdir) / "daily"
        daily_dir.mkdir(parents=True, exist_ok=True)

        html_24 = render_daily_html("2026-03-24", _sample_summary("Test 24 EN", "测试24中文", "https://example.com/24"))
        html_23 = render_daily_html("2026-03-23", _sample_summary("Test 23 EN", "测试23中文", "https://example.com/23"))
        (daily_dir / "2026-03-24.html").write_text(html_24, encoding="utf-8")
        (daily_dir / "2026-03-23.html").write_text(html_23, encoding="utf-8")

        (daily_dir / "summaries.json").write_text(
            json.dumps(
                {
                    "summaries": [
                        {"date": "2026-03-24", "file": "2026-03-24.html", "total": 1},
                        {"date": "2026-03-23", "file": "2026-03-23.html", "total": 1},
                    ]
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        changed = enhance_daily_archive(daily_dir / "summaries.json")
        assert changed == 2
        changed_again = enhance_daily_archive(daily_dir / "summaries.json")
        assert changed_again == 2

        enhanced_24 = (daily_dir / "2026-03-24.html").read_text(encoding="utf-8")
        enhanced_23 = (daily_dir / "2026-03-23.html").read_text(encoding="utf-8")

        assert "daily-enhancement-top-nav" in enhanced_24
        assert "daily-enhancement-bottom-nav" in enhanced_24
        assert "前一天 · 2026-03-23" in enhanced_24
        assert "后一天 · 2026-03-24" in enhanced_23
        assert "当日RSS" in enhanced_24
        assert "../feed.xml" in enhanced_24
        assert "daily-title-link" in enhanced_24
        assert "单页目录" in enhanced_24
        assert "页内定位" in enhanced_24
        assert "daily-toc-card" in enhanced_24
        assert "#highlight-1" in enhanced_24
        assert "#paper-1" in enhanced_24
        assert "# #" not in enhanced_24

    print("[OK] daily page enhancer sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
