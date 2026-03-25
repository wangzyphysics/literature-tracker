#!/usr/bin/env python3
"""
Deterministic sanity test (no network):
- Verify daily page renderer uses `full_list` (and falls back to `summaries`).
"""

from generate_daily_pages import render_daily_html


def main() -> int:
    date_str = "2026-03-15"

    summary_full_list = {
        "overview": "总览测试",
        "trends": "热点测试",
        "full_list": [
            {
                "title_en": "Test English Title",
                "title_zh": "测试中文标题",
                "summary": "测试中文一句话总结",
                "link": "https://example.com/paper",
                "journal": "arXiv",
                "authors": ["Alice", "Bob", "Carol"],
            }
        ],
    }
    html = render_daily_html(date_str, summary_full_list)
    assert "Test English Title" in html
    assert "测试中文标题" in html
    assert "测试中文一句话总结" in html
    assert "https://example.com/paper" in html
    assert "arXiv" in html
    assert "Alice" in html
    assert "AI × Science 文献日报" in html
    assert "今日摘要" in html
    assert "交叉重点" in html
    assert "完整速览" in html

    summary_summaries_only = {
        "overview": "总览测试2",
        "trends": "热点测试2",
        "summaries": [
            {
                "title_en": "Test2 EN",
                "title_zh": "测试2中文",
                "summary": "测试2总结",
                "link": "https://example.com/paper2",
            }
        ],
    }
    html2 = render_daily_html(date_str, summary_summaries_only)
    assert "Test2 EN" in html2
    assert "测试2中文" in html2
    assert "完整速览" in html2

    print("[OK] daily renderer sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
