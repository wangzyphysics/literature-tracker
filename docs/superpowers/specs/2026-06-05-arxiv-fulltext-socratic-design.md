# 设计：arxiv 全文苏格拉底深读（升级 AI 交叉/核心分析）

日期：2026-06-05
状态：已批准设计（待 spec review）

## 背景与动机

用户在 `daily/2026-06-04.html` 看到每篇文献只有「一句话亮点」，要求每篇都有**具体的分析**，并指明用之前 APS 全文用过的**苏格拉底提问 prompt**（`ai_prompts/deep_read.txt`：5 部分、逐章节冷凝、原文引述、创新评估）。

现状差距：
- **APS 全文**（tier 0）→ 完整苏格拉底 `deep_read()`。
- **AI 交叉 arxiv**（tier 1）→ 仅 `abstract_read()`（4 小节、**只读摘要**，且 tier2 候选里 abstract 常被截断到几十字符，分析很薄）。
- **普通 arxiv（~40 篇）→ 无分析**。
- 此外 `arxiv_core_2026-06-04.json` 当天尚未生成（run_deep 预算被前几天占用），所以该页 0 篇富化——这是叠加现象，但根因是 arxiv 分析太薄。

可行性勘察（已实测）：
- arxiv 原生 HTML `arxiv.org/html/<id>` 对新论文多为 404。
- `ar5iv.org/abs/<id>` 对**旧论文**有全文（2406.04520 → 40899 字符），对**很新论文**只返回摘要落地页（2606.04803 → 5537 字符占位）。
- `arxiv.org/pdf/<id>` **即时可得**（2606.04803 → 2.26MB，200）。仓库无 PDF 解析库。

## 关键决策（已与用户确认）

1. **覆盖范围**：只升级 **AI 交叉/核心（~20 篇/天）**，不做全部 60 篇。普通文章仍只有亮点。
2. **深度**：用与 APS 同一套完整苏格拉底 `deep_read.txt`。
3. **全文源（HTML 优先 + PDF 兜底）**：`arxiv.org/html` → `ar5iv.org` →（长度阈值过滤占位页）→ `arxiv.org/pdf` + `pdfminer.six` → 都失败退回摘要苏格拉底。
4. **预算**：`DEEP_MAX_NEW_PER_RUN` 14→24、workers 5→6，尽量当天走完；幂等缓存保证多轮不重复。

## 非目标（YAGNI）

- 不升级普通（非交叉）arxiv——仍只有亮点。
- 不改 APS 路径（已是全文苏格拉底）。
- 不抓 arxiv LaTeX 源 / 不做语义清洗（PDF 文本带公式/参考文献噪声可接受）。
- 不改日报单列表结构（`render_unified_item` 已展示 `deep_analysis`，长文本自然流入 `<details>`）。

## 架构与数据流

```
tier2 候选(data/arxiv_tier2_<date>.json)
  → run_deep._enrich_arxiv_tier2_one(cand):
       arxiv_fulltext.fetch_fulltext(link) → (text, mode)
       text 有 → deep_read(meta, text)  [苏格拉底], analysis_mode=html|pdf
       text 无 → abstract_read(abs)      [兜底], analysis_mode=abstract, ft_attempts++
       生成/复用 poster(信息图+5要素)
  → data/arxiv_core_<date>.json (deep_analysis/image/poster_elements/analysis_mode/ft_attempts)
  → 日报渲染(render_unified_item) <details> 内展示信息图+5要素+深析正文(markdown→HTML)
```

## 组件改动

### 1. 新模块 `arxiv_fulltext.py`

纯函数 + 受控网络层，便于本地无网测试。

