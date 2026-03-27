#!/usr/bin/env python3
"""Deterministic sanity test for weekly page post-enhancement UI."""

from pathlib import Path
from tempfile import TemporaryDirectory

from weekly_summary import WeeklySummarizer


def _sample_summary(week_start: str, title_prefix: str, base_url: str) -> dict:
    both = [
        {
            "id": f"cross-{week_start}",
            "title_zh": f"{title_prefix} 交叉中文标题",
            "title": f"{title_prefix} Cross Paper",
            "journal": "arXiv",
            "authors": ["Alice", "Bob"],
            "ai_analysis": "使用 AI 建模材料与凝聚态物理问题。",
            "abstract_zh": "中文摘要内容。",
            "abstract": "English abstract content.",
            "pub_date": week_start,
            "link": f"{base_url}/cross",
            "is_ferro": True,
            "is_ai": True,
        }
    ]
    ferro = [
        {
            "id": f"ferro-{week_start}",
            "title_zh": f"{title_prefix} 磁性中文标题",
            "title": f"{title_prefix} Ferro Paper",
            "journal": "Nature Materials",
            "authors": ["Carol"],
            "abstract_zh": "磁性摘要。",
            "abstract": "Ferro abstract.",
            "pub_date": week_start,
            "link": f"{base_url}/ferro",
            "is_ferro": True,
            "is_ai": False,
        }
    ]
    ai = [
        {
            "id": f"ai-{week_start}",
            "title_zh": f"{title_prefix} AI 中文标题",
            "title": f"{title_prefix} AI Paper",
            "journal": "Science",
            "authors": ["Dave", "Eve"],
            "abstract_zh": "AI 摘要。",
            "abstract": "AI abstract.",
            "pub_date": week_start,
            "link": f"{base_url}/ai",
            "is_ferro": False,
            "is_ai": True,
        }
    ]
    all_articles = both + ferro + ai
    return {
        "week_start": week_start,
        "week_end": "2026-03-22" if week_start == "2026-03-16" else "2026-03-15",
        "overview": "本周总览测试。",
        "trends": "趋势测试。",
        "outlook": "展望测试。",
        "generated_by": "test",
        "both_articles": both,
        "ferro_articles": ferro,
        "ai_articles": ai,
        "all_articles": all_articles,
        "by_journal": {
            "arXiv": [both[0]],
            "Nature Materials": [ferro[0]],
            "Science": [ai[0]],
        },
    }


def main() -> int:
    with TemporaryDirectory() as tmpdir:
        summarizer = WeeklySummarizer()
        summarizer.save_summary_html(_sample_summary("2026-03-09", "Week09", "https://example.com/week09"), tmpdir)
        summarizer.save_summary_html(_sample_summary("2026-03-16", "Week16", "https://example.com/week16"), tmpdir)

        html_latest = (Path(tmpdir) / "2026-03-16.html").read_text(encoding="utf-8")
        html_prev = (Path(tmpdir) / "2026-03-09.html").read_text(encoding="utf-8")

        assert "weekly-enhancement-top-nav" in html_latest
        assert "weekly-enhancement-bottom-nav" in html_latest
        assert "前一周 · 2026-03-09 → 2026-03-15" in html_latest
        assert "后一周 · 2026-03-16 → 2026-03-22" in html_prev
        assert "单页目录" in html_latest
        assert "weekly-outline-scroll" in html_latest
        assert "站点RSS" in html_latest
        assert "页内定位" in html_latest
        assert "所在专题" in html_latest
        assert "weekly-permalink-link" in html_latest
        assert "weekly-report-sidebar" in html_latest

    print("[OK] weekly page enhancer sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
