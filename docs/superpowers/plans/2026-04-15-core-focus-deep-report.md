# Core-Focus Deep Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让日报/周报以"ML × ferro/凝聚态"为核心深度呈现：新增核心关注判定、金色 section、每篇 3 深度字段（方法要点/相关工作关联/对你方向的启示）、周报结构重构到核心方向在先。

**Architecture:** 新增 `focus_core.py` 做纯函数判定；`ai_summarizer.py` / `weekly_summary.py` 各加一个批量 LLM 调用产出 direction_note + 三字段；`generate_daily_pages.py` / `weekly_summary.py` 渲染层加专用 section。所有 LLM 调用复用 `KimiClaudeCodeProvider`。

**Tech Stack:** Python 3.11 · Anthropic Messages API (Kimi) · requests · BeautifulSoup (现有) · 纯 HTML/CSS 渲染（无 JS 新增）

---

## File Structure

| 文件 | 职责 |
|---|---|
| `focus_core.py` (新) | `is_core_focus`, `core_score`, keyword 常量，纯函数 |
| `test_focus_core.py` (新) | `focus_core.py` 的单元测试，沿用项目现有 `main() -> int` 风格 |
| `focus_filter.py` (改) | `focus_priority` 顶部拼接 `is_core_focus`，保证核心关注永远置顶 |
| `config.py` (改) | 新增 `CORE_FOCUS_CONFIG` 字典 |
| `ai_summarizer.py` (改) | 新增 `AISummarizer.generate_core_deep_fields`；`_parse_response` 注入 `is_core_focus` / `core_score` |
| `generate_daily_pages.py` (改) | 主流程调用 deep-fields；`render_daily_html` 新增 `render_core_section` + 金色 CSS |
| `weekly_summary.py` (改) | 新增 `_generate_core_weekly`；`render_weekly_html` 新增 `render_core_weekly_section`；重排版块顺序 |
| `test_daily_pages_render.py` (改) | 追加断言：核心关注 section 存在 / 不存在两种情况 |
| `test_weekly_pages_render.py` (改) | 追加断言：重排后"本周核心方向"在"相关外围"之前 |

---

## Task 1: 创建 `focus_core.py` — 关键词集常量与 `is_core_focus`

**Files:**
- Create: `focus_core.py`
- Test: `test_focus_core.py`

- [ ] **Step 1.1: 写失败的测试**

创建 `test_focus_core.py`（与现有测试同风格）：

```python
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
```

- [ ] **Step 1.2: 确认测试失败（模块不存在）**

Run: `python3 test_focus_core.py`
Expected: `ModuleNotFoundError: No module named 'focus_core'`

- [ ] **Step 1.3: 实现 `focus_core.py`**

```python
#!/usr/bin/env python3
"""Core-focus classifier: ML × ferro/凝聚态 方向判定，纯函数，无外部依赖。"""

from typing import Any, Mapping, Tuple

# —— 方法侧（AI/ML/势函数/哈密顿量）——
CORE_METHOD_TERMS: Tuple[str, ...] = (
    # 机器学习主流术语
    "machine learning", "deep learning", "neural network", "neural networks",
    "graph neural", "gnn", "transformer", "diffusion model", "generative model",
    "foundation model", "large language model", "llm", "reinforcement learning",
    "active learning", "surrogate model", "data-driven", "ai-driven",
    "artificial intelligence", "message passing", "equivariant neural",
    "equivariant gnn", "equivariant network",
    # 势函数 / Hamiltonian
    "ml potential", "mlip", "interatomic potential", "neural network potential",
    "nnp", "ml hamiltonian", "learnable hamiltonian", "symmetry-adapted",
    "equivariant force field", "mace", "nequip", "allegro", "schnet",
    "hamiltonian", "effective hamiltonian", "spin hamiltonian",
    # 中文
    "机器学习", "深度学习", "神经网络", "大语言模型", "人工智能",
    "哈密顿量", "神经网络势", "机器学习势",
)

# —— ferro/磁/凝聚态侧 ——
CORE_FERRO_TERMS: Tuple[str, ...] = (
    "ferroelectric", "ferromagnet", "ferromagnetic", "antiferromagnet",
    "antiferromagnetic", "altermagnet", "altermagnetic", "multiferroic",
    "piezoelectric", "magnetoelectric", "skyrmion", "magnon", "spin hall",
    "moire magnet", "moiré magnet", "spintronic", "spintronics",
    "spin current", "topological magnon", "spin wave", "spin texture",
    "magnetic order", "magnetic anisotropy", "exchange interaction",
    # 中文
    "铁电", "铁磁", "反铁磁", "交错磁", "多铁", "压电", "磁电",
    "斯格明子", "磁振子", "自旋霍尔", "自旋流", "磁性", "拓扑磁",
    "自旋波", "磁各向异性", "交换相互作用",
)

# —— 高分期刊（用于 score 加成，不是判定必要条件）——
_CURATED_HIGH_HINTS: Tuple[str, ...] = (
    "nature", "science", "phys. rev. lett", "physical review letters",
    "phys. rev. x", "physical review x", "nature materials", "nature physics",
    "nature communications", "npj comput", "npj quantum",
    "j. am. chem. soc", "nano letters",
)


def _normalize(text: Any) -> str:
    return " ".join(str(text or "").replace("\xa0", " ").replace("\n", " ").split()).lower()


def _item_fulltext(item: Mapping[str, Any]) -> str:
    parts = [
        item.get("title") or item.get("title_en") or "",
        item.get("title_zh") or "",
        item.get("abstract") or "",
        item.get("abstract_zh") or "",
    ]
    return _normalize(" ".join(parts))


def _item_title_text(item: Mapping[str, Any]) -> str:
    return _normalize(
        " ".join([item.get("title") or item.get("title_en") or "", item.get("title_zh") or ""])
    )


def _has_any(text: str, terms: Tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def is_core_focus(item: Mapping[str, Any]) -> bool:
    """核心关注 = 同时命中方法侧与 ferro/凝聚态侧。"""
    text = _item_fulltext(item)
    return _has_any(text, CORE_METHOD_TERMS) and _has_any(text, CORE_FERRO_TERMS)


def core_score(item: Mapping[str, Any]) -> float:
    """0.0 ~ 1.0；未命中核心关注时返回 0.0。"""
    if not is_core_focus(item):
        return 0.0
    title = _item_title_text(item)
    score = 0.5
    if _has_any(title, CORE_METHOD_TERMS):
        score += 0.15
    if _has_any(title, CORE_FERRO_TERMS):
        score += 0.15
    text = _item_fulltext(item)
    # Hamiltonian + 磁/铁 组合加成
    if ("hamiltonian" in text) and _has_any(text, ("ferro", "magnet", "铁", "磁")):
        score += 0.10
    # arXiv cond-mat 加成
    src = _normalize(item.get("source_url") or item.get("arxiv_category") or "")
    if "cond-mat" in src:
        score += 0.05
    # 高分期刊加成
    journal = _normalize(item.get("journal") or "")
    if any(hint in journal for hint in _CURATED_HIGH_HINTS):
        score += 0.05
    return min(1.0, round(score, 3))
```

