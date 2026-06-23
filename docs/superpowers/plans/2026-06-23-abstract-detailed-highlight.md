# 日报/周报每篇增加「摘要中文 + 详细亮点」Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让日报/周报每篇文章都显式展示加长版中文摘要(≤200 字)与一段 2~3 句的详细亮点(≤100 字)。

**Architecture:** 三层改动——(A) AI 生成层把 prompt 字数上限放宽并喂更多原文摘要;(B) 日报主统一列表渲染补上摘要块(核心区已有,直接对齐);(C) 周报详细解读 prompt 同步加长。回填靠现成 workflow,无新代码。

**Tech Stack:** Python 3.11 stdlib-only 本地环境;自定义 `run_tests.py`(顶层 `test_*` 函数)+ 脚本式 `main()` 测试;GitHub Actions 回填。

## Global Constraints

- 本地无 pip/pytest/bs4/Pillow/json_repair;测试用 stdlib;缺依赖的测试在 CI 跑。
- 新增 Python 测试写成**顶层 `test_*` 函数**(被 `run_tests.py` 发现)。
- 改前端资产必须 bump `docs/sw.js` 的 `CACHE_NAME`/`DATA_CACHE_NAME`;SW 预缓存与注册保持**相对路径**(`./`);`test_docs_assets.py` 把关。
- 字段名 `one_sentence_summary`/`summary`/`abstract_zh` **保持不变**,只改写作要求与长度。
- 不动:`data/index.json` 写回链路、`focus_core` 判定与计分、深析正文与信息图、`docs/data` 不入库。
- 截断阈值统一:`abstract_zh` → 240 字符(放行 ≤200 字);`one_sentence_summary` → 120 字符(放行 ≤100 字)。
- 每次提交前跑 `python run_tests.py`,并对改到的脚本式测试单独跑 `python3 test_xxx.py`。

---

### Task 1: AI 日报生成层(prompt 加长 + clamp 放行)

**Files:**
- Modify: `ai_summarizer.py`
  - `_build_prompt()`(L603-666):abstract_zh ≤120→≤200;one_sentence_summary 一句话≤40→一段2~3句≤100;喂入摘要 `[:300]`→`[:600]`(L616);更新 `example_block`(L625-636)与输出格式注释(L656-664)。
  - `_build_missing_summaries_prompt()`(L668-704):喂入摘要 `[:300]`→`[:600]`(L683);文案 "摘要中文翻译(100字以内)"→"摘要中文概括(≤200字)"、"一句话中文总结"→"一段2~3句、≤100字的中文亮点"(L700-701)。
  - `_parse_response()`:one_sentence clamp `80`→`120`(L897 与 L956);abstract_zh 维持 240(L896、L954)。
- Test: `test_ai_summarizer_prompt.py`(Create,顶层 `test_*`,纯字符串断言,无网络/无第三方依赖)

**Interfaces:**
- Consumes: `from ai_summarizer import AISummarizer`;`AISummarizer()` 无参可构造(无 key 时 `self.provider=None`,但 `_build_prompt` 不依赖 provider)。
- Produces: `_build_prompt(articles, date)` 返回的 prompt 字符串包含 "≤200" 与 "2~3" 与 "≤100" 字样;`_clamp_text` 在长输入下保留 ≥100 个中文字符。

- [ ] **Step 1: 写失败测试**

创建 `test_ai_summarizer_prompt.py`:

```python
#!/usr/bin/env python3
"""AI 日报 prompt 字数要求与 clamp 阈值回归(stdlib-only, 无网络)。
确保:摘要 ≤200 字、亮点 2~3 句 ≤100 字的硬性要求写进 prompt;
clamp 阈值放行新长度(否则 AI 写够了也会被截断)。"""
from ai_summarizer import AISummarizer, _clamp_text


_ARTS = [{"title": "Room-temperature ferroelectricity in 2D NbOI2",
          "journal": "arXiv", "authors": ["A", "B"],
          "abstract": "We report robust out-of-plane ferroelectric switching " * 30}]


def test_daily_prompt_requires_longer_abstract_and_highlight():
    prompt = AISummarizer()._build_prompt(_ARTS, "2026-01-01")
    assert "≤200" in prompt, "abstract_zh 应要求 ≤200 字"
    assert "2~3" in prompt, "one_sentence_summary 应要求 2~3 句"
    assert "≤100" in prompt, "亮点应要求 ≤100 字"
    # 旧的过短上限不应再出现在硬性要求里
    assert "≤120 字" not in prompt and "≤40 字" not in prompt


def test_daily_prompt_feeds_more_abstract_source():
    # 喂给 AI 的原文摘要应放宽到 600 字符(否则写不出 200 字概括)
    prompt = AISummarizer()._build_prompt(_ARTS, "2026-01-01")
    # 原始 abstract 很长;放宽后 prompt 中该摘要片段长度应 > 300
    assert _ARTS[0]["abstract"][:301] in prompt or len(_ARTS[0]["abstract"]) > 300 and \
        _ARTS[0]["abstract"][:600][:400] in prompt


def test_clamp_allows_100_chinese_chars_for_highlight():
    long_zh = "创" * 110
    assert len(_clamp_text(long_zh, 120)) >= 100


if __name__ == "__main__":
    for _fn in sorted(k for k in dir() if k.startswith("test_")):
        globals()[_fn](); print(f"✓ {_fn}")
    print("OK")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 test_ai_summarizer_prompt.py`