- `arxiv_id(link) -> str`：从 `arxiv.org/{abs,pdf,html}/<id>(vN)?` 解析 ID；兼容裸 `YYMM.NNNNN` 与旧式 `archive/NNNNNNN`。无法解析 → `""`。
- `html_to_text(html) -> str`：stdlib `html.parser.HTMLParser` 子类，跳过 `script/style/nav/header/footer/noscript`，收集可见文本，压缩空白。
- `extract_pdf_text(pdf_bytes) -> str`：`from pdfminer.high_level import extract_text`（import 失败/解析失败 → `""`，静默降级）。
- `_get_text(url)` / `_get_bytes(url)`：`requests.get` 带 `User-Agent`、`timeout=30`、`allow_redirects`；失败 → `None`。**测试通过 monkeypatch 这两个函数注入内容，不触网。**
- `fetch_fulltext(link, max_chars=40000, min_chars=4000) -> (text, mode)`：
  1. 依次试 `https://arxiv.org/html/<id>`、`https://ar5iv.org/abs/<id>`：`html_to_text` 后**长度 ≥ min_chars** 才接受（拒绝摘要占位页），返回 `(text[:max_chars], "html")`。
  2. 否则下 `https://arxiv.org/pdf/<id>`：`extract_pdf_text` 后 ≥ min_chars 返回 `(text[:max_chars], "pdf")`。
  3. 都不行 → `("", "")`。

### 2. `run_deep.py` 接线

- **新增 `_tier2_complete(rec) -> bool`**（替代 `process_arxiv_tier2` 里对 `_deep_complete_abstract` 的调用，改为传整条 rec）：
  ```python
  def _tier2_complete(rec):
      if not rec: return False
      text = rec.get("deep_analysis") or ""
      if not text: return False
      attempts = int(rec.get("ft_attempts") or 0)
      mode = rec.get("analysis_mode") or "abstract"
      # 拿到真正全文苏格拉底 → 完成
      if mode in ("html", "pdf") and ("创新" in text) and len(text) >= 3000:
          return True
      # 否则继续尝试升级全文；attempts 封顶避免无限重处理（HTML-less 论文最终接受摘要版）
      if attempts >= 3 and ("创新" in text) and len(text) >= 120:
          return True
      return False
  ```
  说明：旧缓存记录无 `analysis_mode`/`ft_attempts` → 视为未完成 → 后续轮自动尝试升级为全文；连续 3 次拿不到全文则接受摘要版定稿。

- **改 `_enrich_arxiv_tier2_one(cand, provider, out_dir, cached=None)`**：
  ```python
  def _enrich_arxiv_tier2_one(cand, provider, out_dir, cached=None):
      if cached and _tier2_complete(cached):
          return cached
      import hashlib
      from arxiv_fulltext import fetch_fulltext
      rec = dict(cand); rec["source"] = "arxiv"
      rec["category"] = cand.get("category") or classify(cand, provider=provider)
      doc_id = "ax" + hashlib.sha1((cand.get("link") or cand.get("title","")).encode("utf-8")).hexdigest()[:14]
      meta = {"title": cand.get("title",""), "authors": cand.get("authors"),
              "year": cand.get("year"), "doc_id": doc_id}
      fulltext, mode = fetch_fulltext(cand.get("link") or "")
      prev_attempts = int((cached or {}).get("ft_attempts") or 0)
      if fulltext:
          rec["deep_analysis"] = deep_read(meta, fulltext, provider=provider)
          rec["analysis_mode"] = mode
          poster_src = fulltext
      else:
          abs_txt = cand.get("abstract") or cand.get("summary") or ""
          rec["deep_analysis"] = abstract_read(cand, abs_txt, provider=provider) if abs_txt else ""
          rec["analysis_mode"] = "abstract"
          poster_src = abs_txt
      rec["ft_attempts"] = prev_attempts + 1          # 每次处理都自增 → 封顶重试
      poster = (cached or {}).get("poster") or (
          generate_poster(meta, poster_src, provider=provider, out_dir=out_dir) if poster_src else None)
      rec["poster"] = poster
      rec["image"] = (poster or {}).get("image")
      rec["poster_elements"] = (poster or {}).get("elements")
      if poster and poster.get("title_zh") and not rec.get("title_zh"):
          rec["title_zh"] = poster["title_zh"]
      return rec
  ```
- `process_arxiv_tier2`：把分流判断 `_deep_complete_abstract(prev.get("deep_analysis"))` 改为 `_tier2_complete(prev)`。其余（预算/overflow/并发）不变。
- `main()` tier-2 循环：`max_new=budget`、workers 从 env `DEEP_WORKERS` 读（默认 6）。

### 3. 依赖 + CI

