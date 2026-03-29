#!/usr/bin/env python3
"""Sanity tests for mojibake / LaTeX text repair helpers."""

from text_normalizer import is_suspicious_text, normalize_text


def main() -> int:
    mojibake = "è½¨é\x81\x93å¡\x9eè´\x9då\x85\x8bæ\x95\x88åº\x94"
    assert normalize_text(mojibake) == "轨道塞贝克效应"

    latex = 'J\\"orn St\\"ohler, V. Bal\\\'edent, St\\v{r}eda, {\\L}ukasz'
    fixed_latex = normalize_text(latex)
    assert "Jörn" in fixed_latex
    assert "Stöhler" in fixed_latex
    assert "Balédent" in fixed_latex
    assert "Středa" in fixed_latex
    assert "Łukasz" in fixed_latex

    formula = "Mn$_2$Ru$_{1-x}$Ga and 4\\times10^10"
    fixed_formula = normalize_text(formula)
    assert "Mn₂Ru₁₋ₓGa" in fixed_formula
    assert "4×10¹⁰" in fixed_formula

    assert is_suspicious_text(mojibake)
    assert is_suspicious_text(latex)
    assert not is_suspicious_text("正常中文标题")

    print("[OK] text normalizer sanity checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