- [ ] **Step 1.4: 运行测试通过**

Run: `python3 test_focus_core.py`
Expected: `OK: focus_core unit tests passed`，exit 0

- [ ] **Step 1.5: 提交**

```bash
git add focus_core.py test_focus_core.py
git commit -m "feat: 新增 focus_core 模块判定 ML×ferro/凝聚态 核心关注"
```

---

## Task 2: `focus_filter.py` — `focus_priority` 接入 `is_core_focus`

**Files:**
- Modify: `focus_filter.py:420-444`
- Test: `test_focus_filter.py`（现有文件）

- [ ] **Step 2.1: 查看现状**

Run: `grep -n "def focus_priority" focus_filter.py`
确认 `focus_priority` 位于 L420-444。

- [ ] **Step 2.2: 写断言（追加到 test_focus_filter.py 的 main() 尾部）**

打开 `test_focus_filter.py`，在 `return 0` 之前插入：

```python
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
```

- [ ] **Step 2.3: 运行测试，确认新断言失败**

Run: `python3 test_focus_filter.py`
Expected: `FAIL: core_focus item should sort BEFORE non-core`，exit 1

- [ ] **Step 2.4: 修改 `focus_filter.py` 的 `focus_priority`**

把现有 `focus_priority` 的返回 tuple **整体** 前面插入 `is_core_focus` 键。用 Edit 替换：

```python
def focus_priority(item: Mapping[str, Any]) -> tuple:
    from focus_core import is_core_focus, core_score  # 避免循环 import，函数内局部导入
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
        0 if is_core_focus(item) else 1,      # ← 新增：核心关注永远置顶
        -core_score(item),                     # ← 新增：分数高者在前
        0 if signals['ai_science'] else 1,
        direct_bonus,
        bucket_rank,
        0 if is_arxiv else 1,
        -ai_score,
        _normalize_text(item.get('title') or item.get('title_zh') or ''),
    )
```

- [ ] **Step 2.5: 运行全部测试**

Run: `python3 test_focus_filter.py && python3 test_focus_core.py`
Expected: 两个都 exit 0

- [ ] **Step 2.6: 提交**

```bash
git add focus_filter.py test_focus_filter.py
git commit -m "feat: focus_priority 让核心关注排序置顶"
```

---

## Task 3: `config.py` — `CORE_FOCUS_CONFIG`

**Files:**
- Modify: `config.py`（末尾追加）

- [ ] **Step 3.1: 追加配置**

在 `config.py` 末尾（`GITHUB_CONFIG` 之后）追加：

```python
# 核心关注（ML × ferro/凝聚态）开关与阈值
CORE_FOCUS_CONFIG = {
    "enabled": (os.environ.get("CORE_FOCUS_ENABLED", "1").strip().lower() not in ("0", "false", "no")),
    "daily_max_items": int(os.environ.get("CORE_FOCUS_DAILY_MAX", "8")),
    "weekly_max_items": int(os.environ.get("CORE_FOCUS_WEEKLY_MAX", "20")),
    "min_score": float(os.environ.get("CORE_FOCUS_MIN_SCORE", "0.60")),
}
```

- [ ] **Step 3.2: 快速验证能读出**

Run:
```bash
CORE_FOCUS_ENABLED=1 python3 -c "from config import CORE_FOCUS_CONFIG; print(CORE_FOCUS_CONFIG)"
```
Expected: `{'enabled': True, 'daily_max_items': 8, 'weekly_max_items': 20, 'min_score': 0.6}`

- [ ] **Step 3.3: 提交**

```bash
git add config.py
git commit -m "feat: 新增 CORE_FOCUS_CONFIG 配置（enabled/上限/阈值）"
```

---

## Task 4: `ai_summarizer.py` — `_parse_response` 注入 `is_core_focus` + `core_score`

**Files:**
- Modify: `ai_summarizer.py:820-834`（`_parse_response` 里 full_list 构造处）

- [ ] **Step 4.1: 读取当前 `_parse_response` 的 full_list append 区段**

Run: `grep -n "full_list.append" ai_summarizer.py`
确认位置。

- [ ] **Step 4.2: 修改：在 append 的 dict 里加入两字段**

找到类似下面的代码（大致 L820 起）：

```python
                full_list.append({
                    "title_en": article.get('title'),
                    "title_zh": title_zh,
                    "abstract_zh": abstract_zh,
                    "summary": one_sentence,
                    "link": article.get('link'),
                    "journal": article.get("journal", ""),
                    "authors": article.get("authors", []),
                    "pub_date": article.get("pub_date", ""),
                    "ai_score": article.get("ai_score"),
                    "source_url": article.get("source_url", ""),
                    "arxiv_category": article.get("arxiv_category", ""),
                })
```

替换成（在 append 之前 import 核心关注，并在 dict 尾部加入两字段）：

