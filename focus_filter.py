#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focus filtering for AI × physics / chemistry / materials literature.

The goal is high recall for AI4Science / physical-science papers while aggressively
removing clearly off-topic biomedical, clinical, education, and social-science
content that may slip through broad keyword RSS feeds.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

AI_TERMS: Tuple[str, ...] = (
    'machine learning', 'deep learning', 'neural network', 'neural networks', 'graph neural', 'gnn',
    'transformer', 'diffusion model', 'generative model', 'foundation model', 'large language model',
    'llm', 'reinforcement learning', 'active learning', 'surrogate model', 'data-driven', 'ai-driven',
    'artificial intelligence', 'message passing', 'equivariant neural', 'ml potential', 'mlip',
    '机器学习', '深度学习', '神经网络', '大语言模型', '人工智能',
)

PHYSICS_TERMS: Tuple[str, ...] = (
    'quantum', 'spin', 'magnetic', 'magnetism', 'ferroelectric', 'ferromagnet', 'antiferromagnet',
    'multiferroic', 'condensed matter', 'superconduct', 'phonon', 'lattice', 'exciton', 'moire',
    'moiré', 'topological', 'skyrmion', 'hall effect', 'electronic structure', 'band structure',
    'weyl', 'josephson', 'magnon', 'altermagnet', 'quantum gas', 'plasma',
    '凝聚态', '量子', '磁性', '铁电', '铁磁', '反铁磁', '多铁', '超导', '声子', '晶格', '拓扑',
)

PHYSICS_CORE_TERMS: Tuple[str, ...] = PHYSICS_TERMS + (
    'quantum spin hall', 'magnetoresistance', 'magnetoelectric', 'spin hall', 'single-photon',
    'van der waals heterostructure', 'moire potential',
)

DAILY_PHYSICS_TERMS: Tuple[str, ...] = (
    'quantum', 'spin', 'magnetic', 'magnetism', 'ferroelectric', 'ferromagnet', 'antiferromagnet',
    'multiferroic', 'superconduct', 'phonon', 'exciton', 'moire', 'moiré', 'electronic structure',
    'band structure', 'hall effect', 'skyrmion', 'altermagnet', 'kagome', 'spintronic', 'spintronics',
    'photonic crystal', 'electron tomography',
)

CHEMISTRY_TERMS: Tuple[str, ...] = (
    'chemical', 'chemistry', 'molecule', 'molecular', 'catalyst', 'catalysis', 'electrochem',
    'reaction mechanism', 'reaction network', 'spectroscopy', 'photochemistry', 'surface chemistry',
    'computational chemistry', 'molecular design', 'polymerization', 'solvation', 'adsorption',
    '化学', '分子', '催化', '电化学', '反应机理', '光化学', '光谱',
)

CHEMISTRY_CORE_TERMS: Tuple[str, ...] = (
    'catalyst', 'catalysis', 'electrochem', 'reaction mechanism', 'reaction network', 'spectroscopy',
    'photochemistry', 'surface chemistry', 'computational chemistry', 'molecular design',
    'polymerization', 'adsorption', 'solvation', 'chemical space', 'ligand design',
    '催化', '电化学', '反应机理', '光化学', '光谱',
)

MATERIALS_TERMS: Tuple[str, ...] = (
    'material', 'materials', 'crystal', 'crystalline', 'perovskite', 'semiconductor', 'electrode',
    'battery', 'alloy', 'oxide', 'heterostructure', 'thin film', 'surface', 'interface', 'nanostructure',
    '2d material', '2d materials', 'device', 'optoelectronic', 'materials discovery', 'solar cell',
    'solid electrolyte', 'photovoltaic', 'memristor', 'dielectric', 'monolayer',
    '固态', '材料', '晶体', '钙钛矿', '半导体', '电极', '电池', '合金', '氧化物', '异质结构',
    '薄膜', '界面', '器件',
)

