# 日报 × Feed v2 实现计划 — 英文信息图 + 分层深析 + 强耦合 + 交互修复

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把日报与 Feed 升级为：可读英文信息图（图字分离）+ 分层深析（APS全文/arXiv摘要级/常规）+ 同源补全字段强耦合 + Feed 交互修复（收藏FAB/进度/分组/AI交叉置顶/中文标题/死链）。

**Architecture:** 复用现有 `image_provider` 流式管线、`classify_taxonomy`、预算/幂等机制、`BookmarkUI/LikeUI`。后端改 `poster_generator`(信息图)、`deep_reader`(摘要级)、`run_deep`(分层+预算)、`generate_daily_pages`(core_export 补字段+tier2候选)、`feed_builder`(死链/元信息)。前端重构 `docs/feed.js/feed.css/feed.html` + `index.html` 入口 + `bookmarks.css/likes.css`。

**Tech Stack:** Python3.11(requests/Pillow)、gpt-5.5 chat + gpt-image-2(Responses流式)、原生JS + jsdom、GitHub Actions。

---

## 环境与测试约定（每个 worker 必读）
- 本地**无 pytest/Pillow/bs4**，只 stdlib。Python 测试**无 fixture**（不用 monkeypatch/tmp_path），用 `unittest.mock` + `tempfile`，每个 `test_*` 无参函数；跑 `python3 run_tests.py <test_x.py>`，**不要**用 `python3 -m pytest`。
- 前端测试：浏览器风格 HTML 测试页（仿 `docs/test-feed.html`），跑 `node /tmp/run_fe.js docs/test-*.html`（若缺 jsdom：`cd /tmp && npm install jsdom --no-save --silent`）。通过=`#out` 无 `✗`、`FAIL: 0`。
- 安全：**任何提交文件不得出现真实凭据**（APS密码/OSS key/网关key/IP）。测试用假值。
- 每个 worker 完成后跑相关测试确认通过再 commit。

## File Structure（职责）
| 文件 | 改动 |
|---|---|
| `ai_prompts/poster_elements.txt` | 升级：输出 中文5要素 + 英文短标签 `elements_en` + `title_zh` |
| `ai_prompts/abstract_analysis.txt` (新) | 摘要级解析模板 |
| `poster_generator.py` | `extract_elements` 返回 elements/elements_en/title_zh；`build_infographic_prompt`；`generate_poster` 用信息图 prompt + max_edge=1280 |
| `deep_reader.py` | `abstract_read(meta, abstract, provider)` |
| `generate_daily_pages.py` | 抽 `build_core_export`/`build_tier2_candidates` 纯函数 + main 调用；日报卡加「在 Feed 中查看」 |
| `run_deep.py` | `process_arxiv_tier2`；统一预算；`_enrich_one` 写 title_zh；删 `DEEP_ENABLE_ARXIV_IMAGES` 闸；`write_feed_json` 传 today |
| `feed_builder.py` | `normalize_link`(DOI→doi.org) + `daily_url` + tier2 字段 |
| `docs/feed.js` | 卡片重构(图字分离/中文标题/兜底/链接修复/深链) + 收藏FAB/分类置顶/进度分组 |
| `docs/feed.css` | 图字分离布局 + 进度条 + 日期标头 + .feed-card position |
| `docs/feed.html` | 进度条容器 + 引 likes.css |
| `docs/likes.css` (新) | `.like-btn` 角标样式（daily/weekly/feed 共用） |
| `docs/bookmarks.css` | `.feed-card` 加入 position:relative 列表 |
| `docs/index.html` | 显眼 Feed hero 入口 |
| `.github/workflows/generate-deep.yml` | 适配（T2 默认开、预算保持） |

测试文件：`test_poster_generator.py`(扩) `test_deep_reader.py`(扩) `test_daily_pages_render.py`(扩) `test_run_deep.py`(扩) `test_feed_json.py`(扩) `docs/test-feed.html`(扩)。

---

## Task 1：WS-A 英文信息图 + title_zh（poster_generator）

**Files:** Modify `ai_prompts/poster_elements.txt`、`poster_generator.py`；Test `test_poster_generator.py`(扩)

- [ ] **Step 1: 改 prompt 模板** `ai_prompts/poster_elements.txt` —— 在现有"输出 JSON 5 个中文键"基础上，要求**同一个 JSON** 额外包含：`title_zh`(论文标题中文翻译) 与 `elements_en`(对象，键 `research_question/method/workflow/result/value`，每个 ≤6 个英文单词的短标签，用于信息图)。明确："elements_en 用作信息图英文标签，要短、名词性、可视觉化"。保留原 5 中文键。

- [ ] **Step 2: 写失败测试**（追加到 `test_poster_generator.py`）

```python
def test_extract_elements_returns_en_and_title_zh():
    class P:
        def call_api(self, prompt):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"标题中文","elements_en":{"research_question":"RQ","method":"GNN potential",'
                    '"workflow":"train infer","result":"5x faster","value":"materials discovery"}}')
    out = extract_elements({"title": "T"}, "body", provider=P())
    assert out["elements"]["创新方法"] == "m"
    assert out["title_zh"] == "标题中文"
    assert out["elements_en"]["method"] == "GNN potential"

def test_extract_elements_back_compat_without_en():
    # 旧式只回中文 5 键也不崩，elements_en/title_zh 给空
    class P:
        def call_api(self, prompt):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}'
    out = extract_elements({"title": "T"}, "body", provider=P())
    assert out["elements"]["研究问题"] == "q"
    assert out["title_zh"] == ""
    assert isinstance(out["elements_en"], dict)

def test_infographic_prompt_is_readable_english_no_chinese():
    p = build_infographic_prompt({"method": "GNN potential", "result": "5x faster"}, "Some Title")
    assert "infographic" in p.lower()
    assert "16:9" in p
    assert "no chinese" in p.lower() or "no chinese characters" in p.lower()
    assert "do not invent" in p.lower() or "schematic" in p.lower()
    assert "GNN potential" in p  # 英文标签进图

def test_generate_poster_returns_title_zh_and_image(monkeypatch=None):
    import tempfile
    from unittest import mock
    class P:
        def call_api(self, prompt):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"标题中文","elements_en":{"method":"GNN"}}')
    with mock.patch.object(poster_generator, "generate_and_save",
                           side_effect=lambda prompt, out_path, **k: out_path):
        res = poster_generator.generate_poster({"title": "T", "doc_id": "d1"}, "body",
                                               provider=P(), out_dir=tempfile.mkdtemp())
    assert res["title_zh"] == "标题中文"
    assert res["image"].endswith("d1.webp")
    assert res["elements"]["创新方法"] == "m"
```
（确保文件顶部 `import poster_generator` 与 `from poster_generator import extract_elements, build_infographic_prompt` 存在。）