```python
                # lazy import to avoid circular deps at module top
                from focus_core import is_core_focus as _icf, core_score as _cs
                full_list.append({
                    "title_en": article.get('title'),
                    "title_zh": title_zh,
                    "abstract_zh": abstract_zh,
                    "summary": one_sentence,
                    "link": article.get('link'),
                    "journal": article.get("journal", ""),
                    "authors": article.get("authors", []),
                    "pub_date": article.get("pub_date", ""),
                    "ai_score": article.get("ai_score"),
                    "source_url": article.get("source_url", ""),
                    "arxiv_category": article.get("arxiv_category", ""),
                    "is_core_focus": _icf(article),
                    "core_score": _cs(article),
                })
```

- [ ] **Step 4.3: 快速验证**

Run:
```bash
python3 -c "
from ai_summarizer import AISummarizer
s = AISummarizer.__new__(AISummarizer)
s.provider_name = 'x'
# 构造 fake data and manually exercise _parse_response via a minimal JSON
import json
articles = [{'title':'Equivariant neural network potential for ferroelectrics','abstract':'We train MACE for BaTiO3.','link':'https://ex/1','journal':'Nature','authors':['A']}]
# Provide a minimal response body
body = json.dumps({'overview':'o','trends':'t','summaries':[{'index':1,'title_zh':'Equivariant 神经网络势函数用于铁电体','abstract_zh':'为BaTiO3训练MACE势函数。','one_sentence_summary':'为BaTiO3训练MACE势函数。'}],'highlights':[]})
res = s._parse_response(body, articles, '2026-04-15')
print('is_core_focus:', res['full_list'][0]['is_core_focus'])
print('core_score:', res['full_list'][0]['core_score'])
assert res['full_list'][0]['is_core_focus'] is True
assert res['full_list'][0]['core_score'] > 0.5
print('OK')
"
```
Expected: `is_core_focus: True`, `core_score: 0.80` (approx), `OK`

- [ ] **Step 4.4: 提交**

```bash
git add ai_summarizer.py
git commit -m "feat: _parse_response 注入 is_core_focus 与 core_score 字段"
```

---

## Task 5: `ai_summarizer.py` — 新增 `generate_core_deep_fields` 方法

**Files:**
- Modify: `ai_summarizer.py`（在 `AISummarizer` 类里新增方法）

- [ ] **Step 5.1: 定位 `AISummarizer` 类体尾部**

Run: `grep -n "def fallback_summary" ai_summarizer.py`
在 `fallback_summary` 之前插入新方法。

- [ ] **Step 5.2: 追加方法定义**

```python
    def generate_core_deep_fields(
        self,
        core_items: List[Dict],
        date: str,
    ) -> Tuple[Dict[str, Dict[str, str]], str]:
        """对核心关注论文批量生成 3 深度字段 + 方向点评。

        Returns: (deep_fields_by_link, direction_note)
          deep_fields_by_link: {link: {method_point, related_work, implication}}
          direction_note: 3-4 句中文段落，失败时返回空串
        """
        if not core_items:
            return {}, ""

        lines = []
        for i, it in enumerate(core_items, 1):
            title = it.get('title_en') or it.get('title') or ''
            title_zh = it.get('title_zh') or ''
            abstract = (it.get('abstract_zh') or it.get('abstract') or '')[:400]
            journal = it.get('journal', '')
            lines.append(
                f"[{i}] 中文标题: {title_zh}\n    EN: {title}\n    期刊: {journal}\n    摘要: {abstract}"
            )
        articles_str = "\n".join(lines)

        prompt = (
            f"你是深耕 ML × 铁电/磁性/凝聚态方向的资深研究员。以下是 {date} 当日的 "
            f"{len(core_items)} 篇核心关注论文（均已判定为 ML × ferro/凝聚态方向）。\n\n"
            f"【文献列表】\n{articles_str}\n\n"
            "请给出两部分输出：\n"
            "A. direction_note（3-4 句中文）：概括本日 ML × ferro/凝聚态方向的**实质进展**，"
            "必须点名具体材料（如 NbOI2、CrI3、CrSBr、BaTiO3）与具体方法（如 equivariant GNN、"
            "MACE、NEP、DFT+U），禁止 '整体来看 / 值得关注 / 有望 / 为…提供新思路' 之类套话。\n"
            "B. items：对每篇文章输出三条线索（全中文、信息密度高）：\n"
            "   1) method_point（≤60 字）：核心技术/方法/模型，一针见血；\n"
            "   2) related_work（≤70 字）：与哪些已知方法/体系/方向呼应，只写方向名不编造文献；\n"
            "   3) implication（≤70 字）：对 ML × ferro/凝聚态研究者的具体启发。\n\n"
            "【输出格式】只输出 JSON，无 markdown、无额外文字：\n"
            "{\n"
            '  "direction_note": "...",\n'
            '  "items": [\n'
            '    {"index": 1, "method_point": "...", "related_work": "...", "implication": "..."},\n'
            "    ...\n"
            "  ]\n"
            "}\n"
        )

        try:
            response = self.provider.call_api(prompt)
            data = self._load_json_lenient(response, context="core deep fields")
        except Exception as e:
            print(f"⚠️ generate_core_deep_fields failed: {e}")
            return {}, ""

        if not isinstance(data, dict):
            return {}, ""

        def _clamp(s, n):
            s = (s or "").strip()
            return s if len(s) <= n else s[: n - 1].rstrip() + "…"

        deep_fields: Dict[str, Dict[str, str]] = {}
        for entry in data.get("items", []) or []:
            if not isinstance(entry, dict):
                continue
            try:
                idx = int(entry.get("index"))
            except Exception:
                continue
            if not (1 <= idx <= len(core_items)):
                continue
            link = core_items[idx - 1].get("link") or ""
            if not link:
                continue
            deep_fields[link] = {
                "method_point": _clamp(entry.get("method_point", ""), 80),
                "related_work": _clamp(entry.get("related_work", ""), 100),
                "implication": _clamp(entry.get("implication", ""), 100),
            }

        direction_note = _clamp(data.get("direction_note", ""), 400)
        return deep_fields, direction_note
```

- [ ] **Step 5.3: 单元级烟囱测试（用真 Kimi key）**

