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
    # image/text separated: 5 elements live in a dedicated block, not overlaid on image
    assert "poster-overlay" not in html
    assert "daily-deep-elements" in html
    assert "AI×物理" in html
    assert 'data-bookmark-key="http://x"' in html


def test_render_deep_section_empty_returns_empty():
    from generate_daily_pages import render_deep_section
    assert render_deep_section([]) == ""


def test_deep_section_has_feed_link_and_no_overlay():
    from generate_daily_pages import render_deep_section
    aps = [{"title": "T", "title_zh": "标题", "category": "AI×物理",
            "deep_analysis": "x",
            "poster": {"image": "images/posters/d1.webp",
                       "elements": {"研究问题": "q", "创新方法": "m", "工作流程": "f",
                                    "关键结果": "r", "应用价值": "v"}},
            "link": "10.1103/abc", "doc_id": "d1"}]
    html = render_deep_section(aps, date="2026-05-28")
    assert "feed.html" in html and "在 Feed" in html
    # image/text separated: elements live in a non-overlay block, image still present
    assert "poster-overlay" not in html
    assert "daily-deep-elements" in html
    assert "../images/posters/d1.webp" in html
    # bare DOI normalized to a real URL somewhere in the card
    assert "doi.org/10.1103/abc" in html


def test_deep_section_empty_still_empty():
    from generate_daily_pages import render_deep_section
    assert render_deep_section([], date="2026-05-28") == ""