- [ ] **Step 3: 运行确认失败**

Run: `python3 run_tests.py test_poster_generator.py`
Expected: FAIL（新键/新函数缺失）

- [ ] **Step 4: 实现** `poster_generator.py`

把 `_parse_json` 与 `extract_elements` 改为返回结构化对象，并新增 `build_infographic_prompt`，`generate_poster` 改用信息图 prompt：

```python
_KEYS = ["研究问题", "创新方法", "工作流程", "关键结果", "应用价值"]
_EN_KEYS = ["research_question", "method", "workflow", "result", "value"]

def _parse_elements(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    if not all(k in d for k in _KEYS):
        return None
    elements = {k: str(d.get(k, "")) for k in _KEYS}
    en_raw = d.get("elements_en") or {}
    elements_en = {k: str(en_raw.get(k, "")) for k in _EN_KEYS} if isinstance(en_raw, dict) else {}
    return {"elements": elements, "elements_en": elements_en,
            "title_zh": str(d.get("title_zh", "") or "")}

def extract_elements(meta, markdown, provider, language="中文", max_chars=40000):
    if not markdown or provider is None:
        return None
    try:
        ctx = markdown[:max_chars]
        prompt = Template(_load_template()).safe_substitute(
            language=language, title=str(meta.get("title", "")), context=ctx)
        return _parse_elements(provider.call_api(prompt))
    except Exception as e:
        print(f"⚠️ extract_elements failed: {e}"); return None

def build_infographic_prompt(elements_en, title):
    labels = "; ".join(f"{k}: {(elements_en or {}).get(k, '')}" for k in _EN_KEYS
                       if (elements_en or {}).get(k))
    return (
        "Generate a clean, readable Modern Minimalist Tech Infographic that visually "
        "explains a research paper, flat vector illustration with subtle isometric elements, "
        "corporate Memphis style, clean lines and geometric shapes. "
        "Left-to-right 5-node process flow: INPUT -> METHOD -> WORKFLOW -> RESULT -> VALUE, "
        "with SHORT ENGLISH labels only (a few words each), simple schematic bar/line/network "
        "diagrams as icons. Background solid off-white #F5F5F7, no clutter. "
        "Palette: deep academic blue and slate grey, vibrant orange/teal accents, high contrast. "
        "16:9 aspect ratio, high resolution, crisp legible English text labels. "
        "IMPORTANT: use ONLY short English words as labels — NO Chinese characters, no garbled text. "
        "This is a SCHEMATIC concept diagram: do NOT invent specific numeric values or fake data. "
        "No photorealism, no messy sketches, no chaotic background. "
        f"Node labels to depict: {labels}. Paper topic: {str(title)[:80]}.")

def generate_poster(meta, markdown, provider, out_dir="docs/images/posters",
                    api_key=None, base=None):
    parsed = extract_elements(meta, markdown, provider)
    if not parsed:
        return None
    doc_id = meta.get("doc_id") or meta.get("paper_id") or "unknown"
    out_path = os.path.join(out_dir, f"{doc_id}.webp")
    prompt = build_infographic_prompt(parsed["elements_en"], meta.get("title", ""))
    saved = generate_and_save(prompt, out_path, max_edge=1280,
                              api_key=api_key, base=base)
    return {"elements": parsed["elements"],
            "elements_en": parsed["elements_en"],
            "title_zh": parsed["title_zh"],
            "image": (saved or "").replace("docs/", "") or None,
            "doc_id": doc_id}
```
删除旧 `_parse_json`/`build_background_prompt`（被 `_parse_elements`/`build_infographic_prompt` 取代）。

- [ ] **Step 5: 运行确认通过**

Run: `python3 run_tests.py test_poster_generator.py`
Expected: PASS（含旧用例若引用 build_background_prompt 需同步更新为 build_infographic_prompt）

- [ ] **Step 6: 提交**

```bash
git add ai_prompts/poster_elements.txt poster_generator.py test_poster_generator.py
git commit -m "feat(poster): readable English infographic + elements_en + title_zh"
```

---

## Task 2：WS-H 摘要级解析（deep_reader）

**Files:** Create `ai_prompts/abstract_analysis.txt`；Modify `deep_reader.py`；Test `test_deep_reader.py`(扩)

- [ ] **Step 1: 写模板** `ai_prompts/abstract_analysis.txt`（占位 `${title}/${authors}/${abstract}`）：

```
你是严谨的资深研究员。仅依据下面提供的论文【摘要】（无全文），用中文做精炼解析。不要臆测摘要未给出的具体数值或实验细节，无法确定处明确说"摘要未详述"。

## 核心概览
100 字内概述这篇论文做了什么、属于什么方向。

## 方法要点
列出可从摘要推断的关键方法/技术（要点式，每点一句）。

## 关键结果
摘要中明确陈述的主要结果或结论（要点式）。

## 创新性判断
相对同方向工作，这篇的新颖点可能在哪里（基于摘要的合理判断，注明不确定性）。

---
论文：《${title}》（${authors}）
摘要：
${abstract}
```

- [ ] **Step 2: 写失败测试**（追加 `test_deep_reader.py`）