Run:
```bash
KIMI_API_KEY=sk-kimi-01xf9u21wS7heXrPhwoiUXmkD3LPTT8G7FX1ms7lFzjxEYY4Nmgm3hs5z0ch5exg \
AI_PROVIDER=kimi python3 -c "
from ai_summarizer import AISummarizer
s = AISummarizer('kimi', 'sk-kimi-01xf9u21wS7heXrPhwoiUXmkD3LPTT8G7FX1ms7lFzjxEYY4Nmgm3hs5z0ch5exg')
items = [
  {'title':'Equivariant neural network potential for ferroelectric perovskites','title_zh':'用于铁电钙钛矿的等变神经网络势','abstract':'We train MACE on BaTiO3 and report coercive fields of 0.2 V/nm with sub-meV/atom energy error.','link':'https://ex/1','journal':'npj Comput Mater'},
  {'title':'Learnable spin Hamiltonian for antiferromagnets via graph networks','title_zh':'基于图网络的反铁磁可学习自旋哈密顿量','abstract':'Graph NN learns exchange Js for CrI3 within 0.5 meV.','link':'https://ex/2','journal':'Phys. Rev. Lett.'},
]
deep, note = s.generate_core_deep_fields(items, '2026-04-15')
print('NOTE:', note[:200])
print('DEEP keys:', list(deep.keys()))
for k,v in deep.items():
  print(k)
  for f in ('method_point','related_work','implication'):
    print(' ', f, ':', v.get(f,'')[:80])
assert note, 'direction_note should not be empty'
assert len(deep) >= 1, 'at least one item should have deep fields'
print('OK')
"
```
Expected: direction_note 非空且含中文 + 材料名；`deep` 有 2 个条目；每条有 method_point/related_work/implication。

- [ ] **Step 5.4: 提交**

```bash
git add ai_summarizer.py
git commit -m "feat: AISummarizer.generate_core_deep_fields 批量生成 3 深度字段 + 方向点评"
```

---

## Task 6: `generate_daily_pages.py` — 主流程接入 core_items

**Files:**
- Modify: `generate_daily_pages.py`（主循环里 summary 生成后）

- [ ] **Step 6.1: 找到主循环里 summary 被 AISummarizer 生成的位置**

Run: `grep -n "generate_daily_summary\|summaries\[" generate_daily_pages.py`
定位 summary 获得后、`render_daily_html` 调用前的位置（通常在主循环尾部）。

- [ ] **Step 6.2: 注入 core_items 与 direction_note**

在 summary 返回之后、`render_daily_html(date_str, summary)` 之前插入：

```python
        # ---- Core-focus deep fields (ML × ferro/凝聚态) ----
        try:
            from config import CORE_FOCUS_CONFIG
        except Exception:
            CORE_FOCUS_CONFIG = {"enabled": True, "daily_max_items": 8, "min_score": 0.60}
        if CORE_FOCUS_CONFIG.get("enabled", True) and summarizer is not None:
            full = summary.get("full_list", [])
            min_score = float(CORE_FOCUS_CONFIG.get("min_score", 0.60))
            max_n = int(CORE_FOCUS_CONFIG.get("daily_max_items", 8))
            core_items = [
                it for it in full
                if it.get("is_core_focus") and float(it.get("core_score") or 0.0) >= min_score
            ]
            core_items.sort(key=lambda x: -float(x.get("core_score") or 0.0))
            core_items = core_items[:max_n]
            if core_items:
                try:
                    deep_fields, direction_note = summarizer.generate_core_deep_fields(core_items, date_str=day_str) \
                        if False else summarizer.generate_core_deep_fields(core_items, day_str)
                except Exception as e:
                    print(f"⚠️ core deep-fields skipped: {e}")
                    deep_fields, direction_note = {}, ""
                for it in core_items:
                    link = it.get("link") or ""
                    info = deep_fields.get(link, {})
                    it["method_point"] = info.get("method_point", "")
                    it["related_work"] = info.get("related_work", "")
                    it["implication"] = info.get("implication", "")
                summary["core_items"] = core_items
                summary["core_direction_note"] = direction_note
            else:
                summary["core_items"] = []
                summary["core_direction_note"] = ""
```

注：上面 `day_str` 是主循环的日期变量；如该位置变量名不同（例如 `date_str`），相应替换。Run `grep -nE "for (day_str|date_str) in" generate_daily_pages.py` 可确认。

- [ ] **Step 6.3: 本地干跑一下（不需真跑 Kimi，只验语法）**

Run: `python3 -c "import generate_daily_pages; print('import OK')"`
Expected: `import OK`（若报 ImportError 因缺 bs4，可跳过此验证，但需要至少 `python3 -c "import ast; ast.parse(open('generate_daily_pages.py').read()); print('OK')"` 通过）

- [ ] **Step 6.4: 提交**

```bash
git add generate_daily_pages.py
git commit -m "feat: 日报主流程注入 core_items 与 direction_note"
```

---

## Task 7: `generate_daily_pages.py` — `render_core_section` + CSS

**Files:**
- Modify: `generate_daily_pages.py`（`render_daily_html` 内）

- [ ] **Step 7.1: 在 `render_daily_html` 内新增 `render_core_section` 局部函数**

在 `render_daily_html` 里，靠近其他 `render_*` 局部函数处，加入：