MATERIALS_CORE_TERMS: Tuple[str, ...] = (
    'perovskite', 'semiconductor', 'electrode', 'battery', 'alloy', 'oxide', 'heterostructure',
    'thin film', 'surface', 'interface', '2d material', '2d materials', 'materials discovery',
    'solar cell', 'solid electrolyte', 'photovoltaic', 'memristor', 'dielectric', 'monolayer',
    'crystal structure prediction', '晶体', '钙钛矿', '半导体', '电极', '电池', '合金', '氧化物',
    '异质结构', '薄膜', '界面', '器件',
)

SIMULATION_TERMS: Tuple[str, ...] = (
    'dft', 'density functional', 'ab initio', 'first-principles', 'first principles', 'molecular dynamics',
    'monte carlo', 'phase field', 'finite element', 'atomistic simulation', 'electronic-structure',
    'computational materials', 'physics-informed', 'simulation', 'interatomic potential',
    'crystal structure prediction', '拟合势', '模拟', '第一性原理', '分子动力学', '相场', '有限元',
    '原子模拟', '电子结构', '物理约束',
)

SIMULATION_CORE_TERMS: Tuple[str, ...] = (
    'dft', 'density functional', 'ab initio', 'first-principles', 'first principles', 'molecular dynamics',
    'monte carlo', 'phase field', 'finite element', 'atomistic simulation', 'electronic structure',
    'electronic-structure', 'computational materials', 'physics-informed', 'interatomic potential',
    'crystal structure prediction', 'materials discovery', '第一性原理', '分子动力学', '相场', '有限元',
    '原子模拟', '电子结构', '物理约束',
)

DAILY_SIMULATION_TERMS: Tuple[str, ...] = tuple(term for term in SIMULATION_CORE_TERMS if term != 'physics-informed')

CURATED_JOURNAL_HINTS: Tuple[str, ...] = (
    'phys. rev.', 'physical review', 'j. chem. phys', 'journal of chemical physics', 'advanced materials',
    'advanced science', 'materials today', 'npj comput', 'npj quantum', 'nature materials', 'nature physics',
    'nature chemistry', 'nature electronics', 'nature energy', 'science advances', 'nano letters', 'jacs',
    'computer physics communications', 'computational materials science', 'digital discovery',
    'nature machine intelligence', 'phys. rev. materials',
    # 新增2区期刊
    'journal of applied physics', 'j. appl. phys.',
    'journal of physics: condensed matter', 'j. phys. condens. matter',
    'physical chemistry chemical physics', 'pccp',
    'journal of materials chemistry', 'j. mater. chem.',
    'ceramics international',
    'journal of the american ceramic society', 'j. am. ceram. soc.',
    'scripta materialia',
    'intermetallics',
    'journal of alloys and compounds', 'j. alloys compd.',
    'journal of magnetism and magnetic materials', 'j. magn. magn. mater.',
    'ieee transactions on magnetics', 'ieee trans. magn.',
    'physica status solidi', 'phys. stat. sol.',
    'applied physics letters', 'appl. phys. lett.',
)

ALLOWED_ARXIV_PHYSICAL: Tuple[str, ...] = (
    'cond-mat', 'physics.comp-ph', 'physics.chem-ph',
)

ALLOWED_ARXIV_AI: Tuple[str, ...] = (
    'cs.lg', 'stat.ml', 'cs.ai',
)

NEGATIVE_CLINICAL_TERMS: Tuple[str, ...] = (
    'patient', 'patients', 'clinical', 'clinic', 'biomedical', 'biomed', 'disease', 'diseases', 'cancer', 'tumor', 'tumour',
    'therapy', 'therapeutic', 'diagnosis', 'diagnostic', 'hospital', 'healthcare', 'medical', 'medicine',
    'drug', 'drugs', 'pharmac', 'pathology', 'radiology', 'epidemiology', 'histology', 'oncology',
    'survival', 'prognostic', 'risk stratification', 'case report', 'sickle cell', 'stroke', 'dialysis',
    'hemodialysis', 'glioblastoma', 'alzheimer', 'alzheimer\'s', 'parkinson', 'pancreatic', 'prostate cancer',
    'breast cancer', 'colorectal cancer', 'kidney disease', 'uterine', 'fertility', 'clinical-grade',
    '临床', '患者', '疾病', '癌', '肿瘤', '治疗', '诊断', '医院', '医学', '药物', '病理', '放射',
)