```python
from deep_reader import abstract_read, build_abstract_prompt

def test_build_abstract_prompt_fills():
    p = build_abstract_prompt(title="T", authors="A", abstract="ABS-BODY")
    assert "T" in p and "ABS-BODY" in p and "${abstract}" not in p

def test_abstract_read_uses_provider():
    calls = {}
    class P:
        def call_api(self, prompt):
            calls["p"] = prompt
            return "## 核心概览\n摘要级解析内容"
    out = abstract_read({"title": "T", "authors": "['A']"}, "the abstract text", provider=P())
    assert "摘要级解析内容" in out
    assert "the abstract text" in calls["p"]

def test_abstract_read_empty_or_error_returns_empty():
    class Boom:
        def call_api(self, p): raise Exception("down")
    assert abstract_read({"title": "T"}, "", provider=Boom()) == ""
    assert abstract_read({"title": "T"}, "abs", provider=Boom()) == ""
```

- [ ] **Step 3: 运行确认失败** → `python3 run_tests.py test_deep_reader.py`

- [ ] **Step 4: 实现** `deep_reader.py` 追加：

```python
_ABS_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "abstract_analysis.txt")

def _load_abs_template():
    with open(_ABS_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def build_abstract_prompt(title, authors, abstract, max_chars=6000):
    abs_txt = (abstract or "")[:max_chars]
    return Template(_load_abs_template()).safe_substitute(
        title=str(title or ""), authors=_fmt_authors(authors), abstract=abs_txt)

def abstract_read(meta, abstract, provider):
    if not abstract or provider is None:
        return ""
    try:
        prompt = build_abstract_prompt(meta.get("title"), meta.get("authors"), abstract)
        return (provider.call_api(prompt) or "").strip()
    except Exception as e:
        print(f"⚠️ abstract_read failed for {meta.get('doc_id') or meta.get('link')}: {e}")
        return ""
```

- [ ] **Step 5: 运行确认通过** → `python3 run_tests.py test_deep_reader.py`

- [ ] **Step 6: 提交**

```bash
git add ai_prompts/abstract_analysis.txt deep_reader.py test_deep_reader.py
git commit -m "feat(deep): abstract-level analysis for arXiv (no full text)"
```

---

## Task 3：WS-C core_export 补字段 + tier2 候选（generate_daily_pages）

**Files:** Modify `generate_daily_pages.py`；Test `test_daily_pages_render.py`(扩)

- [ ] **Step 1: 写失败测试**（追加 `test_daily_pages_render.py`）

```python
def test_build_core_export_has_category_and_link():
    from generate_daily_pages import build_core_export
    items = [{"title": "ML interatomic potential for perovskite",
              "title_zh": "钙钛矿的机器学习势", "summary": "图神经网络势",
              "abstract": "graph neural network potential for materials",
              "abstract_zh": "用于材料的图神经网络势",
              "link": "http://arxiv.org/abs/2601.001", "journal": "arXiv"}]
    out = build_core_export(items)
    assert out[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert out[0]["abstract"]            # 英文摘要透传
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
```

- [ ] **Step 2: 运行确认失败** → `python3 run_tests.py test_daily_pages_render.py -? `（用 `python3 run_tests.py test_daily_pages_render.py`）

- [ ] **Step 3: 实现** `generate_daily_pages.py`：在模块级（靠近 `render_deep_section` 附近）新增两个纯函数，并在 main 的 core_export 处改调用。

```python
from focus_core import classify_taxonomy, is_core_focus  # 顶部已可能有 focus 相关 import；若无则加

def build_core_export(core_items):
    out = []
    for it in (core_items or []):
        link = (it.get("link") or "").strip()
        out.append({
            "title": it.get("title") or it.get("title_en") or "",
            "title_zh": it.get("title_zh") or "",
            "summary": it.get("summary") or it.get("abstract_zh") or "",
            "abstract": it.get("abstract") or it.get("abstract_en") or "",
            "category": classify_taxonomy(it),
            "link": link,
            "journal": it.get("journal") or "",
        })
    return out

def build_tier2_candidates(full_list, max_n=20):
    cand = []
    for it in (full_list or []):
        cat = classify_taxonomy(it)
        if cat in ("AI×物理", "AI×化学·材料") or it.get("is_core_focus"):
            cand.append({
                "title": it.get("title") or it.get("title_en") or "",
                "title_zh": it.get("title_zh") or "",
                "summary": it.get("summary") or it.get("abstract_zh") or "",
                "abstract": it.get("abstract") or it.get("abstract_en") or "",
                "category": cat,
                "link": (it.get("link") or "").strip(),
                "journal": it.get("journal") or "",
            })
    return cand[:max_n]
```

在 main 的 core_export 区（当前 :1020-1035）改为：
```python
    try:
        core_export = build_core_export(core_items)
        os.makedirs("data", exist_ok=True)
        with open(os.path.join("data", f"arxiv_core_{day_str}.json"), "w", encoding="utf-8") as cf:
            json.dump(core_export, cf, ensure_ascii=False, indent=2)
        tier2 = build_tier2_candidates(summary.get("full_list", []))
        with open(os.path.join("data", f"arxiv_tier2_{day_str}.json"), "w", encoding="utf-8") as tf:
            json.dump(tier2, tf, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ arxiv core/tier2 export skipped: {e}")
```

- [ ] **Step 4: 运行确认通过** → `python3 run_tests.py test_daily_pages_render.py`（含既有用例）。再 `python3 -c "import generate_daily_pages"` 确认导入无误。

- [ ] **Step 5: 提交**

```bash
git add generate_daily_pages.py test_daily_pages_render.py
git commit -m "feat(daily): core_export adds category/abstract + tier2 candidates export"
```

---

## Task 4：WS-B 分层深析 + APS title_zh + 统一预算（run_deep）

**Files:** Modify `run_deep.py`；Test `test_run_deep.py`(扩)

- [ ] **Step 1: 写失败测试**（追加 `test_run_deep.py`）