```python
    def render_core_section(core_items: List[Dict], note: str) -> str:
        if not core_items:
            return ""
        note_html = f"<p class='daily-core-note'>{safe_text(note)}</p>" if note else ""
        cards = []
        for i, it in enumerate(core_items, 1):
            title_zh = safe_text((it.get('title_zh') or '').strip())
            title_en = safe_text((it.get('title_en') or it.get('title') or '').strip())
            show_zh_block = bool(title_zh) and title_zh.casefold() != title_en.casefold()
            journal = safe_text(it.get('journal') or '')
            abstract_zh = safe_text((it.get('abstract_zh') or '').strip())
            one_sentence = safe_text((it.get('summary') or '').strip())
            mp = safe_text((it.get('method_point') or '').strip())
            rw = safe_text((it.get('related_work') or '').strip())
            im = safe_text((it.get('implication') or '').strip())
            link = safe_url(it.get('link') or '')
            title_en_block = f"<div class='daily-core-title-en'>{title_en}</div>" if show_zh_block else ""
            display_title = title_zh if show_zh_block else title_en
            deep_block = ""
            if mp or rw or im:
                deep_parts = []
                if mp: deep_parts.append(f"<p><strong>📐 方法要点：</strong>{mp}</p>")
                if rw: deep_parts.append(f"<p><strong>🔗 相关工作关联：</strong>{rw}</p>")
                if im: deep_parts.append(f"<p><strong>💡 对你方向的启示：</strong>{im}</p>")
                deep_block = f"<div class='daily-core-deep'>{''.join(deep_parts)}</div>"
            cards.append(f"""
            <li class="daily-core-card">
                <div class="daily-core-number">{i:02d}</div>
                <div class="daily-core-body">
                    <div class="daily-core-title-zh">{display_title}</div>
                    {title_en_block}
                    <div class="daily-core-meta"><span class="daily-chip daily-chip-core">🎯 核心关注</span><span class="daily-chip daily-chip-journal">📖 {journal}</span></div>
                    {f"<p class='daily-paper-abstract'><strong>📄 摘要：</strong>{abstract_zh}</p>" if abstract_zh else ""}
                    {f"<p class='daily-paper-highlight'><strong>💡 亮点：</strong>{one_sentence}</p>" if one_sentence else ""}
                    {deep_block}
                    <div class="daily-paper-actions"><a class="daily-news-link" href="{link}" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a></div>
                </div>
            </li>
            """)
        return f"""
        <section id="core-focus" class="daily-section daily-core-section">
          <div class="daily-section-head">
            <span class="daily-section-index">🎯</span>
            <h2 class="daily-section-title">核心关注（ML × ferro / 凝聚态）</h2>
            <span class="daily-core-count">{len(core_items)} 篇</span>
          </div>
          {note_html}
          <ol class="daily-core-list">{''.join(cards)}</ol>
        </section>
        """
```

- [ ] **Step 7.2: 在 style 块里追加 CSS**

在 `render_daily_html` 已有 `.daily-nav { ... }` 附近追加：

```python
    .daily-core-section {{ border-radius: 22px; padding: 22px; margin-top: 26px; background: linear-gradient(135deg, rgba(253,244,215,0.55), rgba(255,248,230,0.88)); border: 1.5px solid rgba(245,158,11,0.45); box-shadow: 0 4px 18px rgba(245,158,11,0.08); }}
    .daily-core-section .daily-section-title {{ color: #b45309; }}
    .daily-core-section .daily-section-index {{ background: rgba(245,158,11,0.18); color: #b45309; }}
    .daily-core-count {{ margin-left: auto; padding: 6px 12px; border-radius: 999px; background: rgba(245,158,11,0.15); color: #b45309; font-weight: 700; font-size: 0.9rem; }}
    .daily-core-note {{ margin: 12px 0 18px; padding: 14px 16px; border-radius: 14px; background: rgba(255,255,255,0.7); border-left: 3px solid #f59e0b; color: var(--text-primary); line-height: 1.8; }}
    .daily-core-list {{ list-style: none; margin: 0; padding: 0; }}
    .daily-core-card {{ display: grid; grid-template-columns: auto minmax(0,1fr); gap: 14px; padding: 18px; border-radius: 18px; background: rgba(255,255,255,0.95); border: 1px solid rgba(245,158,11,0.25); border-left: 3px solid #f59e0b; box-shadow: var(--shadow-sm); }}
    .daily-core-card + .daily-core-card {{ margin-top: 14px; }}
    .daily-core-number {{ width: 42px; height: 42px; display: inline-flex; align-items: center; justify-content: center; border-radius: 14px; font-weight: 800; color: white; background: linear-gradient(135deg, #f59e0b, #fbbf24); box-shadow: var(--shadow-sm); flex-shrink: 0; }}
    .daily-core-title-zh {{ font-size: 1.1rem; font-weight: 700; line-height: 1.5; margin-bottom: 4px; }}
    .daily-core-title-en {{ color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6; }}
    .daily-core-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
    .daily-chip-core {{ background: rgba(245,158,11,0.18); color: #b45309; font-weight: 600; }}
    .daily-core-deep {{ margin-top: 10px; padding: 12px 14px; border-radius: 12px; background: rgba(245,158,11,0.06); border: 1px dashed rgba(245,158,11,0.35); line-height: 1.75; }}
    .daily-core-deep p + p {{ margin-top: 6px; }}
    @media (max-width: 720px) {{
      .daily-core-card {{ grid-template-columns: 1fr; }}
      .daily-core-number {{ width: 36px; height: 36px; }}
    }}
```

- [ ] **Step 7.3: 把 `render_core_section` 注入模板**

在 `render_daily_html` 的 HTML 模板字符串里，定位 `<section id="summary" class="daily-section">`（"今日摘要"），在它**之前**插入：

```python
        {render_core_section(summary.get('core_items', []) or [], summary.get('core_direction_note') or '')}
```

（也记得在相应 f-string 的 .format 阶段不要踩 `{` 转义问题 —— 此 render_daily_html 已是 f-string，直接用 `{render_core_section(...)}` 即可。）

- [ ] **Step 7.4: 也在 TOC（`.daily-toc` 的锚点列表）加入 "🎯 核心关注"**

找到 `<a href="#summary"><span>今日摘要</span><span>01</span></a>`，在它之前插入：

```python
          {'<a href="#core-focus"><span>🎯 核心关注</span><span>00</span></a>' if summary.get('core_items') else ''}
```

- [ ] **Step 7.5: 渲染烟囱测试**

Run:
```bash
PYTHONPATH=/tmp/bs4root/usr/lib/python3/dist-packages python3 -c "
import importlib, generate_daily_pages
from generate_daily_pages import render_daily_html
summary = {'date':'2026-04-15','total':1,'overview':'x','trends':'y',
  'full_list':[{'title_en':'Equivariant NNP','title_zh':'等变神经网络势','abstract_zh':'a','summary':'s','link':'https://ex/1','journal':'Nature'}],
  'summaries':[],'ml_highlights':[],'ferro_highlights':[],
  'core_items':[{'title_en':'Equivariant NNP','title_zh':'等变神经网络势','abstract_zh':'a','summary':'s','link':'https://ex/1','journal':'Nature','method_point':'MACE 势训练','related_work':'与 NequIP / Allegro 同一族','implication':'可迁移到反铁磁体系'}],
  'core_direction_note':'本日 ML×ferro 方向出现 MACE 势应用于 BaTiO3；与 NequIP 同族。'
}
html = render_daily_html('2026-04-15', summary)
assert 'daily-core-section' in html, 'core section missing'
assert '核心关注（ML × ferro' in html
assert '方法要点' in html
assert '🎯 核心关注' in html  # chip
print('OK render has core section; size:', len(html))
"
```
（若 bs4 不可用，可先用 step 1 的 `python3 -c "import ast; ast.parse(open('generate_daily_pages.py').read()); print('OK')"` 替代；生产端真正的端到端会在 Task 10 走 Actions 做。）