Expected: FAIL(当前 prompt 含 "≤120 字"/"≤40 字",且喂入只 `[:300]`)

- [ ] **Step 3: 改 `_build_prompt` 写作要求(L646-648)**

把 L646-648 三条改为:

```python
            "2. abstract_zh：用中文把摘要写成 ≤200 字的研究要点概括，必须写出：体系/方法/关键数值或结论，"
            "尽量多覆盖。禁止任何套话：'本研究/取得进展/具有重要意义/为…提供新思路/点击查看' 等一律不允许。\n"
            "3. one_sentence_summary：一段 2~3 句、≤100 字的中文亮点：核心创新点 + 最强结论 + 对凝聚态/"
            "AI for science 方向的意义。要落到具体材料/现象/方法，不得空泛。\n"
```

- [ ] **Step 4: 放宽喂入摘要长度(L616)**

```python
            abstract = (article.get('abstract', ''))[:600]
```

- [ ] **Step 5: 更新 example_block(L632-634)**

把示例里的 abstract_zh / one_sentence_summary 改成更长样例:

```python
            '  "abstract_zh": "在二维 NbOI2 薄层中观测到稳定的面外铁电翻转，矫顽场约 0.3 V/nm，"\n'
            '                "室温保持时间 > 10^4 s；通过二次谐波与压电力显微镜确认极化方向，"\n'
            '                "并给出层厚依赖的相变温度，为低维非易失存储提供候选体系。",\n'
            '  "one_sentence_summary": "首次在二维 NbOI2 中实现室温稳定的面外铁电翻转，矫顽场低至 0.3 V/nm。'
            '该体系兼具薄层可集成性与长保持时间，为低功耗非易失存储与可重构光电器件提供了新的二维材料平台。"\n'
```

- [ ] **Step 6: 更新输出格式内联注释(L656-657)**

```python
            '  "overview": "今日文献总览（中文，2-3句，含具体方向与代表性工作）",\n'
            '  "trends": "研究热点分析（中文，3-5句）",\n'
```

(此两行无需改动;确认 `summaries` 行注释不含旧字数;若 L659 示例注释提及字数则一并对齐。)

- [ ] **Step 7: 改 `_build_missing_summaries_prompt`(L683, L700-701)**

L683:

```python
            abstract = (article.get('abstract', ''))[:600]
```

L700-701:

```python
      "abstract_zh": "摘要中文概括（≤200字，写出体系/方法/关键结论）",
      "one_sentence_summary": "一段2~3句、≤100字的中文亮点（创新点+最强结论+方向意义）"
```

- [ ] **Step 8: 放行 clamp(L897, L956)**

L897:

```python
                one_sentence = _clamp_text(ai_info.get('one_sentence_summary') or "", 120)
```

L956:

```python
                        "summary": _clamp_text(info.get('one_sentence_summary') or "", 120),
```

- [ ] **Step 9: 跑测试确认通过**

Run: `python3 test_ai_summarizer_prompt.py`
Expected: PASS(`✓ test_...` ×3 + `OK`)

- [ ] **Step 10: 跑全量套件**

Run: `python run_tests.py`
Expected: 新测试计入 passed;无新增 failed(缺依赖的照常 skip)。

- [ ] **Step 11: 提交**

```bash
git add ai_summarizer.py test_ai_summarizer_prompt.py
git commit -m "feat(ai): 日报摘要≤200字、亮点2~3句≤100字,clamp放行,喂入摘要600字符"
```

---

### Task 2: 日报主统一列表渲染补摘要块

**Files:**
- Modify: `generate_daily_pages.py` → `render_unified_item()`(L492-538)
- Test: `test_daily_pages_render.py`(Modify,新增顶层 `test_*`)