- `requirements.txt` 增 `pdfminer.six>=20221105`。
- `.github/workflows/generate-deep.yml` run_deep 步骤 env 增：`DEEP_MAX_NEW_PER_RUN: "24"`、`DEEP_WORKERS: "6"`。CI `timeout-minutes` 保持 90；幂等多轮兜底。

### 4. 深析正文 markdown 渲染（可读性，小幅）

全文苏格拉底输出长（每篇 5-10KB，含 `##` 标题/`**粗体**/`- 列表`）。当前 `deep-body` 是 `white-space:pre-wrap` 原样显示，字面 `##` 难读。新增 `generate_daily_pages.py` 纯函数 `md_to_html(text) -> str`（stdlib，仅支持：`#/##/###` 标题、`**粗体**`、`- `/`数字. ` 列表、空行分段；其余 `safe_text` 转义）。`render_unified_item` 的 `deep-body` 用 `md_to_html(deep)` 替代 `safe_text(deep)`；移除 `.deep-body{white-space:pre-wrap}`。**安全**：先对每行 `safe_text` 再套白名单标签，杜绝注入。

## 测试

| 测试 | 验证 |
|---|---|
| `test_arxiv_fulltext.py`（新，stdlib） | `arxiv_id` 解析 abs/pdf/html/带版本/裸 ID/旧式；`html_to_text` 去 script/style 取正文；`fetch_fulltext` 顺序：HTML 命中→`html`；HTML 太短→落 PDF→`pdf`；全失败→`("","")`；min_chars 拒绝占位页（均 monkeypatch `_get_text`/`_get_bytes`，不触网） |
| `test_run_deep.py`（扩展） | `_tier2_complete`：全文模式+创新+≥3000→True；摘要模式 attempts<3→False，attempts≥3→True；旧记录(无 mode/attempts)→False(待升级)。`_enrich_arxiv_tier2_one`：monkeypatch `fetch_fulltext` 返回全文→走 `deep_read`、mode=html；返回空→`abstract_read`、mode=abstract、ft_attempts 自增。`process_arxiv_tier2` 用 `_tier2_complete` 分流、预算不变 |
| `test_daily_pages_render.py`（扩展） | `md_to_html`：`##` →`<h*>`、`**x**`→`<strong>`、`- a`→`<li>`、转义 `<script>`；`render_unified_item` 富化项 deep-body 含 `<h`/`<strong>` 而非字面 `##` |
| PDF 提取（pdfminer） | 仅 CI 验证（本地无 pip）。run_deep 跑真实论文时产出 mode=pdf 的全文深析 |

本地：`python3 run_tests.py`（stdlib）。pdfminer/bs4/feedparser 相关本地缺包失败属已知，不视为回归。

## 受影响文件清单

| 文件 | 改动 |
|---|---|
| `arxiv_fulltext.py` | 新建（ID 解析 + HTML/PDF 抓取 + 全文获取编排） |
| `run_deep.py` | `_tier2_complete`；`_enrich_arxiv_tier2_one` 改用 fetch_fulltext+deep_read；`process_arxiv_tier2` 分流；workers 读 env |
| `generate_daily_pages.py` | `md_to_html`；`render_unified_item` deep-body 用 md_to_html；去 pre-wrap |
| `requirements.txt` | 加 `pdfminer.six` |
| `.github/workflows/generate-deep.yml` | env 加 DEEP_MAX_NEW_PER_RUN=24 / DEEP_WORKERS=6 |
| `test_arxiv_fulltext.py` `test_run_deep.py` `test_daily_pages_render.py` | 新增/扩展 |

## 验证方式

1. 本地 `python3 run_tests.py` 全绿（pdfminer/bs4/feedparser 本地缺包除外）。
2. 触发 generate-deep，确认 `arxiv_core_<date>.json` 出现 `analysis_mode` in (html,pdf) 的记录、`deep_analysis` ≥3000 字含「第五部分：创新评估」。
3. 线上日报某 AI 交叉条目展开：信息图 + 5 要素 + **结构化苏格拉底深析**（标题/粗体/逐章节），非一句话亮点。
4. 旧缓存的摘要版条目在后续轮升级为全文版（mode 变 html/pdf）。

## 安全

APS 凭据不涉及。arxiv/ar5iv 为公开源，带 User-Agent、超时、礼貌；`md_to_html` 先转义后套白名单标签，防注入。