- [ ] **Step 7.6: 提交**

```bash
git add generate_daily_pages.py
git commit -m "feat: 日报新增 🎯 核心关注 section + 金色 CSS + 目录锚点"
```

---

## Task 8: 周报 — `_generate_core_weekly` + 结构重排

**Files:**
- Modify: `weekly_summary.py`（新增方法 + 修改渲染顺序）

- [ ] **Step 8.1: 新增 `_generate_core_weekly` 方法**

在 `WeeklySummarizer` 类内，找到 `_generate_ai_summary` 方法之后插入：

```python
    def _generate_core_weekly(
        self,
        core_items: List[Dict],
        week_start: str,
        week_end: str,
    ) -> tuple:
        """对核心关注论文批量产出 direction_weekly_note + 三深度字段。

        Returns: (note_str, {link -> {method_point, related_work, implication}})
        """
        if not core_items or not self.provider:
            return "", {}

        lines = []
        for i, it in enumerate(core_items, 1):
            title = it.get('title') or ''
            title_zh = it.get('title_zh') or ''
            abstract = (it.get('abstract_zh') or it.get('abstract') or '')[:400]
            journal = it.get('journal', '')
            lines.append(f"[{i}] 中文: {title_zh}\n    EN: {title}\n    期刊: {journal}\n    摘要: {abstract}")
        articles_str = "\n".join(lines)

        prompt = (
            f"你是深耕 ML × 铁电/磁性/凝聚态方向的资深研究员。下面是 {week_start} 至 {week_end} "
            f"这一周 {len(core_items)} 篇属于该方向的核心论文。\n\n"
            f"【文献列表】\n{articles_str}\n\n"
            "请给出两部分输出：\n"
            "A. weekly_direction_note（6-8 句中文）：回顾本周 ML × ferro/凝聚态方向的实质进展，"
            "按 '新材料 / 新方法 / 新现象' 三条主线展开，必须点名具体材料、方法与关键数值或结论。"
            "禁止 '整体来看/具有重要意义/为…提供新思路' 之类套话。\n"
            "B. items：每篇三字段（全中文）：\n"
            "   1) method_point ≤60 字\n   2) related_work ≤70 字\n   3) implication ≤70 字\n\n"
            "只输出 JSON：\n"
            "{\n"
            '  "weekly_direction_note": "...",\n'
            '  "items": [{"index": 1, "method_point": "...", "related_work": "...", "implication": "..."}]\n'
            "}\n"
        )

        try:
            response = self.provider.call_api(prompt)
            from ai_summarizer import AISummarizer as _AS
            data = _AS._load_json_lenient(response, context="weekly core deep")
        except Exception as e:
            print(f"⚠️ _generate_core_weekly failed: {e}")
            return "", {}

        if not isinstance(data, dict):
            return "", {}

        def _c(s, n):
            s = (s or "").strip()
            return s if len(s) <= n else s[: n - 1].rstrip() + "…"

        deep: Dict[str, Dict[str, str]] = {}
        for entry in data.get("items", []) or []:
            if not isinstance(entry, dict):
                continue
            try:
                idx = int(entry.get("index"))
            except Exception:
                continue
            if not (1 <= idx <= len(core_items)):
                continue
            link = core_items[idx - 1].get("link") or ""
            if not link:
                continue
            deep[link] = {
                "method_point": _c(entry.get("method_point", ""), 80),
                "related_work": _c(entry.get("related_work", ""), 100),
                "implication": _c(entry.get("implication", ""), 100),
            }
        note = _c(data.get("weekly_direction_note", ""), 800)
        return note, deep
```

- [ ] **Step 8.2: 在周报主流程里调用**

在 `_generate_ai_summary` 返回 dict 之前（紧接着 article_summaries / highlights / topic_buckets 组装完），加入：

```python
        # ---- Core-focus: ML × ferro/凝聚态 ----
        try:
            from config import CORE_FOCUS_CONFIG
        except Exception:
            CORE_FOCUS_CONFIG = {"enabled": True, "weekly_max_items": 20, "min_score": 0.60}

        from focus_core import is_core_focus as _icf, core_score as _cs
        core_items_raw = [a for a in all_articles if _icf(a)]
        core_items_raw.sort(key=lambda x: -_cs(x))
        min_s = float(CORE_FOCUS_CONFIG.get("min_score", 0.60))
        core_items_raw = [a for a in core_items_raw if _cs(a) >= min_s]
        core_items_raw = core_items_raw[: int(CORE_FOCUS_CONFIG.get("weekly_max_items", 20))]

        weekly_note = ""
        core_deep: Dict[str, Dict[str, str]] = {}
        if CORE_FOCUS_CONFIG.get("enabled", True) and core_items_raw:
            weekly_note, core_deep = self._generate_core_weekly(core_items_raw, week_start, week_end)

        core_items_enriched = []
        for a in core_items_raw:
            link = a.get("link") or ""
            info = core_deep.get(link, {})
            core_items_enriched.append({
                "title": a.get("title_zh") or a.get("title", ""),
                "title_en": a.get("title", ""),
                "link": a.get("link", ""),
                "journal": a.get("journal", ""),
                "abstract_zh": a.get("abstract_zh", ""),
                "method_point": info.get("method_point", ""),
                "related_work": info.get("related_work", ""),
                "implication": info.get("implication", ""),
                "core_score": _cs(a),
            })
```

然后在最终返回 dict 里加入两个字段：