**Interfaces:**
- Consumes: `from generate_daily_pages import render_unified_item`;item 字段 `abstract_zh`/`summary`。
- Produces: 当 `abstract_zh` 非空时,渲染含 `daily-paper-abstract` 与 "📄 摘要"的块;`summary` 仍渲染为 `daily-paper-highlight` "💡 亮点";两块不互相兜底(摘要为空不拿亮点填,亮点为空不拿摘要填)。

- [ ] **Step 1: 写失败测试(追加到 `test_daily_pages_render.py` 末尾)**

```python
def test_render_unified_item_shows_abstract_then_highlight():
    from generate_daily_pages import render_unified_item
    item = {"title": "P", "title_en": "P", "title_zh": "标题",
            "abstract_zh": "该工作在 BaTiO3 中用 MACE 等变势复现相变温度，误差 < 5K。",
            "summary": "首次把等变势用于钙钛矿相变预测，精度接近第一性原理。",
            "link": "http://x", "journal": "arXiv", "_tier": 2, "_enrich": None}
    html = render_unified_item(item, 1)
    assert "daily-paper-abstract" in html and "📄 摘要" in html
    assert "MACE 等变势复现相变温度" in html
    assert "daily-paper-highlight" in html and "💡 亮点" in html
    assert "首次把等变势用于钙钛矿相变预测" in html
    # 摘要块在亮点块之前
    assert html.index("📄 摘要") < html.index("💡 亮点")


def test_render_unified_item_no_abstract_block_when_empty():
    from generate_daily_pages import render_unified_item
    item = {"title": "P", "title_en": "P", "summary": "只有亮点",
            "link": "http://x", "journal": "arXiv", "_tier": 2, "_enrich": None}
    html = render_unified_item(item, 1)
    assert "📄 摘要" not in html           # 无 abstract_zh 不出摘要块
    assert "💡 亮点" in html and "只有亮点" in html
    # 亮点不再被 abstract_zh 兜底污染(此处无 abstract_zh,亮点仍是 summary)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -c "import test_daily_pages_render as t; t.test_render_unified_item_shows_abstract_then_highlight()"`
Expected: FAIL(当前 `render_unified_item` 不渲染 "📄 摘要")

- [ ] **Step 3: 改 `render_unified_item`(L503-506)**

把 L503-506:

```python
    highlight = (item.get("summary") or item.get("abstract_zh")
                 or item.get("one_sentence_summary") or "").strip()
    hl_html = (f'<p class="daily-paper-highlight"><strong>💡 亮点：</strong>{safe_text(highlight)}</p>'
               if highlight else "")
```

改为:

```python
    abstract_zh = (item.get("abstract_zh") or "").strip()
    abs_html = (f'<p class="daily-paper-abstract"><strong>📄 摘要：</strong>{safe_text(abstract_zh)}</p>'
                if abstract_zh else "")
    highlight = (item.get("summary") or item.get("one_sentence_summary") or "").strip()
    hl_html = (f'<p class="daily-paper-highlight"><strong>💡 亮点：</strong>{safe_text(highlight)}</p>'
               if highlight else "")
```

- [ ] **Step 4: 在卡片模板插入摘要块(L532-533)**

把 L532-533:

```python
            <div class="daily-paper-meta">{meta_html}</div>
            {hl_html}
```

改为:

```python
            <div class="daily-paper-meta">{meta_html}</div>
            {abs_html}
            {hl_html}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `python3 -c "import test_daily_pages_render as t; t.test_render_unified_item_shows_abstract_then_highlight(); t.test_render_unified_item_no_abstract_block_when_empty(); print('OK')"`
Expected: `OK`

- [ ] **Step 6: 跑脚本式 main + 全量**

Run: `python3 test_daily_pages_render.py && python run_tests.py`
Expected: `[OK] daily renderer sanity checks passed`;全量无新增 failed。

- [ ] **Step 7: 提交**

```bash
git add generate_daily_pages.py test_daily_pages_render.py
git commit -m "feat(daily): 主列表每篇显式展示中文摘要,亮点与摘要不互相兜底"
```

---

### Task 3: 摘要/亮点样式 + Service Worker 版本

**Files:**
- Modify: `docs/daily-common.css`(在 L62 `.daily-news-summary, .daily-paper-summary` 行后追加)
- Modify: `docs/sw.js`(L15-16 CACHE 版本)
- Test: `test_docs_assets.py`(已存在,跑通即可;新增 1 个顶层 `test_*` 断言 CSS 类存在)

**Interfaces:**
- Consumes: 无。
- Produces: `daily-common.css` 含 `.daily-paper-abstract` 与 `.daily-paper-highlight` 规则;`sw.js` `CACHE_NAME`/`DATA_CACHE_NAME` 升到 `v6`。

- [ ] **Step 1: 写失败测试(追加到 `test_docs_assets.py`)**

```python
def test_daily_common_css_has_abstract_and_highlight():
    css = _read("daily-common.css")
    assert ".daily-paper-abstract" in css, "应为摘要块加样式"
    assert ".daily-paper-highlight" in css, "应为亮点块加样式"