def test_build_core_export_has_category_and_link():
    from generate_daily_pages import build_core_export
    items = [{"title": "ML interatomic potential for perovskite",
              "title_zh": "钙钛矿的机器学习势", "summary": "图神经网络势",
              "abstract": "graph neural network potential for materials",
              "abstract_zh": "用于材料的图神经网络势",
              "link": "http://arxiv.org/abs/2601.001", "journal": "arXiv"}]
    out = build_core_export(items)
    assert out[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert out[0]["abstract"]
    assert out[0]["link"].startswith("http")
    assert out[0]["title_zh"] == "钙钛矿的机器学习势"

def test_build_tier2_candidates_picks_ai_cross():
    from generate_daily_pages import build_tier2_candidates
    full = [
        {"title": "Deep learning for catalyst discovery", "summary": "neural network",
         "abstract": "graph neural network for chemistry catalyst", "link": "http://x", "journal": "arXiv"},
        {"title": "A study of medieval poetry", "summary": "", "abstract": "", "link": "http://y"},
    ]
    cand = build_tier2_candidates(full)
    links = [c["link"] for c in cand]
    assert "http://x" in links and "http://y" not in links
    assert cand and cand[0]["category"]


def test_load_enrichment_keys_by_link_and_skips_plain():
    import json, os, tempfile
    from generate_daily_pages import load_enrichment
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "data"), exist_ok=True)
    rows = [
        {"link": "http://arxiv.org/abs/1", "deep_analysis": "## 深析",
         "image": "images/posters/a.webp",
         "poster": {"elements": {"研究问题": "q", "创新方法": "m"}},
         "category": "AI×物理", "title_zh": "中文一"},
        {"link": "10.1103/xyz", "deep_analysis": "## 二",
         "poster": {"image": "images/posters/b.webp", "elements": {"关键结果": "r"}},
         "category": "AI×化学·材料", "title_zh": "中文二"},
        {"link": "http://arxiv.org/abs/3", "summary": "no enrichment"},  # plain → skipped
    ]
    with open(os.path.join(d, "data", "arxiv_core_2026-06-01.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    cwd = os.getcwd()
    try:
        os.chdir(d)
        m = load_enrichment("2026-06-01")
    finally:
        os.chdir(cwd)
    assert "http://arxiv.org/abs/1" in m
    assert m["http://arxiv.org/abs/1"]["image"] == "images/posters/a.webp"
    assert m["http://arxiv.org/abs/1"]["elements"]["研究问题"] == "q"
    # bare DOI normalized as key
    assert "https://doi.org/10.1103/xyz" in m
    assert m["https://doi.org/10.1103/xyz"]["image"] == "images/posters/b.webp"
    # plain row (no deep, no image) skipped
    assert "http://arxiv.org/abs/3" not in m


def test_load_enrichment_missing_file_returns_empty():
    from generate_daily_pages import load_enrichment
    assert load_enrichment("1999-01-01") == {}


def test_build_unified_items_merges_and_sorts():
    from generate_daily_pages import build_unified_items
    full_list = [
        {"title": "Plain paper", "title_en": "Plain paper", "summary": "x",
         "link": "http://arxiv.org/abs/plain"},
        {"title": "AI cross arxiv", "title_en": "AI cross arxiv", "title_zh": "交叉",
         "summary": "y", "link": "http://arxiv.org/abs/cross"},
    ]
    enrich_map = {
        "http://arxiv.org/abs/cross": {"deep_analysis": "## d", "image": "images/posters/c.webp",
                                       "elements": {"研究问题": "q"}, "category": "AI×物理",
                                       "title_zh": "交叉"},
    }
    aps_items = [
        {"title": "APS fulltext", "title_zh": None, "doi": "10.1103/abc", "category": "软物质",
         "deep_analysis": "## aps", "poster": {"image": "images/posters/aps.webp",
                                               "elements": {"创新方法": "m"}}},
        {"title": "APS plain", "doi": "10.1103/plain", "poster": {}},  # no enrichment → skipped
    ]
    out = build_unified_items(full_list, enrich_map, aps_items)
    tiers = [it["_tier"] for it in out]
    assert tiers == sorted(tiers)
    assert out[0]["_tier"] == 0 and out[0]["_enrich"]["image"] == "images/posters/aps.webp"
    assert out[0]["link"] == "https://doi.org/10.1103/abc"  # bare DOI normalized
    cross = next(it for it in out if it["link"] == "http://arxiv.org/abs/cross")
    assert cross["_tier"] == 1 and cross["_enrich"]["category"] == "AI×物理"
    plain = next(it for it in out if it["link"] == "http://arxiv.org/abs/plain")
    assert plain["_tier"] == 2 and plain["_enrich"] is None
    assert all("APS plain" != it.get("title") for it in out)


def test_build_unified_items_dedups_aps_already_in_full_list():
    from generate_daily_pages import build_unified_items
    full_list = [{"title": "Dup", "link": "https://doi.org/10.1103/dup", "summary": "s"}]
    aps_items = [{"title": "Dup", "doi": "10.1103/dup", "deep_analysis": "d",
                  "poster": {"image": "p.webp"}}]
    out = build_unified_items(full_list, {}, aps_items)
    assert len(out) == 1 and out[0]["_tier"] == 0


def test_render_unified_item_enriched_has_details_and_image():
    from generate_daily_pages import render_unified_item
    item = {"title": "Cross", "title_en": "Cross", "title_zh": "交叉标题",
            "summary": "一句话亮点", "link": "http://arxiv.org/abs/cross", "journal": "arXiv",
            "_tier": 1, "_enrich": {"deep_analysis": "## 深析正文", "image": "images/posters/c.webp",
                                    "elements": {"研究问题": "q", "创新方法": "m", "工作流程": "f",
                                                 "关键结果": "r", "应用价值": "v"},
                                    "category": "AI×物理", "title_zh": "交叉标题"}}
    html = render_unified_item(item, 1)
    assert "交叉标题" in html
    assert "enrich-badge" in html and "含图深析" in html
    assert "<details" in html
    assert 'src="../images/posters/c.webp"' in html
    assert "daily-deep-elements" in html and "研究问题" in html
    assert "深析正文" in html
    assert 'data-bookmark-key="http://arxiv.org/abs/cross"' in html
    assert "poster-overlay" not in html


def test_render_unified_item_plain_has_no_details():
    from generate_daily_pages import render_unified_item
    item = {"title": "Plain", "title_en": "Plain", "summary": "brief",
            "link": "http://x", "journal": "arXiv", "_tier": 2, "_enrich": None}
    html = render_unified_item(item, 2)
    assert "<details" not in html
    assert "enrich-badge" not in html
    assert "brief" in html
    assert 'data-bookmark-key="http://x"' in html


if __name__ == "__main__":
    raise SystemExit(main())


def test_classify_uses_title_en_when_title_empty():
    # full_list stores English under title_en with title empty → must still classify AI×
    from generate_daily_pages import build_tier2_candidates, build_core_export
    full = [{"title": "", "title_en": "Physics-Informed Machine Learning for quantum materials",
             "title_zh": "面向量子材料的物理信息机器学习", "summary": "机器学习",
             "abstract_zh": "用神经网络预测材料性质", "link": "http://x", "is_core_focus": False}]
    cand = build_tier2_candidates(full)
    assert cand, "AI-cross paper with title_en must be selected"
    assert cand[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert cand[0]["title"].startswith("Physics-Informed")  # English title resolved
    assert cand[0]["abstract"]  # non-empty (falls back to abstract_zh)
    ce = build_core_export(full)
    assert ce[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert ce[0]["abstract"]