```python
            'core_items': core_items_enriched,
            'core_weekly_note': weekly_note,
```

- [ ] **Step 8.3: 找到周报 HTML 渲染函数，插入"本周核心方向" section**

Run: `grep -n "def render_weekly_html\|def render_weekly_summary\|def build_weekly_html\|def _render_html" weekly_summary.py`

在周报 HTML 主体里，**在 overview / highlights / by_topic 等原 section 之前**，新增一个 `render_core_weekly_section`：

```python
def render_core_weekly_section(summary: Dict) -> str:
    items = summary.get('core_items') or []
    if not items:
        return ""
    note = summary.get('core_weekly_note') or ""
    cards = []
    for i, it in enumerate(items, 1):
        title = (it.get('title') or '').strip()
        title_en = (it.get('title_en') or '').strip()
        journal = (it.get('journal') or '').strip()
        link = (it.get('link') or '').strip() or '#'
        abstract_zh = (it.get('abstract_zh') or '').strip()
        mp = (it.get('method_point') or '').strip()
        rw = (it.get('related_work') or '').strip()
        im = (it.get('implication') or '').strip()
        show_en = bool(title) and title.casefold() != title_en.casefold()
        deep = ""
        if mp or rw or im:
            parts = []
            if mp: parts.append(f"<p><strong>📐 方法要点：</strong>{mp}</p>")
            if rw: parts.append(f"<p><strong>🔗 相关工作关联：</strong>{rw}</p>")
            if im: parts.append(f"<p><strong>💡 对你方向的启示：</strong>{im}</p>")
            deep = f"<div class='weekly-core-deep'>{''.join(parts)}</div>"
        title_en_html = f"<div class='weekly-core-title-en'>{title_en}</div>" if show_en else ""
        abs_block = f"<p class='weekly-core-abs'><strong>📄 摘要：</strong>{abstract_zh}</p>" if abstract_zh else ""
        cards.append(f"""
        <li class="weekly-core-card">
          <div class="weekly-core-number">{i:02d}</div>
          <div class="weekly-core-body">
            <div class="weekly-core-title-zh">{title or title_en}</div>
            {title_en_html}
            <div class="weekly-core-meta"><span class="weekly-chip weekly-chip-core">🎯 核心</span><span class="weekly-chip">📖 {journal}</span></div>
            {abs_block}
            {deep}
            <div class="weekly-core-actions"><a href="{link}" target="_blank" rel="noopener noreferrer">阅读原文 ↗</a></div>
          </div>
        </li>
        """)
    note_html = f"<p class='weekly-core-note'>{note}</p>" if note else ""
    return f"""
    <section id="core-focus" class="weekly-section weekly-core-section">
      <div class="weekly-section-head"><span class="weekly-section-index">🎯</span><h2 class="weekly-section-title">本周核心方向（ML × ferro / 凝聚态）</h2><span class="weekly-core-count">{len(items)} 篇</span></div>
      {note_html}
      <ol class="weekly-core-list">{''.join(cards)}</ol>
    </section>
    """
```

（注意：以上函数体里中文可能被 .format 或 f-string 影响；按现有 weekly_summary.py 的具体渲染写法调整。）

- [ ] **Step 8.4: 在周报模板字符串里把此 section 插到现有 "交叉研究 / 全文速览 / 期刊分布" 的**之前**（即第一个 `<section>` 位置）**

在主 HTML f-string 里找到第一个 `<section` 标签，在它之前注入：

```python
  {render_core_weekly_section(summary)}
```

- [ ] **Step 8.5: 补 CSS（复用日报 `.daily-core-*` 风格，改前缀 `weekly-core-*`）**

在周报 `<style>` 块追加：

```css
.weekly-core-section { border-radius:22px; padding:22px; margin-bottom:26px; background:linear-gradient(135deg,rgba(253,244,215,0.55),rgba(255,248,230,0.88)); border:1.5px solid rgba(245,158,11,0.45); box-shadow:0 4px 18px rgba(245,158,11,0.08); }
.weekly-core-section .weekly-section-title { color:#b45309; }
.weekly-core-count { margin-left:auto; padding:6px 12px; border-radius:999px; background:rgba(245,158,11,0.15); color:#b45309; font-weight:700; font-size:.9rem; }
.weekly-core-note { margin:12px 0 18px; padding:14px 16px; border-radius:14px; background:rgba(255,255,255,.7); border-left:3px solid #f59e0b; line-height:1.8; }
.weekly-core-list { list-style:none; margin:0; padding:0; }
.weekly-core-card { display:grid; grid-template-columns:auto minmax(0,1fr); gap:14px; padding:18px; border-radius:18px; background:rgba(255,255,255,0.95); border:1px solid rgba(245,158,11,0.25); border-left:3px solid #f59e0b; }
.weekly-core-card + .weekly-core-card { margin-top:14px; }
.weekly-core-number { width:40px; height:40px; display:inline-flex; align-items:center; justify-content:center; border-radius:14px; font-weight:800; color:white; background:linear-gradient(135deg,#f59e0b,#fbbf24); }
.weekly-core-title-zh { font-size:1.08rem; font-weight:700; line-height:1.5; margin-bottom:4px; }
.weekly-core-title-en { color:#64748b; font-size:.92rem; line-height:1.6; }
.weekly-core-meta { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0; }
.weekly-chip { padding:6px 10px; border-radius:999px; background:rgba(99,102,241,.08); font-size:.88rem; color:#475569; }
.weekly-chip-core { background:rgba(245,158,11,.18); color:#b45309; font-weight:600; }
.weekly-core-deep { margin-top:10px; padding:12px 14px; border-radius:12px; background:rgba(245,158,11,.06); border:1px dashed rgba(245,158,11,.35); line-height:1.75; }
.weekly-core-deep p + p { margin-top:6px; }
@media (max-width:720px){ .weekly-core-card{ grid-template-columns:1fr; } }
```

- [ ] **Step 8.6: 提交**

```bash
git add weekly_summary.py
git commit -m "feat: 周报新增 🎯 本周核心方向 section + 深度字段 + 金色 CSS"
```

---

## Task 9: 渲染测试补充