```python
def test_enrich_one_sets_title_zh_from_poster():
    import run_deep, tempfile
    from unittest import mock
    meta = {"title": "EN title", "has_full_text": True, "markdown_oss_key": "k", "doc_id": "d1"}
    class FakeClient:
        def fetch_markdown(self, m): return "# P\nbody"
    class P:
        def call_api(self, p):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"中文标题","elements_en":{"method":"GNN"}}') if ("研究问题" in p or "JSON" in p) \
                   else "## 完整\n第五部分：创新评估 " + "y"*6000
    with mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        rec = run_deep._enrich_one(meta, FakeClient(), P(), tempfile.mkdtemp())
    assert rec["title_zh"] == "中文标题"

def test_process_arxiv_tier2_enriches_and_budgets():
    import run_deep, tempfile
    from unittest import mock
    cands = [{"title": "ML for magnet", "abstract": "neural network spin", "link": "http://z%d" % i,
              "category": "AI×物理"} for i in range(5)]
    class P:
        def call_api(self, p):
            return ('{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v",'
                    '"title_zh":"标题","elements_en":{"method":"GNN"}}') if ("研究问题" in p or "JSON" in p) \
                   else "## 摘要级\n创新性判断 " + "z"*5200
    with mock.patch.object(run_deep, "generate_and_save", side_effect=lambda prompt, out_path, **k: out_path):
        out, used = run_deep.process_arxiv_tier2("2026-05-28", cands, P(),
                                                 out_dir=tempfile.mkdtemp(), max_new=3)
    assert used == 3
    assert sum(1 for x in out if x.get("deep_analysis")) == 3
    assert out[0].get("image", "").endswith(".webp") or out[0].get("image") is None
```

- [ ] **Step 2: 运行确认失败** → `python3 run_tests.py test_run_deep.py`

- [ ] **Step 3: 实现** `run_deep.py`

(a) `_enrich_one` 写入 `title_zh`（来自 poster）：在 `rec["poster"] = ...` 之后加：
```python
    if rec.get("poster") and rec["poster"].get("title_zh"):
        rec["title_zh"] = rec["poster"]["title_zh"]
```

(b) 新增 arXiv 摘要级解析的单篇与批处理（信息图复用 generate_poster，但输入是 abstract 而非全文；title_zh 来自 poster 或 candidate）：
```python
from deep_reader import abstract_read

def _enrich_arxiv_tier2_one(cand, provider, out_dir, cached=None):
    if cached and _deep_complete(cached.get("deep_analysis")):
        return cached
    abs = cand.get("abstract") or cand.get("summary") or ""
    rec = dict(cand)
    rec["source"] = "arxiv"
    rec["category"] = cand.get("category") or classify(cand, provider=provider)
    rec["deep_analysis"] = abstract_read(cand, abs, provider=provider) if abs else ""
    # 信息图：用 abstract 当 markdown 喂 generate_poster（doc_id 用 link 的 hash）
    import hashlib
    doc_id = "ax" + hashlib.sha1((cand.get("link") or cand.get("title","")).encode("utf-8")).hexdigest()[:14]
    meta = {"title": cand.get("title", ""), "doc_id": doc_id}
    poster = (cached or {}).get("poster") or (generate_poster(meta, abs, provider=provider, out_dir=out_dir) if abs else None)
    rec["poster"] = poster
    rec["image"] = (poster or {}).get("image")
    rec["poster_elements"] = (poster or {}).get("elements")
    if poster and poster.get("title_zh") and not rec.get("title_zh"):
        rec["title_zh"] = poster["title_zh"]
    return rec

def process_arxiv_tier2(date, candidates, provider, out_dir="docs/images/posters",
                        max_workers=5, cache=None, max_new=None):
    cache = cache or {}
    cands = candidates or []
    cached, fresh = [], []
    for c in cands:
        key = c.get("link") or c.get("title")
        prev = cache.get(key)
        (cached if (prev and _deep_complete(prev.get("deep_analysis"))) else fresh).append((c, prev))
    if max_new is not None:
        fresh = fresh[:max(0, max_new)]
    results = [p for (_c, p) in cached]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_enrich_arxiv_tier2_one, c, provider, out_dir, prev) for (c, prev) in fresh]
        for f in futs:
            try: results.append(f.result())
            except Exception as e: print(f"⚠️ tier2 enrich failed: {e}")
    return results, len(fresh)
```

(c) `main()`：统一预算覆盖 T1(APS)+T2(arXiv tier2)，T2 结果写回 `data/arxiv_core_<date>.json`（带 deep/image/category），删除 `DEEP_ENABLE_ARXIV_IMAGES` 分支。在每个日期循环里，APS 处理后用剩余预算跑 tier2：
```python
        # T2: arXiv AI×交叉 摘要级深析 + 信息图（用剩余预算）
        try:
            import json as _json
            tpath = f"data/arxiv_tier2_{d}.json"
            if budget > 0 and os.path.exists(tpath):
                cands = _json.load(open(tpath, encoding="utf-8"))
                t2cache = {(x.get("link") or x.get("title")): x for x in _load_core_cache(d)}
                t2, t2used = process_arxiv_tier2(d, cands, provider, max_workers=workers,
                                                 cache=t2cache, max_new=budget)
                budget -= t2used
                if t2:
                    with open(f"data/arxiv_core_{d}.json", "w", encoding="utf-8") as cf:
                        _json.dump(t2, cf, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ tier2 processing failed for {d}: {e}")
```
并新增 `_load_core_cache(date)`（读已有 `data/arxiv_core_<date>.json` 为 list，失败 []）：
```python
def _load_core_cache(date):
    path = f"data/arxiv_core_{date}.json"
    if os.path.exists(path):
        try: return json.load(open(path, encoding="utf-8"))
        except Exception: return []
    return []
```
删除原 `arxiv_images`/`DEEP_ENABLE_ARXIV_IMAGES` 相关分支与 `enrich_arxiv_core` 调用（保留 `enrich_arxiv_core`/`_enrich_arxiv_one` 函数不删亦可，但 main 不再用它）。

(d) `write_feed_json` 传 today：
```python
    import datetime as _dt
    today = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).date().isoformat()  # 北京时间
    write_feed_json(_load_existing_feeds(), today=today, window_days=60)
```

- [ ] **Step 4: 运行确认通过** → `python3 run_tests.py test_run_deep.py` + `python3 -c "import run_deep"`

- [ ] **Step 5: 提交**