NEGATIVE_LIFE_SCIENCE_TERMS: Tuple[str, ...] = (
    'immune', 'immunology', 'immunotherapy', 'protein', 'proteins', 'peptide',
    'dna', 'rna', 'genome', 'genomic', 'genomics', 'transcriptomic', 'proteomic', 'cell biology',
    'single-cell', 'stem cell', 'cell line', 'mouse', 'mice', 'rat', 'rats', 'vaccine', 'virus', 'viral',
    'bacteria', 'bacterial', 'fungal', 'microbiome', 'nuclease', 'adenocarcinoma', 'biopsy', 'in vivo',
    'biochemical recurrence', 'follicular', 'ovarian', 'lung adenocarcinoma', 'prostate', 'breast',
    '免疫', '蛋白', '肽', '基因组', '转录组', '蛋白质组', '单细胞', '小鼠', '疫苗', '病毒', '细菌',
)

NEGATIVE_SOCIAL_TERMS: Tuple[str, ...] = (
    'education', 'educational', 'student', 'students', 'school', 'qualitative', 'cross-sectional',
    'retrospective', 'survey', 'sociology', 'public health', 'teacher', 'curriculum', 'undergraduate',
    'intervention', 'competency', 'learning experience', 'online class', '访谈', '教育', '学生', '横断面',
    '回顾性', '调查', '公共卫生',
)


def _normalize_text(value: Any) -> str:
    return ' '.join(str(value or '').replace('\xa0', ' ').replace('\n', ' ').split()).lower()


def _item_text(item: Mapping[str, Any]) -> str:
    parts = [
        item.get('title') or item.get('title_en') or '',
        item.get('title_zh') or '',
        item.get('abstract') or '',
        item.get('abstract_zh') or '',
        item.get('summary') or '',
        item.get('journal') or '',
        item.get('source_url') or '',
        item.get('arxiv_category') or '',
    ]
    return _normalize_text(' '.join(parts))


def _item_title_focus_text(item: Mapping[str, Any]) -> str:
    parts = [
        item.get('title') or item.get('title_en') or '',
        item.get('title_zh') or '',
        item.get('journal') or '',
        item.get('arxiv_category') or '',
    ]
    return _normalize_text(' '.join(parts))


def _has_any(text: str, terms: Sequence[str], *, whole_term: bool = False) -> bool:
    for term in terms:
        if not term:
            continue
        if not whole_term or any(ord(ch) > 127 for ch in term):
            if term in text:
                return True
            continue
        pattern = rf'(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])'
        if re.search(pattern, text):
            return True
    return False


