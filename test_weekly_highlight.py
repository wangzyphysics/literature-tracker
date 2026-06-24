#!/usr/bin/env python3
"""周报单篇详细解读 prompt 加长回归(stdlib-only, 无 provider)。"""
from weekly_prompts import _build_analyze_prompt


def test_weekly_analyze_prompt_is_detailed():
    p = _build_analyze_prompt("标题", "Nature", "abstract " * 100)
    assert "2~3" in p, "应要求 2~3 句"
    assert "≤100" in p, "应要求 ≤100 字"
    assert "50-80字" not in p and "50-80 字" not in p


def test_weekly_analyze_prompt_truncates_abstract_to_500():
    long_abstract = "x" * 1000
    p = _build_analyze_prompt("t", "j", long_abstract)
    assert ("x" * 500) in p
    assert ("x" * 501) not in p


if __name__ == "__main__":
    test_weekly_analyze_prompt_is_detailed()
    test_weekly_analyze_prompt_truncates_abstract_to_500()
    print("OK")