```bash
git add run_deep.py test_run_deep.py
git commit -m "feat(deep): tiered arXiv abstract-level analysis+infographic, APS title_zh, unified budget, feed.generated"
```

---

## Task 5：WS-F 死链/元信息/中文（feed_builder）

**Files:** Modify `feed_builder.py`；Test `test_feed_json.py`(扩)

- [ ] **Step 1: 写失败测试**（追加 `test_feed_json.py`）

```python
from feed_builder import normalize_link, build_feed

def test_normalize_link_doi_to_url():
    assert normalize_link("10.1103/766t-tqsy") == "https://doi.org/10.1103/766t-tqsy"
    assert normalize_link("http://arxiv.org/abs/2601.1") == "http://arxiv.org/abs/2601.1"
    assert normalize_link("") == ""

def test_aps_item_link_normalized_and_daily_url():
    aps = [{"source": "APS", "title": "T", "title_zh": "标题", "doi": "10.1103/abc",
            "doc_id": "d1", "deep_analysis": "x"}]
    feed = build_feed(aps, [], date="2026-05-28")
    it = feed["items"][0]
    assert it["link"] == "https://doi.org/10.1103/abc"
    assert it["daily_url"] == "daily/2026-05-28.html"
```

- [ ] **Step 2: 运行确认失败** → `python3 run_tests.py test_feed_json.py`

- [ ] **Step 3: 实现** `feed_builder.py`

```python
def normalize_link(link):
    s = (link or "").strip()
    if not s:
        return ""
    if s.startswith("http://") or s.startswith("https://"):
        return s
    # 裸 DOI（含 '/' 且无协议）→ doi.org
    return f"https://doi.org/{s}"
```
`_item_from_aps`/`_item_from_arxiv` 的 link 改用 `normalize_link(a.get("link") or a.get("doi",""))`；`build_feed` 给每条加 `daily_url`：
```python
def build_feed(aps_items, arxiv_items, date):
    items = [_item_from_aps(a) for a in (aps_items or [])] + \
            [_item_from_arxiv(a) for a in (arxiv_items or [])]
    for it in items:
        it["daily_url"] = f"daily/{date}.html"
    return {"date": date, "items": items}
```
（`_item_from_aps` 内：`"link": normalize_link(a.get("link") or a.get("doi", ""))`；`_item_from_arxiv` 内：`"link": normalize_link(a.get("link", ""))`。）

- [ ] **Step 4: 运行确认通过** → `python3 run_tests.py test_feed_json.py`

- [ ] **Step 5: 提交**

```bash
git add feed_builder.py test_feed_json.py
git commit -m "feat(feed): normalize DOI links to doi.org + daily_url backlink"
```

---

## Task 6：WS-D Feed 卡片重构（图字分离/中文标题/兜底/深链）

**Files:** Modify `docs/feed.js`、`docs/feed.css`；Test `docs/test-feed.html`(扩)

- [ ] **Step 1: 扩测试** `docs/test-feed.html`：mock items（1 APS 带 image+poster_elements+deep_analysis+title_zh、1 arxiv 无 image 无 title_zh）调 `window.FeedUI.renderFeed(items, container)` 后断言：
  - 每卡标题元素 `.feed-title-zh` 文本 = title_zh（APS）；无 title_zh 的卡回退 title_en（不为空）。
  - **不再有 `.poster-overlay`**（图字分离）；改为图后跟独立 `.poster-elements` 块，含 5 行 `.poster-row`（APS）。
  - `img` 的 src = item.image；卡片有 `.poster-figure`。
  - `.src-link` href 以 http 开头（链接修复后数据已是 http；前端不再产生相对裸 DOI）。
  - 调 `window.FeedUI.applyDeepLink({date:'2026-05-28', doc:'d1'})`（或通过 `renderFeed` 后 `scrollToTarget`）能给匹配卡加 `.feed-target` 高亮 class（不报错即可）。
  断言写法仿现有 test-feed.html 的 assert/log/PASS 计数。

- [ ] **Step 2: 运行确认失败** → `node /tmp/run_fe.js docs/test-feed.html`

- [ ] **Step 3: 实现** `docs/feed.js`

(a) `buildPosterFigure`：**移除 overlay**，只放 `<img>`：
```javascript
  function buildPosterFigure(item) {
    const fig = el('div', 'poster-figure');
    const img = document.createElement('img');
    img.loading = 'lazy';
    img.src = item.image;
    img.alt = item.title_zh || item.title_en || '';
    img.setAttribute('onerror', "this.style.display='none'");
    fig.appendChild(img);
    return fig;
  }
  function buildElementsBlock(item) {
    if (!item.poster_elements || typeof item.poster_elements !== 'object') return null;
    const box = el('div', 'poster-elements');
    let rows = 0;
    POSTER_ROWS.forEach(function (key) {
      const val = item.poster_elements[key];
      if (val == null || val === '') return;
      box.appendChild(el('div', 'poster-row', '<b>' + esc(key) + '</b>' + esc(val)));
      rows++;
    });
    return rows > 0 ? box : null;
  }
```
(b) `buildCard`：标题中文优先 + 摘要兜底（无 summary 用 abstract 截断）+ 图在标题后、要素块在图后 + 深链高亮 + daily 回链：
```javascript
  function buildCard(item) {
    const card = el('article', 'feed-card');
    card.dataset.bookmarkKey = item.link || '';
    card.dataset.category = item.category || '';
    if (item.doc_id) card.dataset.doc = item.doc_id;
    if (item.date) card.dataset.date = item.date;

    if (item.category) card.appendChild(el('span', 'cat-tag', esc(item.category)));

    const h = el('h2', 'feed-title-zh');
    h.textContent = item.title_zh || item.title_en || '(无标题)';
    card.appendChild(h);

    const sumText = item.summary || (item.abstract ? String(item.abstract).slice(0, 180) + '…' : '');
    if (sumText) card.appendChild(el('p', 'summary', esc(sumText)));

    if (item.image) card.appendChild(buildPosterFigure(item));
    const elemBlock = buildElementsBlock(item);
    if (elemBlock) card.appendChild(elemBlock);

    const linkRow = el('div', 'card-links');
    if (item.link) {
      const a = el('a', 'src-link'); a.href = item.link; a.target = '_blank';
      a.rel = 'noopener noreferrer'; a.textContent = '查看原文 ↗'; linkRow.appendChild(a);
    }
    if (item.daily_url) {
      const d = el('a', 'daily-link'); d.href = item.daily_url;
      d.textContent = '当日日报 ↗'; linkRow.appendChild(d);
    }
    card.appendChild(linkRow);

    if (item.deep_analysis) {
      const details = el('details', 'deep-details');
      details.appendChild(el('summary', null, '展开精读'));
      const body = el('div', 'deep-body'); body.textContent = item.deep_analysis;
      details.appendChild(body); card.appendChild(details);
    }
    return card;
  }
```
(c) 深链：新增 `applyDeepLink(params)` 与在 `loadFeed` 末尾解析 `location.search`：
```javascript
  function applyDeepLink(params) {
    if (!params || (!params.doc && !params.date)) return;
    const cards = document.querySelectorAll('.feed-card');
    for (const c of cards) {
      if ((params.doc && c.dataset.doc === params.doc) ||
          (!params.doc && params.date && c.dataset.date === params.date)) {
        c.classList.add('feed-target');
        if (c.scrollIntoView) c.scrollIntoView();
        break;
      }
    }
  }
```
在 `renderFeed(items, main)` 之后（`loadFeed` 的 then 里）：
```javascript
        const sp = new URLSearchParams(location.search);
        applyDeepLink({ doc: sp.get('doc'), date: sp.get('date') });
```
并把 `applyDeepLink` 暴露到 `window.FeedUI`。

