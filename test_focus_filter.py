#!/usr/bin/env python3
"""Deterministic sanity tests for focus filtering heuristics."""

from focus_filter import analyze_focus, filter_focus_items, is_daily_focus, is_target_domain, topic_bucket


def main() -> int:
    medical = {
        "title": "Wireless, non-invasive, high-resolution thrill sensor for continuous vascular access monitoring of hemodialysis patients",
        "journal": "Nature Communications",
    }
    cancer_ai = {
        "title": "Deep learning from routine histology improves risk stratification for biochemical recurrence in prostate cancer",
        "journal": "Preprints",
    }
    education = {
        "title": "Exploring students perceptions of their learning experience and self efficacy in physics online class with project based learning",
        "journal": "arXiv",
        "arxiv_category": "cs.LG",
    }
    ai_materials = {
        "title": "Machine learning interatomic potential for ferroelectric perovskites",
        "journal": "arXiv",
        "arxiv_category": "cs.LG",
    }
    condensed_matter = {
        "title": "First-principles study of quantum spin Hall effect in moire materials",
        "journal": "Phys. Rev. Lett.",
    }
    methods = {
        "title": "Toward Reaction Vessel Mimicry: Machine Learning-Assisted Automated Exploration of Alkene Polymerization and Its Mechanism",
        "journal": "ACS",
    }
    pure_ai = {
        "title": "A Federated Many-to-One Hopfield model for associative Neural Networks",
        "journal": "arXiv",
        "arxiv_category": "cs.LG",
    }

    assert is_target_domain(ai_materials)
    assert is_target_domain(condensed_matter)
    assert is_target_domain(methods)
    assert not is_target_domain(medical)
    assert not is_target_domain(cancer_ai)
    assert not is_target_domain(education)
    assert is_daily_focus(ai_materials)
    assert is_daily_focus(methods)
    assert not is_daily_focus(pure_ai)
    assert topic_bucket(ai_materials) in {"physics", "materials", "methods"}
    assert topic_bucket(condensed_matter) == "physics"
    assert analyze_focus(medical)["hard_offtopic"] is True
    assert analyze_focus(cancer_ai)["hard_offtopic"] is True
    assert analyze_focus(education)["hard_offtopic"] is True

    kept, dropped = filter_focus_items([medical, cancer_ai, education, ai_materials, condensed_matter, methods])
    assert len(kept) == 3
    assert len(dropped) == 3
    assert {item["title"] for item in dropped} == {medical["title"], cancer_ai["title"], education["title"]}

    print("[OK] focus filter sanity checks passed")

    # ——— 核心关注置顶测试 ———
    from focus_filter import focus_priority as _fp
    core_item = {
        "title": "Equivariant neural network potential for ferroelectric perovskites",
        "abstract": "We train MACE on BaTiO3.",
        "journal": "npj Computational Materials",
    }
    noncore_item = {
        "title": "A transformer for protein structure prediction",
        "journal": "Nature",
    }
    if _fp(core_item) >= _fp(noncore_item):
        print("FAIL: core_focus item should sort BEFORE non-core")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