```

(`_read` 已在该文件定义,读取 `docs/<name>`。)

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -c "import test_docs_assets as t; t.test_daily_common_css_has_abstract_and_highlight()"`
Expected: FAIL(`AssertionError: 应为摘要块加样式`)

- [ ] **Step 3: 加 CSS(daily-common.css,在 L62 后插入)**

```css
    .daily-paper-abstract { color: var(--text-primary); line-height: 1.85; margin: 4px 0 8px; }
    .daily-paper-abstract strong { color: var(--accent-primary); }
    .daily-paper-highlight { color: var(--text-secondary); line-height: 1.8; margin: 4px 0; background: rgba(245,158,11,0.08); border-radius: 12px; padding: 10px 14px; }
    .daily-paper-highlight strong { color: #b45309; }
```

- [ ] **Step 4: bump SW 版本(sw.js L15-16)**

```javascript
const CACHE_NAME = 'literature-tracker-v6';
const DATA_CACHE_NAME = 'literature-data-v6';
```

- [ ] **Step 5: 跑资产测试确认通过**

Run: `python3 test_docs_assets.py`
Expected: `✓ test_...`(含新断言)+ `OK`(预缓存仍相对路径且文件存在)

- [ ] **Step 6: 提交**

```bash
git add docs/daily-common.css docs/sw.js test_docs_assets.py
git commit -m "feat(ui): 摘要/亮点块样式 + sw 缓存 bump v6"
```

---

### Task 4: 周报详细解读加长

**Files:**
- Modify: `weekly_summary.py`
  - 抽出纯函数 `_build_analyze_prompt(title, journal, abstract)` 并由 `_analyze_single_article` 调用(L330-356 区域);prompt "50-80字"→"2~3句、≤100字";返回 clamp `[:100]`→`[:130]`(L381)。
  - 普通卡摘要预览长度 `shorten_text(preview_source, 220)`→`240`(L1512),保证 ≤200 字摘要不被截。
- Test: `test_weekly_highlight.py`(Create,顶层 `test_*`,纯字符串,无 provider/无网络)

**Interfaces:**
- Consumes: `from weekly_summary import _build_analyze_prompt`(模块级纯函数)。
- Produces: `_build_analyze_prompt(title, journal, abstract)` 返回 prompt 字符串,含 "2~3" 与 "≤100",且原文摘要按 `[:500]` 喂入。

- [ ] **Step 1: 写失败测试**

创建 `test_weekly_highlight.py`:

```python
#!/usr/bin/env python3
"""周报单篇详细解读 prompt 加长回归(stdlib-only, 无 provider)。"""
from weekly_summary import _build_analyze_prompt


def test_weekly_analyze_prompt_is_detailed():
    p = _build_analyze_prompt("标题", "Nature", "abstract " * 100)
    assert "2~3" in p, "应要求 2~3 句"
    assert "≤100" in p, "应要求 ≤100 字"
    assert "50-80字" not in p and "50-80 字" not in p


if __name__ == "__main__":
    test_weekly_analyze_prompt_is_detailed()
    print("OK")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 test_weekly_highlight.py`
Expected: FAIL(`ImportError: cannot import name '_build_analyze_prompt'`)

- [ ] **Step 3: 抽出模块级纯函数(weekly_summary.py,放在 `WeeklySummarizer` 类定义之前,如 L113 附近)**

```python
def _build_analyze_prompt(title: str, journal: str, abstract: str) -> str:
    """单篇详细解读 prompt:一段 2~3 句、≤100 字的中文分析。"""
    return f"""请对以下文献进行分析，生成一段 2~3 句、≤100 字的中文解读，突出核心创新点、最强结论与研究意义。

标题: {title}
期刊: {journal}
摘要: {abstract[:500]}

要求:
1. 用中文输出
2. 2~3 句、≤100 字
3. 突出核心创新点与最强结论
4. 说明研究意义或应用价值
5. 不要照抄摘要，而是分析总结

直接输出分析结果，不要添加任何前缀或格式："""
```