- [ ] **Step 4: 改 `docs/feed.css`** — 删除 `.poster-overlay` 那段盖图样式，新增图字分离与高亮：
```css
.poster-elements{margin:8px 0;display:flex;flex-direction:column;gap:6px;font-size:14px;line-height:1.6;}
.poster-row b{color:#1456b8;margin-right:6px;}
.card-links{display:flex;gap:16px;margin-top:6px;}
.daily-link{color:#0f766e;text-decoration:none;}
.feed-target{outline:3px solid #f59e0b;outline-offset:-3px;}
```
（保留 `.poster-figure`/`.poster-figure img`，删 `.poster-overlay`/`.poster-row` 旧定义中依赖 overlay 的部分。）

- [ ] **Step 5: 运行确认通过** → `node /tmp/run_fe.js docs/test-feed.html`（并回归 `docs/test-bookmarks.html docs/test-likes.html`）

- [ ] **Step 6: 提交**

```bash
git add docs/feed.js docs/feed.css docs/test-feed.html
git commit -m "feat(feed): image/text separation, Chinese title, summary fallback, deep-link + daily backlink"
```

---

## Task 7：WS-D 收藏/点赞修复 + AI 交叉分类置顶

**Files:** Modify `docs/feed.js`、`docs/feed.css`、`docs/bookmarks.css`；Create `docs/likes.css`；Modify `docs/feed.html`、daily/weekly 模板的 head（引 likes.css）；Test `docs/test-feed.html`(扩)

- [ ] **Step 1: 扩测试** `docs/test-feed.html`：renderFeed 后断言每卡内同时有 `.bookmark-btn` 与 `.like-btn`（`window.BookmarkUI`/`window.LikeUI` 在测试页已加载）；`buildCatBar([{category:'其他'},{category:'AI×物理'}])` 生成的 chips 中 `AI×物理` 排在 `其他` 之前（紧随 `全部`）。

- [ ] **Step 2: 运行确认失败** → `node /tmp/run_fe.js docs/test-feed.html`

- [ ] **Step 3: 实现**
(a) `docs/feed.js` `renderFeed` 末尾：attach 后补调 FAB/手势（容错）：
```javascript
    if (window.literatureBookmarks && window.literatureBookmarks.ui) {
      const bu = window.literatureBookmarks.ui;
      bu.attachToCards(container);
      if (bu.renderFab) try { bu.renderFab(); } catch (e) {}
      if (bu.bindGestures) try { bu.bindGestures(container); } catch (e) {}
    } else if (window.BookmarkUI && window.BookmarkStore) {
      new window.BookmarkUI(new window.BookmarkStore()).attachToCards(container);
    }
    if (window.LikeUI && window.likeStore) {
      new window.LikeUI(window.likeStore).attachToCards(container);
    }
```
(b) `buildCatBar`：按 taxonomy tier 排序，AI× 置顶。新增 tier 权重表与排序：
```javascript
  const CAT_ORDER = ['AI×物理','AI×化学·材料','磁性·自旋电子学','铁电·极化','拓扑·电子结构',
                     '超导','量子信息·计算','软物质·流体·统计','其他凝聚态','其他'];
  function distinctCategories(items) {
    const seen = [];
    (items || []).forEach(function (it) {
      const c = it && it.category;
      if (c && seen.indexOf(c) === -1) seen.push(c);
    });
    seen.sort(function (a, b) {
      const ia = CAT_ORDER.indexOf(a), ib = CAT_ORDER.indexOf(b);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    });
    return seen;
  }
```
在 `buildCatBar` 给 AI× chip 加高亮 class：
```javascript
      if (cat === 'AI×物理' || cat === 'AI×化学·材料') chip.classList.add('chip-ai');
```
(c) `docs/feed.css` 加：`.feed-card{position:relative;}`（已有 .feed-card 规则，追加 position）；⭐/❤️ 错位 + AI chip 高亮：
```css
.feed-card .bookmark-btn{top:8px;right:8px;}
.feed-card .like-btn{position:absolute;top:8px;right:46px;z-index:5;background:transparent;border:0;
  font-size:18px;cursor:pointer;width:32px;height:32px;}
.cat-bar .chip.chip-ai{background:#1456b8;color:#fff;font-weight:700;}
.cat-bar .chip.chip-ai.active{box-shadow:0 0 0 2px #f59e0b inset;}
```
(d) Create `docs/likes.css`（daily/weekly/feed 共用的 ❤️ 基础样式，参照 .bookmark-btn）：
```css
.like-btn{position:absolute;top:8px;right:46px;width:32px;height:32px;display:inline-flex;
  align-items:center;justify-content:center;border:0;background:transparent;font-size:18px;
  cursor:pointer;z-index:5;-webkit-tap-highlight-color:transparent;}
.like-btn:active{transform:scale(0.92);}
.is-liked{border-right:3px solid #ef4444;}
```
(e) `docs/feed.html` head 增 `<link rel="stylesheet" href="likes.css">`；`generate_daily_pages.py` 与 `weekly_summary.py` 的 head 模板增 `<link rel="stylesheet" href="../likes.css">`（与现有 `../bookmarks.css` 并列）。
(f) `docs/bookmarks.css` 把 `.feed-card` 加进 position:relative 列表（第 34-38 行那组选择器末尾加 `,\n.feed-card`）。

