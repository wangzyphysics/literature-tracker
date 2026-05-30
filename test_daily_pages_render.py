#!/usr/bin/env python3
"""
Deterministic sanity test (no network):
- Verify daily page renderer uses `full_list` (and falls back to `summaries`).
- Verify daily page renderer carries the layout fixes that avoid global header/body bleed-through.
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
                "authors": list("Alice Smith, Bob Jones, Carol Chen"),
            }
        ],
    }
    html = render_daily_html(date_str, summary_full_list)
    assert "Test English Title" in html
    assert "测试中文标题" in html
    assert "测试中文一句话总结" in html
    assert "https://example.com/paper" in html
    assert "arXiv" in html
    assert "Alice Smith, Bob Jones, Carol Chen" in html
    assert "AI × Science 文献日报" in html
    assert 'application/rss+xml' in html
    assert '2026-03-15.xml' in html
    assert "今日摘要" in html
    assert "交叉重点" in html
    assert "完整速览" in html
    assert '<div class="daily-hero">' in html
    assert '<header class="daily-hero">' not in html
    assert 'body::before { content: none !important; }' in html

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

    # ----- Core-focus section -----
    from generate_daily_pages import render_daily_html as _rdh
    summary_with_core = {
        'date':'2026-04-15','total':0,'overview':'','trends':'',
        'full_list':[],'summaries':[],'ml_highlights':[],'ferro_highlights':[],
        'core_items':[{
            'title_en':'Equivariant neural network potential for ferroelectric perovskites',
            'title_zh':'用于铁电钙钛矿的等变神经网络势','abstract_zh':'为 BaTiO3 训练 MACE。',
            'summary':'一句话总结。','link':'https://ex/1','journal':'Nature',
            'method_point':'MACE 等变势训练','related_work':'与 NequIP/Allegro 同族','implication':'可迁移反铁磁'
        }],
        'core_direction_note':'本日 ML×ferro 方向出现 MACE 势应用于 BaTiO3。'
    }
    html_core = _rdh('2026-04-15', summary_with_core)
    if 'id="core-focus"' not in html_core:
        print('FAIL: missing core-focus section when core_items present'); return 1
    if '核心关注（ML' not in html_core:
        print('FAIL: missing core heading'); return 1
    if '方法要点' not in html_core or '启示' not in html_core:
        print('FAIL: missing deep fields'); return 1

    summary_no_core = dict(summary_with_core)
    summary_no_core['core_items'] = []
    summary_no_core['core_direction_note'] = ''
    html_empty = _rdh('2026-04-15', summary_no_core)
    if 'id="core-focus"' in html_empty:
        print('FAIL: should NOT render core section when empty'); return 1

    print("[OK] daily renderer sanity checks passed")
    return 0


def test_daily_renders_deep_read_section():
    from generate_daily_pages import render_deep_section
    aps = [{"title": "T", "title_zh": "标题", "category": "AI×物理",
            "deep_analysis": "## 第一部分：核心概览\n内容",
            "poster": {"image": "images/posters/d1.webp",
                       "elements": {"研究问题": "q", "创新方法": "m",
                                    "工作流程": "f", "关键结果": "r", "应用价值": "v"}},
            "link": "http://x", "doc_id": "d1"}]
    html = render_deep_section(aps)
    assert "今日精读" in html
    # daily pages live at docs/daily/<date>.html → sibling assets need ../ prefix
    assert 'src="../images/posters/d1.webp"' in html
    assert "poster-overlay" in html
    assert "AI×物理" in html
    assert 'data-bookmark-key="http://x"' in html


def test_render_deep_section_empty_returns_empty():
    from generate_daily_pages import render_deep_section
    assert render_deep_section([]) == ""


if __name__ == "__main__":
    raise SystemExit(main())