- [ ] **Step 4: 改 `_analyze_single_article` 用该函数(L343-356 替换为一行调用)**

把 L343-356 的内联 `prompt = f"""..."""` 整体替换为:

```python
            prompt = _build_analyze_prompt(title, journal, abstract)
```

- [ ] **Step 5: 放行返回 clamp(L381)**

```python
            return analysis[:130]  # 限制长度(≤100字留余量)
```

- [ ] **Step 6: 普通卡摘要预览不截断 ≤200 字摘要(L1512)**

```python
                    preview_raw = shorten_text(preview_source, 240)
```

- [ ] **Step 7: 跑测试确认通过**

Run: `python3 test_weekly_highlight.py`
Expected: `OK`

- [ ] **Step 8: 跑全量(周报渲染测试本地缺 bs4 会 skip,CI 跑)**

Run: `python run_tests.py`
Expected: 新 `test_weekly_highlight` passed;无新增 failed。

- [ ] **Step 9: 提交**

```bash
git add weekly_summary.py test_weekly_highlight.py
git commit -m "feat(weekly): 单篇解读改2~3句≤100字,摘要预览放宽到240"
```

---

### Task 5: 收尾——文档、回填、验证

**Files:**
- Modify: `README.md`(若其中描述了日报/周报每篇展示字段,更新为"摘要中文 + 详细亮点";无则跳过)
- 无代码改动;本任务是验证 + 回填操作。

**Interfaces:** 无。

- [ ] **Step 1: 全量回归**

Run: `python run_tests.py`
Expected: 全绿(新增 4 个测试均 passed;bs4/json_repair 相关 skip)。

- [ ] **Step 2: 逐个脚本式 main 测试**

Run: `for t in test_daily_pages_render test_text_normalizer test_focus_filter test_entry_navigation_docs test_rss_generation; do python3 $t.py || echo "FAIL $t"; done`
Expected: 每个打印各自 OK,无 FAIL。

- [ ] **Step 3: 本地干跑一次日报渲染(用已有缓存,确认页面含两块)**

Run: `python generate_daily_pages.py --rerender-only --days 1 2>&1 | tail -5`
说明:`--rerender-only` 复用旧缓存(旧缓存摘要短),仅验证**渲染层**不报错、页面结构含 "📄 摘要"/"💡 亮点"(若旧缓存 abstract_zh 非空)。真正的长文本需 Step 5 回填后才出现。
Expected: 无异常退出。

- [ ] **Step 4: 合并分支到 main(走 finishing-a-development-branch 决策)**

由执行者在所有 Task 通过、用户确认后,按 `superpowers:finishing-a-development-branch` 选择合并方式。

- [ ] **Step 5: 触发回填(合并后,经 git-credential token + REST API,本环境无 gh CLI)**

- `backfill-daily.yml`:`days=14`、`force=true`。
- `backfill-weekly.yml`:最近 2 周。
触发后盯 Actions 运行结果;成功后线上验证近 1~2 天日报页每篇出现加长摘要 + 2~3 句亮点。

- [ ] **Step 6: 提交收尾(若改了 README)**

```bash
git add README.md
git commit -m "docs: 更新日报/周报每篇展示字段说明"
```

---

## Self-Review

**Spec coverage:**
- A. AI 生成层(摘要≤200/亮点2~3句/输入600/clamp) → Task 1 ✅
- B. 日报渲染补摘要块 → Task 2 ✅;核心区已具备,无需改(spec 已注明) ✅
- B. 周报普通卡摘要默认可见 → 既有 `preview_html` 已默认显示,Task 4 Step 6 仅放宽截断防止 ≤200 字被切 ✅;核心区自动受益 ✅
- B. CSS + SW bump → Task 3 ✅
- C. 回填(无新代码) → Task 5 Step 5 ✅
- 周报详细亮点(ai_analysis 加长) → Task 4 ✅
- 测试 → 每 Task 内含 TDD;Task 5 收尾全量 ✅

**Placeholder scan:** 无 TBD/TODO;每个 code step 给出完整代码。README 改动为条件性(明确"无则跳过")。

**Type consistency:** `_build_prompt`/`_clamp_text`/`render_unified_item`/`_build_analyze_prompt`/`shorten_text` 名称在各 Task 间一致;clamp 阈值统一(abstract 240、one_sentence 120、weekly analyze [:130]);CSS 类名 `.daily-paper-abstract`/`.daily-paper-highlight` 与渲染代码一致。