- [ ] **Step 4: 运行确认通过** → `node /tmp/run_fe.js docs/test-feed.html docs/test-bookmarks.html docs/test-likes.html`

- [ ] **Step 5: 提交**

```bash
git add docs/feed.js docs/feed.css docs/likes.css docs/bookmarks.css docs/feed.html generate_daily_pages.py weekly_summary.py docs/test-feed.html
git commit -m "feat(feed): fix bookmark/like positioning + FAB + like CSS + AI-cross category pinning"
```

---

## Task 8：WS-D 进度条 + 按天分组 + 未读计数

**Files:** Modify `docs/feed.js`、`docs/feed.css`、`docs/feed.html`；Test `docs/test-feed.html`(扩)

- [ ] **Step 1: 扩测试** `docs/test-feed.html`：renderFeed 多天 items（含 date）后断言：容器内出现 `.feed-day-header`（按天分组标头）且数量=去重日期数；进度文本元素 `#feed-progress` 存在且含「共 N」；调 `window.FeedUI.markRead('d1')` 后 `localStorage` 键 `literature_feed_read` 含 'd1'。

- [ ] **Step 2: 运行确认失败** → `node /tmp/run_fe.js docs/test-feed.html`

- [ ] **Step 3: 实现**
(a) `docs/feed.html` 顶部加进度容器：在 `<nav id="cat-bar">` 后加 `<div id="feed-progress" class="feed-progress"></div>`。
(b) `docs/feed.js`：
- `READ_KEY='literature_feed_read'`；`getRead()/markRead(id)`（localStorage 读写，容错）。
- `renderFeed` 渲染时按 `item.date` 分组，在每组首张卡前插入 `<div class="feed-day-header">📅 {date}（共 n 篇）</div>`（普通块，非占满屏）。
- 进度：渲染后写 `#feed-progress` 文本 `已读 X / 共 M`；监听 `#feed` 的 `scroll`（节流）更新「第 N 篇」与已读（当前贴顶卡 markRead）。
- 暴露 `markRead`、`getRead` 到 `window.FeedUI`。

实现要点代码：
```javascript
  const READ_KEY = 'literature_feed_read';
  function getRead() { try { return JSON.parse(localStorage.getItem(READ_KEY) || '[]'); } catch (e) { return []; } }
  function markRead(id) {
    if (!id) return;
    const r = getRead(); if (r.indexOf(id) === -1) { r.push(id); try { localStorage.setItem(READ_KEY, JSON.stringify(r)); } catch (e) {} }
  }
  function updateProgress(total) {
    const p = document.getElementById('feed-progress'); if (!p) return;
    p.textContent = '已读 ' + getRead().length + ' / 共 ' + total + ' 篇';
  }
```
`renderFeed(items, container)` 改为：清空后按序遍历，`if (item.date !== lastDate)` 插日期标头；每张卡 append；末尾 `updateProgress(items.length)` + attach。卡 `id` 用 `item.doc_id || item.link`，进入视口时 `markRead`（可在 scroll 处理里对贴顶卡调 markRead + updateProgress）。
(c) `docs/feed.css`：
```css
.feed-progress{position:fixed;top:44px;left:0;right:0;z-index:9;font-size:12px;color:#5f6b7a;
  background:rgba(255,255,255,.92);padding:4px 12px;border-bottom:1px solid #eef2f7;}
.feed-day-header{scroll-snap-align:start;padding:10px 20px;font-weight:700;color:#1456b8;
  background:#f6f7f9;position:sticky;top:72px;z-index:8;}
```
（注意：日期标头不要给 `min-height:100vh`，避免占满一屏。）

- [ ] **Step 4: 运行确认通过** → `node /tmp/run_fe.js docs/test-feed.html`

- [ ] **Step 5: 提交**

```bash
git add docs/feed.js docs/feed.css docs/feed.html docs/test-feed.html
git commit -m "feat(feed): progress indicator + day grouping + unread tracking"
```

---

## Task 9：WS-E 显眼入口 + WS-G 日报→Feed 链接

**Files:** Modify `docs/index.html`、`generate_daily_pages.py`；Test `test_daily_pages_render.py`(扩)

- [ ] **Step 1: 写失败测试**（`render_deep_section` 应含 Feed 跳转链接）：

```python
def test_deep_section_has_feed_link():
    from generate_daily_pages import render_deep_section
    aps = [{"title": "T", "title_zh": "标题", "category": "AI×物理",
            "deep_analysis": "x", "poster": {"image": "images/posters/d1.webp", "elements": {"研究问题":"q"}},
            "link": "http://x", "doc_id": "d1"}]
    html = render_deep_section(aps, date="2026-05-28")
    assert "feed.html" in html and "在 Feed" in html
```
（注意：`render_deep_section` 需要接受 `date` 参数以构造 `../feed.html?date=...&doc=...`。若当前签名是 `render_deep_section(aps_items)`，本任务把它改为 `render_deep_section(aps_items, date="")` 并在调用处传 `day_str`；缺省 "" 时不输出日期参数，保证旧测试不破。）

- [ ] **Step 2: 运行确认失败** → `python3 run_tests.py test_daily_pages_render.py`