def analyze_focus(item: Mapping[str, Any]) -> Dict[str, bool]:
    text = _item_text(item)
    journal = _normalize_text(item.get('journal') or '')
    arxiv_category = _normalize_text(item.get('arxiv_category') or '')

    has_ai = _has_any(text, AI_TERMS)
    has_physics = _has_any(text, PHYSICS_TERMS)
    has_chemistry = _has_any(text, CHEMISTRY_TERMS)
    has_materials = _has_any(text, MATERIALS_TERMS)
    has_simulation = _has_any(text, SIMULATION_TERMS)

    strong_physics = _has_any(text, PHYSICS_CORE_TERMS)
    strong_chemistry = _has_any(text, CHEMISTRY_CORE_TERMS)
    strong_materials = _has_any(text, MATERIALS_CORE_TERMS)
    strong_simulation = _has_any(text, SIMULATION_CORE_TERMS)

    curated_journal = _has_any(journal, CURATED_JOURNAL_HINTS)
    arxiv_physical = _has_any(arxiv_category, ALLOWED_ARXIV_PHYSICAL)
    arxiv_ai = _has_any(arxiv_category, ALLOWED_ARXIV_AI)

    clinical_biomed = _has_any(text, NEGATIVE_CLINICAL_TERMS, whole_term=True)
    life_science = clinical_biomed or _has_any(text, NEGATIVE_LIFE_SCIENCE_TERMS, whole_term=True)
    social = _has_any(text, NEGATIVE_SOCIAL_TERMS, whole_term=True)

    direct_science = strong_physics or strong_chemistry or strong_materials or strong_simulation or (arxiv_physical and (has_physics or has_chemistry or has_materials or strong_simulation))
    journal_supported = curated_journal and (strong_physics or strong_chemistry or strong_materials or strong_simulation)

    hard_offtopic = social or clinical_biomed or (life_science and not (strong_physics or strong_materials or strong_simulation))
    target_domain = not hard_offtopic and (direct_science or journal_supported or (arxiv_ai and direct_science))
    ai_science = not hard_offtopic and has_ai and (direct_science or journal_supported)

    return {
        'has_ai': has_ai,
        'has_physics': has_physics,
        'has_chemistry': has_chemistry,
        'has_materials': has_materials,
        'has_simulation': has_simulation,
        'strong_physics': strong_physics,
        'strong_chemistry': strong_chemistry,
        'strong_materials': strong_materials,
        'strong_simulation': strong_simulation,
        'curated_journal': curated_journal,
        'arxiv_physical': arxiv_physical,
        'arxiv_ai': arxiv_ai,
        'clinical_biomed': clinical_biomed,
        'life_science': life_science,
        'social': social,
        'direct_science': direct_science,
        'hard_offtopic': hard_offtopic,
        'target_domain': target_domain,
        'ai_science': ai_science,
    }


def is_target_domain(item: Mapping[str, Any]) -> bool:
    return analyze_focus(item)['target_domain']


def is_hard_offtopic(item: Mapping[str, Any]) -> bool:
    return analyze_focus(item)['hard_offtopic']


def filter_focus_items(items: Iterable[Mapping[str, Any]]) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    kept: List[Mapping[str, Any]] = []
    dropped: List[Mapping[str, Any]] = []
    for item in items:
        if is_target_domain(item):
            kept.append(item)
        else:
            dropped.append(item)
    return kept, dropped


# 日报聚焦关键词：磁性/铁电相关
DAILY_FERRO_MAGNET_TERMS: Tuple[str, ...] = (
    'ferro', 'magnet', 'magnetic', 'magnetism', 'ferromagnet', 'ferroelectric', 
    'antiferromagnet', 'multiferroic', 'magnetoresistance', 'magnetoelectric',
    'spin', 'spintronic', 'spintronics', 'skyrmion', 'altermagnet',
    '铁磁', '铁电', '反铁磁', '多铁', '磁性', '磁电阻', '磁电',
)

def is_daily_focus(item: Mapping[str, Any]) -> bool:
    signals = analyze_focus(item)
    if not signals['target_domain']:
        return False

    title_text = _item_title_focus_text(item)
    title_has_ai = _has_any(title_text, AI_TERMS)
    title_has_physics = _has_any(title_text, DAILY_PHYSICS_TERMS)
    title_has_chemistry = _has_any(title_text, CHEMISTRY_CORE_TERMS)
    title_has_materials = _has_any(title_text, MATERIALS_CORE_TERMS)
    title_has_simulation = _has_any(title_text, DAILY_SIMULATION_TERMS)
    title_has_ferro_magnet = _has_any(title_text, DAILY_FERRO_MAGNET_TERMS)
    title_core_science = title_has_physics or title_has_chemistry or title_has_materials or title_has_simulation
    
    # 放宽标准：
    # 1. 原有标准：标题AI+核心科学 或 标题模拟+核心科学
    # 2. 新增：标题含ferro/magnet关键词的物理/材料文献（无需AI）
    return (
        (title_has_ai and title_core_science) or 
        (title_has_simulation and title_core_science) or
        (title_has_ferro_magnet and (title_has_physics or title_has_materials))
    )


