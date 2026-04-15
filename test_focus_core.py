#!/usr/bin/env python3
"""Unit tests for focus_core module — ML × ferro/凝聚态 核心关注判定。"""

from focus_core import is_core_focus, core_score, CORE_METHOD_TERMS, CORE_FERRO_TERMS


def main() -> int:
    failures = []

    # 明确命中：ML + ferro
    hit_ml_ferro = {
        "title": "Equivariant neural network potential for ferroelectric perovskites",
        "abstract": "We train a MACE model on BaTiO3 and report coercive fields.",
        "journal": "npj Computational Materials",
    }
    if not is_core_focus(hit_ml_ferro):
        failures.append("EXPECTED core_focus for ML+ferro")
    if not (0.60 <= core_score(hit_ml_ferro) <= 1.0):
        failures.append(f"EXPECTED score in [0.60,1.0], got {core_score(hit_ml_ferro)}")

    # 明确命中：Hamiltonian + 磁性
    hit_hamiltonian_magnet = {
        "title": "Learnable spin Hamiltonian for antiferromagnets",
        "abstract": "A graph neural network learns an effective Hamiltonian for CrI3.",
        "journal": "Phys. Rev. Lett.",
    }
    if not is_core_focus(hit_hamiltonian_magnet):
        failures.append("EXPECTED core_focus for hamiltonian+magnet")

    # 仅 ML，不 ferro → 否
    only_ml = {
        "title": "A transformer for protein structure prediction",
        "abstract": "Alphafold-style model applied to membrane proteins.",
    }
    if is_core_focus(only_ml):
        failures.append("UNEXPECTED core_focus for only-ML")
    if core_score(only_ml) != 0.0:
        failures.append(f"UNEXPECTED non-zero score for only-ML: {core_score(only_ml)}")

    # 仅 ferro，不 ML → 否
    only_ferro = {
        "title": "Room-temperature ferroelectricity in 2D NbOI2",
        "abstract": "We show robust out-of-plane polarization.",
    }
    if is_core_focus(only_ferro):
        failures.append("UNEXPECTED core_focus for only-ferro")

    # 中文命中
    zh_hit = {
        "title": "Machine learning based study on CrSBr",
        "abstract": "利用机器学习和DFT方法研究了二维铁磁体CrSBr的层间耦合。",
    }
    if not is_core_focus(zh_hit):
        failures.append("EXPECTED core_focus for Chinese 机器学习+铁磁")

    # Title 命中权重高
    title_both = {
        "title": "Equivariant GNN for magnon band structures",
        "abstract": "Short.",
    }
    score_title = core_score(title_both)
    # Abstract-only 命中
    abs_only = {
        "title": "A study on 2D materials",
        "abstract": "Equivariant GNN learns magnon bands in antiferromagnets.",
    }
    score_abs = core_score(abs_only)
    if score_title <= score_abs:
        failures.append(f"title hits should outweigh abstract-only: title={score_title}, abs={score_abs}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: focus_core unit tests passed")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
