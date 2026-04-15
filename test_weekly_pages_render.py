#!/usr/bin/env python3
"""Deterministic sanity test for weekly page rendering (no network)."""

from pathlib import Path
from tempfile import TemporaryDirectory

from weekly_summary import WeeklySummarizer


def main() -> int:
    summary = {
        "week_start": "2026-03-16",
        "week_end": "2026-03-22",
        "overview": "本周围绕 AI × 材料交叉、磁性与分子设计展开。",
        "trends": "交叉研究继续集中在 AI 驱动材料发现与自旋体系建模。",
        "outlook": "后续值得关注预印本向顶刊转化与实验验证闭环。",
        "generated_by": "test",
        "both_articles": [
            {
                "id": "cross-1",
                "title_zh": "测试交叉文献中文标题",
                "title": "Test Cross Paper",
                "journal": "arXiv",
                "authors": ["Alice", "Bob", "Carol"],
                "ai_analysis": "利用机器学习建模磁性材料相变。",
                "abstract_zh": "中文摘要内容。",
                "abstract": "English abstract content.",
                "pub_date": "2026-03-18",
                "link": "https://example.com/cross",
                "is_ferro": True,
                "is_ai": True,
            }
        ],
        "ferro_articles": [
            {
                "id": "ferro-1",
                "title_zh": "测试磁性文献中文标题",
                "title": "Test Ferro Paper",
                "journal": "Nature Materials",
                "authors": ["Dave"],
                "abstract_zh": "磁性文献中文摘要。",
                "abstract": "Ferro abstract.",
                "pub_date": "2026-03-17",
                "link": "https://example.com/ferro",
                "is_ferro": True,
                "is_ai": False,
            }
        ],
        "ai_articles": [
            {
                "id": "ai-1",
                "title_zh": "测试 AI 文献中文标题",
                "title": "Test AI Paper",
                "journal": "Science",
                "authors": ["Eve", "Frank"],
                "abstract_zh": "AI 文献中文摘要。",
                "abstract": "AI abstract.",
                "pub_date": "2026-03-19",
                "link": "https://example.com/ai",
                "is_ferro": False,
                "is_ai": True,
            }
        ],
    }
    summary["all_articles"] = summary["both_articles"] + summary["ferro_articles"] + summary["ai_articles"]
    summary["by_journal"] = {
        "arXiv": [summary["both_articles"][0]],
        "Nature Materials": [summary["ferro_articles"][0]],
        "Science": [summary["ai_articles"][0]],
    }

    with TemporaryDirectory() as tmpdir:
        path = WeeklySummarizer().save_summary_html(summary, tmpdir)
        html = Path(path).read_text(encoding="utf-8")

    assert "AI × Science 周报" in html
    assert "本周总览" in html
    assert "交叉研究" in html
    assert "磁性 / 铁电专题" in html
    assert "AI / 机器学习专题" in html
    assert "期刊分布" in html
    assert "测试交叉文献中文标题" in html
    assert "Test Cross Paper" in html
    assert "Alice" in html
    assert "https://example.com/cross" in html
    assert "toggleTheme" in html
    assert "toggleAbstract" in html
    assert "查看完整摘要" in html

    # ----- Weekly core-focus section -----
    from weekly_summary import render_core_weekly_section as _rcw
    wk = {
        'core_items':[{'title':'等变神经网络势','title_en':'Equivariant NNP','link':'https://ex/1','journal':'Nature','abstract_zh':'为 BaTiO3 训练 MACE。','method_point':'MACE 等变势','related_work':'与 NequIP 同族','implication':'可迁移反铁磁'}],
        'core_weekly_note':'本周 MACE 用于 BaTiO3；CrI3 中 GNN 学习自旋哈密顿量。'
    }
    block = _rcw(wk)
    if 'weekly-core-section' not in block or '本周核心方向' not in block:
        print('FAIL: weekly core section missing heading'); return 1
    if '方法要点' not in block or '启示' not in block:
        print('FAIL: weekly deep labels missing'); return 1
    if _rcw({'core_items':[], 'core_weekly_note':''}).strip() != '':
        print('FAIL: weekly core section should be empty when no items'); return 1

    print("[OK] weekly renderer sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