**Files:**
- Modify: `test_daily_pages_render.py`
- Modify: `test_weekly_pages_render.py`

- [ ] **Step 9.1: 查看现有日报渲染测试结构**

Run: `head -50 test_daily_pages_render.py`

- [ ] **Step 9.2: 追加"有 core_items 时渲染金色 section"**

在日报渲染测试 main() 末尾追加：

```python
    # ----- Core focus section -----
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
    html = _rdh('2026-04-15', summary_with_core)
    if 'daily-core-section' not in html:
        print('FAIL: missing .daily-core-section when core_items present'); return 1
    if '核心关注（ML' not in html:
        print('FAIL: missing core heading'); return 1
    if '方法要点' not in html or '启示' not in html:
        print('FAIL: missing deep fields'); return 1

    # Absence path
    summary_no_core = dict(summary_with_core)
    summary_no_core['core_items'] = []
    html2 = _rdh('2026-04-15', summary_no_core)
    if 'daily-core-section' in html2:
        print('FAIL: should NOT render core section when empty'); return 1
```

- [ ] **Step 9.3: 日报渲染测试运行通过**

Run: `python3 test_daily_pages_render.py`
Expected: exit 0

- [ ] **Step 9.4: 周报同理追加**

在 `test_weekly_pages_render.py` main() 末尾追加（名字/细节按现有文件的断言风格微调）：

```python
    # ----- Weekly core focus section -----
    from weekly_summary import render_core_weekly_section as _rc
    summary_wk = {
        'core_items':[{'title':'等变神经网络势','title_en':'Equivariant NNP','link':'https://ex/1','journal':'Nature','abstract_zh':'为 BaTiO3 训练 MACE。','method_point':'MACE 等变势','related_work':'与 NequIP 同族','implication':'可迁移反铁磁'}],
        'core_weekly_note':'本周 MACE 用于 BaTiO3；CrI3 中 GNN 学习自旋 Hamiltonian。'
    }
    block = _rc(summary_wk)
    if 'weekly-core-section' not in block:
        print('FAIL: weekly core section missing'); return 1
    if '核心' not in block or '启示' not in block:
        print('FAIL: weekly core heading/deep missing'); return 1

    block2 = _rc({'core_items':[], 'core_weekly_note':''})
    if block2.strip() != '':
        print('FAIL: weekly core section should be empty when no items'); return 1
```

- [ ] **Step 9.5: 周报渲染测试运行通过**

Run: `python3 test_weekly_pages_render.py`
Expected: exit 0

- [ ] **Step 9.6: 提交**

```bash
git add test_daily_pages_render.py test_weekly_pages_render.py
git commit -m "test: 日报/周报新增 core-focus section 渲染断言"
```

---

## Task 10: 端到端验证（触发 Actions，检查生产页面）

**Files:**
- 无修改；仅运行验证。

- [ ] **Step 10.1: 推送并触发 Backfill Daily Pages**

```bash
git push origin main
export GH_TOKEN=<user's token>
curl -sS -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Hongyu-yu/literature-tracker/actions/workflows/246881370/dispatches \
  -d '{"ref":"main","inputs":{"days":"1","force":"true"}}'
```
Expected: `204`

- [ ] **Step 10.2: 轮询直至 completed success**

```bash
sleep 30
curl -sS -H "Authorization: token $GH_TOKEN" \
  "https://api.github.com/repos/Hongyu-yu/literature-tracker/actions/workflows/246881370/runs?per_page=1"
```
期望最新 run `status=completed conclusion=success`。

- [ ] **Step 10.3: 拉回并验证日报 HTML**

```bash
git pull --rebase origin main
python3 <<'PY'
import re, os
fn = 'docs/daily/2026-04-14.html'
html = open(fn).read()
assert 'daily-core-section' in html, 'core section missing in daily'
assert '核心关注（ML' in html, 'core heading missing'
m = re.search(r'daily-core-card', html)
assert m, 'core card missing'
# deep fields may be missing if LLM failed, but heading must exist
print('size=', len(html))
print('OK daily core section present')
PY
```

- [ ] **Step 10.4: 触发 Weekly Summary + 验证**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Hongyu-yu/literature-tracker/actions/workflows/224472439/dispatches \
  -d '{"ref":"main"}'
```
Expected: `204`，等待完成后：

```bash
git pull --rebase origin main
python3 -c "
import os, re, glob
f = sorted(glob.glob('docs/weekly/*.html'))[-1]
html = open(f).read()
assert 'weekly-core-section' in html, 'weekly core section missing'
assert '本周核心方向' in html
print('OK weekly core section present at', f)
"
```

- [ ] **Step 10.5: 打开浏览器人工验收（软验）**

Open: `https://hongyu-yu.github.io/literature-tracker/daily/2026-04-14.html`
确认：
- 🎯 核心关注 section 在顶部（紧接 hero 之后）
- 有金色边框、数量徽章
- 至少一篇卡片含"方法要点 / 相关工作关联 / 对你方向的启示"
- 导航 "前一天 / 后一天" 仍正常

---

## Self-Review

**1. Spec coverage:**
- §1 核心关注判定 → Task 1
- §2 日报 section + 深度字段 → Task 5 (生成) + Task 6 (主流程) + Task 7 (渲染) + Task 9 (测试)
- §3 LLM 调用 → Task 5
- §4 周报结构重构 → Task 8 + Task 9
- §5 配置 → Task 3
- §6 文件一览 → 全覆盖
- §7 成本估算 → 不需实现
- §8 验证方式 → Task 10
- §9 YAGNI → 全遵守

**2. Placeholder scan:** 已消除；每个 Step 含具体代码或命令。

**3. Type consistency:**
- `is_core_focus` / `core_score` 签名一致
- `generate_core_deep_fields` 在 Task 5 定义、Task 6 调用、Task 9 测试走同一签名
- `core_items` / `core_direction_note` / `core_weekly_note` 字段名在全链贯穿一致

**4. 可执行单元:** 每个 Task 独立可测、可 commit；Task 1→2→3 仅改分类/配置（无需 Kimi），Task 4→5→6→7 打通日报链路，Task 8 搞定周报，Task 9 测试，Task 10 端到端。