def daily_focus_priority(item: Mapping[str, Any]) -> tuple:
    signals = analyze_focus(item)
    title_text = _item_title_focus_text(item)
    title_has_ai = _has_any(title_text, AI_TERMS)
    title_has_simulation = _has_any(title_text, DAILY_SIMULATION_TERMS)
    title_has_physics = _has_any(title_text, DAILY_PHYSICS_TERMS)
    title_has_chemistry = _has_any(title_text, CHEMISTRY_CORE_TERMS)
    title_has_materials = _has_any(title_text, MATERIALS_CORE_TERMS)
    title_has_ferro_magnet = _has_any(title_text, DAILY_FERRO_MAGNET_TERMS)
    title_core_science = title_has_physics or title_has_chemistry or title_has_materials or title_has_simulation or signals['arxiv_physical']

    if title_has_ai and title_core_science:
        band = 0
    elif title_has_simulation and title_core_science:
        band = 1
    elif title_has_ferro_magnet and (title_has_physics or title_has_materials):
        band = 2  # 新增：ferro/magnet物理/材料文献
    elif signals['has_ai'] and (signals['strong_physics'] or signals['strong_chemistry'] or signals['strong_materials'] or signals['strong_simulation']):
        band = 3
    elif signals['curated_journal'] or signals['arxiv_physical']:
        band = 4
    else:
        band = 5
    return (band,) + focus_priority(item)


def filter_daily_focus_items(
    items: Iterable[Mapping[str, Any]],
    *,
    min_keep: int = 12,
    max_keep: int = 60,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    eligible = [item for item in items if is_target_domain(item)]
    eligible = sorted(eligible, key=daily_focus_priority)

    def item_key(item: Mapping[str, Any]) -> str:
        return str(item.get('link') or item.get('title') or item.get('title_en') or item.get('title_zh') or '')

    selected: List[Mapping[str, Any]] = []
    selected_keys = set()

    def add(item: Mapping[str, Any]) -> None:
        key = item_key(item)
        if not key or key in selected_keys or len(selected) >= max_keep:
            return
        selected.append(item)
        selected_keys.add(key)

    primary = [item for item in eligible if is_daily_focus(item)]
    for item in primary:
        add(item)

    target_keep = min(max_keep, max(min_keep, len(selected)))
    if len(selected) < target_keep:
        for item in eligible:
            add(item)
            if len(selected) >= target_keep:
                break

    dropped = [item for item in eligible if item_key(item) not in selected_keys]
    return selected, dropped


def topic_bucket(item: Mapping[str, Any]) -> str:
    signals = analyze_focus(item)
    if signals['strong_physics'] or signals['has_physics']:
        return 'physics'
    if signals['strong_chemistry'] or signals['has_chemistry']:
        return 'chemistry'
    if signals['strong_materials'] or signals['has_materials']:
        return 'materials'
    if signals['has_ai'] or signals['strong_simulation'] or signals['has_simulation']:
        return 'methods'
    return 'other'


def focus_priority(item: Mapping[str, Any]) -> tuple:
    signals = analyze_focus(item)
    bucket = topic_bucket(item)
    bucket_rank = {
        'physics': 0,
        'chemistry': 1,
        'materials': 2,
        'methods': 3,
        'other': 4,
    }.get(bucket, 5)
    try:
        ai_score = float(item.get('ai_score') or 0)
    except Exception:
        ai_score = 0.0
    journal = _normalize_text(item.get('journal') or '')
    is_arxiv = journal == 'arxiv'
    direct_bonus = 0 if signals['direct_science'] else 1
    return (
        0 if signals['ai_science'] else 1,
        direct_bonus,
        bucket_rank,
        0 if is_arxiv else 1,
        -ai_score,
        _normalize_text(item.get('title') or item.get('title_zh') or ''),
    )