- [ ] **Step 3: 实现**
(a) `generate_daily_pages.py` `render_deep_section` 签名加 `date=""`，每卡 `src-link` 旁加：
```python
        feed_link = (f'<a class="to-feed" href="../feed.html?date={_safe(date)}&doc={_safe(a.get("doc_id",""))}">在 Feed 中查看 ↗</a>'
                     if date else "")
```
（`_safe` 用文件中已有的转义助手 `safe_text`；把 `feed_link` 拼进卡片 HTML，紧跟原文链接。）调用处 `render_deep_section(aps_items, date=day_str)`。
若 `render_core_section` 也要加，则同样传 date 并对每个 core item 用其 link 当 doc 锚（可选，本任务必做精读区，核心区为加分项）。
(b) `docs/index.html`：在 `</section>`(:104) 后、`.controls`(:106) 前插入显眼 hero：
```html
        <a class="feed-hero" href="feed.html">
          <div class="feed-hero-emoji">🔥</div>
          <div class="feed-hero-text">
            <div class="feed-hero-title">刷流模式 Feed</div>
            <div class="feed-hero-sub">一屏一篇 · 信息图秒懂 · 收藏点赞 · AI 交叉优先</div>
          </div>
          <div class="feed-hero-arrow">→</div>
        </a>
```
并在 `docs/style.css` 末尾加 `.feed-hero` 样式（大卡、渐变底、醒目）：
```css
.feed-hero{display:flex;align-items:center;gap:14px;margin:18px auto;max-width:880px;padding:16px 20px;
  border-radius:16px;background:linear-gradient(135deg,#1456b8,#0ea5b7);color:#fff;text-decoration:none;
  box-shadow:0 8px 28px rgba(20,86,184,.28);}
.feed-hero-emoji{font-size:30px;}
.feed-hero-title{font-size:18px;font-weight:800;}
.feed-hero-sub{font-size:13px;opacity:.92;margin-top:2px;}
.feed-hero-arrow{margin-left:auto;font-size:24px;font-weight:800;}
```
保留原 nav-link 里的 feed 链接（移除其"收藏点赞"描述即可，避免重复，可选）。

- [ ] **Step 4: 运行确认通过** → `python3 run_tests.py test_daily_pages_render.py`

- [ ] **Step 5: 提交**

```bash
git add docs/index.html docs/style.css generate_daily_pages.py test_daily_pages_render.py
git commit -m "feat(ui): prominent Feed hero entry + daily→Feed deep links"
```

---

## Task 10：集成 + workflow 适配 + 端到端验证 + 推送

**Files:** Modify `.github/workflows/generate-deep.yml`；运维

- [ ] **Step 1: workflow 适配** `.github/workflows/generate-deep.yml`：run_deep 步骤已有 `AI_TIMEOUT_SECONDS:600/AI_MAX_RETRIES:2/DEEP_WINDOW_DAYS/DEEP_MAX_NEW_PER_RUN`(若无显式则用代码默认)。无需 `DEEP_ENABLE_ARXIV_IMAGES`（已删）。确认 daily 步骤仍 `--force`。如需，给 run_deep 步骤显式加 `DEEP_MAX_NEW_PER_RUN: "14"`（覆盖 APS+T2 合计）。

- [ ] **Step 2: 全量本地测试**

Run: `python3 run_tests.py`（核心模块全过；已知 bs4/feedparser 缺失的 3 个本地失败属环境）
Run: `node /tmp/run_fe.js docs/test-feed.html docs/test-bookmarks.html docs/test-likes.html`（全 PASS）

- [ ] **Step 3: 凭据终检**

Run: 对改动文件逐个 grep 会话内真实凭据值，必须为空。

- [ ] **Step 4: 合并 main + 推送**

```bash
git checkout main && git merge --ff-only <feature-branch>   # 若在分支
git fetch origin main && git rebase origin/main             # 整合定时CI提交
git push <auth-url> main
```

- [ ] **Step 5: 先验证 1 张信息图**（CI dispatch，window 小）

```bash
gh/api dispatch generate-deep.yml -f window=4   # 或 REST API POST dispatches
```
跑完拉取，检查 `docs/images/posters/*.webp` 新图英文标签是否清晰可读（人工 Read 一张）。若乱码/不清，调 `build_infographic_prompt`（强化 "large legible English labels"）再跑。

- [ ] **Step 6: 端到端验收**

- `docs/data/feed.json`：`generated` 非 null；APS title_zh 覆盖率↑；arXiv 出现 `AI×物理/AI×化学·材料` category；link 均 http 开头；有 `daily_url`。
- 线上 `feed.html`：信息图清晰不被字盖、5 要素在图下、中文标题、⭐/❤️ 正确角标 + 右下 FAB、分类条 AI× 置顶、顶部进度、按天分组、深链跳转。
- 日报页：精读卡有「在 Feed 中查看 ↗」；首页有显眼 Feed hero。

- [ ] **Step 7: 触发正式 run + 收尾**

确认 cron 与手动 dispatch 正常；幂等多轮回填覆盖更多 tier2 文章。

---

## Self-Review
- **Spec 覆盖**：WS-A→T1；WS-H→T2；WS-C→T3；WS-B→T4；WS-F→T5；WS-D(卡片)→T6、(收藏/分类)→T7、(进度/分组)→T8；WS-E+WS-G→T9；workflow/E2E→T10；title_zh 中文标题→T1(extract)+T4(写入)+T6(前端用)。全覆盖。
- **占位符**：`<feature-branch>`/`<auth-url>` 为运维占位；其余步骤均含完整代码。
- **类型一致**：`extract_elements`→`{elements,elements_en,title_zh}`；`generate_poster`→ 增 `title_zh/elements_en`；`process_arxiv_tier2(date,candidates,provider,out_dir,max_workers,cache,max_new)→(list,int)` 与 `process_date` 同形；`normalize_link`/`build_feed(...daily_url)`/`build_core_export`/`build_tier2_candidates` 跨任务一致；前端 `applyDeepLink/markRead/getRead/buildElementsBlock/distinctCategories(排序)` 一致。
- **失败隔离**：所有 AI/IO 步骤 try/except 降级；预算+幂等守 CI 90min。
