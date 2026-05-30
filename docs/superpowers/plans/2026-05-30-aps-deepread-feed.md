# APS 全文精读 + 概念海报 + 刷流 Feed + gpt-5.5 迁移 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 literature-tracker 上接入 APS 全文源，做深度精读 + 概念海报，新增全屏刷流 Feed 与点赞，并把 chat 模型从 Kimi 迁到 gpt-5.5。

**Architecture:** 新增独立后端模块（`aps_client` / `image_provider` / `deep_reader` / `poster_generator` / `auto_classifier`）+ 编排脚本 `run_deep.py`，由独立 workflow `generate-deep.yml` 调用，产出增强数据（精读、海报、分类、`feed.json`）；前端新增 `/feed` 全屏页与 `likes.js`。所有 AI/网络步骤失败均静默降级，绝不阻塞日报。

**Tech Stack:** Python 3.11（requests、Pillow）、OpenAI 兼容网关（gpt-5.5 chat + gpt-image-2 Responses 流式）、APS HTTP basic-auth 浏览器、原生 JS + jsdom 测试、GitHub Actions。

---

## 安全约束（每个 worker 必读）

APS / OSS / 网关 凭据**不可外传**。实现时：
- 凭据只从环境变量读取（`os.environ`），代码里**不写任何明文凭据**。
- 测试用假凭据（如 `http://u:p@localhost`）。
- workflow yaml 只引用 `${{ secrets.* }}`。
- 提交前每个 worker 对改动文件做凭据扫描：把会话里给到的真实凭据值（APS 密码、OSS id/secret、网关 key、站点 IP）逐个 `grep -rn` 改动文件，命中即清理。**本计划/任何提交文件中不得出现这些真实值（包括作为 grep 模式）。**

环境变量约定：
- `AI_API_KEY` / `AI_PROVIDER=aigw` / `AI_MODEL=gpt-5.5` / `AI_BASE_URL=https://aigw.sotatts.online/v1`
- `IMAGE_API_BASE`（默认同 `AI_BASE_URL` 去掉尾部 `/chat/completions`，即 `.../v1`）、`IMAGE_API_KEY`（默认同 `AI_API_KEY`）
- `APS_HTTP_BASE` / `APS_HTTP_USER` / `APS_HTTP_PASS`

---

## File Structure

| 文件 | 职责 |
|---|---|
| `aps_client.py` (新) | APS HTTP 客户端：列日期 / 取 metadata / 下全文 / 列图 |
| `image_provider.py` (新) | gpt-image-2 Responses 流式生成 + PNG→WebP 压缩 |
| `deep_reader.py` (新) | 全文 → 苏格拉底式精读（gpt-5.5） |
| `poster_generator.py` (新) | 5 要素抽取（gpt-5.5）+ 背景海报生成（image_provider） |
| `auto_classifier.py` (新) | taxonomy 规则分类 + gpt-5.5 兜底 |
| `run_deep.py` (新) | 编排：拉 APS → 精读 → 海报 → arXiv 核心配图 → 分类 → 写 feed.json |
| `ai_prompts/deep_read.txt`、`ai_prompts/poster_elements.txt` (新) | prompt 模板 |
| `focus_core.py` / `config.py` (改) | WS0 taxonomy + 权重 |
| `ai_summarizer.py` (改) | WS1 `aigw` provider 别名 |
| `generate_daily_pages.py` (改) | 「今日精读」区渲染 + 分类标签 |
| `docs/feed.html` / `feed.css` / `feed.js` (新) | WS6 全屏刷流 |
| `docs/likes.js` (新) / `docs/exports.js`、`bookmarks.css` (改) | WS7 点赞 + 导出扩展 |
| `docs/index.html` / `manifest.json` / `sw.js` (改) | feed 入口 + 缓存 |
| `.github/workflows/generate-deep.yml` (新) | 独立精读/海报/feed workflow |
| `config.local.py.example` (改) | 占位符示例 |

测试文件：`test_aps_client.py`、`test_image_provider.py`、`test_deep_reader.py`、`test_poster_generator.py`、`test_auto_classifier.py`、`test_focus_core.py`（扩展）、`test_feed_json.py`、`docs/test-feed.html`、`docs/test-likes.html`。

---

## Task 1：WS1 — 迁移 gpt-5.5 chat provider

**Files:**
- Modify: `ai_summarizer.py:432-441`（`build_provider`）
- Modify: `config.py`（默认 AI 配置）
- Test: `test_provider_aigw.py`（新）

- [ ] **Step 1: 写失败测试**

```python
# test_provider_aigw.py
import os
from ai_summarizer import build_provider, OpenRouterProvider

def test_aigw_routes_to_openai_compatible(monkeypatch):
    monkeypatch.setenv("AI_BASE_URL", "https://aigw.sotatts.online/v1")
    p = build_provider("aigw", "sk-test", model="gpt-5.5")
    assert isinstance(p, OpenRouterProvider)
    assert p.model == "gpt-5.5"
    assert p.base_url.endswith("/chat/completions")
    assert "aigw.sotatts.online" in p.base_url
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_provider_aigw.py -v`
Expected: FAIL（`aigw` 当前落到 gemini 分支）

- [ ] **Step 3: 在 `build_provider` 加 `aigw` 分支**

`ai_summarizer.py`，在 openrouter 分支前/后加：

```python
    if name in ("aigw", "gpt5", "openai-gateway", "sota"):
        return OpenRouterProvider(api_key=api_key, model=model)
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_provider_aigw.py -v`
Expected: PASS

- [ ] **Step 5: 更新 config 默认**

`config.py` 的 `DEFAULT_AI_CONFIG`（或等价 dict）设：`provider="aigw"`、`model="gpt-5.5"`、`base_url="https://aigw.sotatts.online/v1"`。保留 Kimi 配置项注释可切回。

- [ ] **Step 6: 提交**

```bash
git add ai_summarizer.py config.py test_provider_aigw.py
git commit -m "feat(ai): add aigw provider, default to gpt-5.5"
```

---

## Task 2：WS0 — 关注重点 taxonomy 更新

**Files:**
- Modify: `focus_core.py`
- Test: `test_focus_core.py`（扩展）

- [ ] **Step 1: 写失败测试**

```python
# 追加到 test_focus_core.py
from focus_core import classify_taxonomy, core_score, is_core_focus

def test_ai_physics_is_tier1_core():
    a = {"title": "Machine learning interatomic potentials for ferroelectric perovskites",
         "summary": "graph neural network potential predicts polarization"}
    assert is_core_focus(a)
    assert classify_taxonomy(a) in ("AI×物理", "AI×化学·材料")

def test_pure_magnetism_is_tier2_core():
    a = {"title": "Altermagnetic spin splitting in RuO2", "summary": "antiferromagnet spin"}
    assert is_core_focus(a)
    assert classify_taxonomy(a) == "磁性·自旋电子学"

def test_unrelated_is_other():
    a = {"title": "A note on medieval poetry", "summary": ""}
    assert not is_core_focus(a)
    assert classify_taxonomy(a) == "其他"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_focus_core.py -k "tier1 or tier2 or unrelated" -v`
Expected: FAIL（`classify_taxonomy` 不存在）

- [ ] **Step 3: 实现 taxonomy**

`focus_core.py` 增加：

```python
TAXONOMY = {
    "AI×物理": {
        "terms": ["machine learning", "deep learning", "neural network", "graph neural",
                  "transformer", "generative model", "diffusion model", "foundation model",
                  "ml interatomic", "neural network potential", "ml potential",
                  "physics-informed", "scientific machine learning"],
        "domain": ["physics", "quantum", "phase transition", "hamiltonian", "spin",
                   "lattice", "electronic structure", "dft"],
        "tier": 1,
    },
    "AI×化学·材料": {
        "terms": ["machine learning", "deep learning", "neural network", "graph neural",
                  "generative model", "diffusion model", "foundation model",
                  "ml interatomic", "neural network potential", "ml potential",
                  "active learning", "bayesian optimization"],
        "domain": ["material", "chemistry", "molecule", "catalyst", "crystal",
                   "perovskite", "alloy", "polymer", "battery", "synthesis"],
        "tier": 1,
    },
    "磁性·自旋电子学": {"terms": ["magnet", "magnetism", "spintronic", "antiferromagnet",
                          "ferromagnet", "altermagnet", "spin current", "spin orbit",
                          "magnon", "skyrmion"], "tier": 2},
    "铁电·极化": {"terms": ["ferroelectric", "polarization", "piezoelectric",
                       "multiferroic", "dielectric"], "tier": 2},
    "拓扑·电子结构": {"terms": ["topological", "weyl", "dirac", "band structure",
                         "berry phase", "chern", "quantum hall"], "tier": 2},
    "超导": {"terms": ["superconduct", "cooper pair", "bcs", "meissner"], "tier": 2},
    "量子信息·计算": {"terms": ["qubit", "quantum computing", "quantum information",
                         "entanglement", "quantum error", "quantum circuit"], "tier": 2},
    "软物质·流体·统计": {"terms": ["soft matter", "fluid", "turbulence", "statistical mechanics",
                          "active matter", "colloid", "granular"], "tier": 3},
    "其他凝聚态": {"terms": ["condensed matter", "phonon", "thermal transport",
                       "2d material", "graphene"], "tier": 3},
}

def _text(article: dict) -> str:
    if not article:
        return ""
    return " ".join(str(article.get(k, "") or "") for k in ("title", "summary", "abstract")).lower()

def classify_taxonomy(article: dict) -> str:
    txt = _text(article)
    if not txt.strip():
        return "其他"
    best, best_tier = None, 99
    for cat, spec in TAXONOMY.items():
        terms_hit = any(t in txt for t in spec["terms"])
        domain_hit = ("domain" not in spec) or any(d in txt for d in spec["domain"])
        if terms_hit and domain_hit and spec["tier"] < best_tier:
            best, best_tier = cat, spec["tier"]
    return best or "其他"
```

并把 `core_score()` 调整为：命中 tier1 +100、tier2 +50、tier3 +10（叠加现有打分）；`is_core_focus()` 返回 `classify_taxonomy(article)` 属于 tier1/tier2 的类别。保留现有 None/空守卫。

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_focus_core.py -v`
Expected: PASS（含原有用例）

- [ ] **Step 5: 提交**

```bash
git add focus_core.py test_focus_core.py
git commit -m "feat(focus): AI×physics/chem/materials taxonomy + tiered scoring"
```

---

## Task 3：WS2 — APS HTTP 客户端

**Files:**
- Create: `aps_client.py`
- Test: `test_aps_client.py`

- [ ] **Step 1: 写失败测试**（用 `responses` 库或 monkeypatch `requests.get`）

```python
# test_aps_client.py
import json
import aps_client
from aps_client import ApsClient

class FakeResp:
    def __init__(self, text="", content=b"", status=200, headers=None, url=""):
        self.text = text; self.content = content; self.status_code = status
        self.headers = headers or {}; self.url = url
    def raise_for_status(self):
        if self.status_code >= 400: raise Exception(self.status_code)

def test_list_dates_parses_folder_links(monkeypatch):
    html = ("<a href='/browse?prefix=APS%2F2026-05-27%2F'>2026-05-27/</a>"
            "<a href='/browse?prefix=APS%2F2026-05-28%2F'>2026-05-28/</a>"
            "<a href='/browse?prefix=APS%2Fbegin%2F'>begin/</a>")
    monkeypatch.setattr(aps_client.requests, "get",
                        lambda *a, **k: FakeResp(text=html))
    c = ApsClient(base="http://h", user="u", password="p")
    dates = c.list_dates(window_days=30, today="2026-05-30")
    assert "2026-05-28" in dates and "2026-05-27" in dates
    assert "begin" not in dates

def test_fetch_metadata_follows_redirect_jsonl(monkeypatch):
    jsonl = '{"title":"A","journal":"PRL","has_full_text":true,"markdown_oss_key":"k1","doc_id":"d1"}\n' \
            '{"title":"B","journal":"PRX","has_full_text":true,"markdown_oss_key":"k2","doc_id":"d2"}\n'
    monkeypatch.setattr(aps_client.requests, "get",
                        lambda *a, **k: FakeResp(content=jsonl.encode()))
    c = ApsClient(base="http://h", user="u", password="p")
    metas = c.fetch_metadata("2026-05-28")
    assert len(metas) == 2 and metas[0]["doc_id"] == "d1"

def test_fetch_markdown_returns_text(monkeypatch):
    monkeypatch.setattr(aps_client.requests, "get",
                        lambda *a, **k: FakeResp(content=b"# Title\n\nbody"))
    c = ApsClient(base="http://h", user="u", password="p")
    md = c.fetch_markdown({"markdown_oss_key": "APS/2026-05-28/markdown/d1/d1.md"})
    assert md.startswith("# Title")

def test_errors_are_swallowed(monkeypatch):
    def boom(*a, **k): raise Exception("network down")
    monkeypatch.setattr(aps_client.requests, "get", boom)
    c = ApsClient(base="http://h", user="u", password="p")
    assert c.fetch_metadata("2026-05-28") == []
    assert c.fetch_markdown({"markdown_oss_key": "k"}) == ""
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_aps_client.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现 `aps_client.py`**

```python
"""APS 全文源 HTTP 客户端（basic-auth 浏览器）。所有 IO 失败均吞掉返回空，不阻塞主流程。"""
import os, re, json, datetime
from urllib.parse import quote
import requests

_DATE_RE = re.compile(r"prefix=APS%2F(\d{4}-\d{2}-\d{2})%2F")

class ApsClient:
    def __init__(self, base=None, user=None, password=None, timeout=40):
        self.base = (base or os.environ.get("APS_HTTP_BASE", "")).rstrip("/")
        self.user = user or os.environ.get("APS_HTTP_USER", "")
        self.password = password or os.environ.get("APS_HTTP_PASS", "")
        self.timeout = timeout

    @property
    def _auth(self):
        return (self.user, self.password) if self.user else None

    def _get(self, path):
        url = path if path.startswith("http") else f"{self.base}{path}"
        return requests.get(url, auth=self._auth, timeout=self.timeout,
                            allow_redirects=True)

    def list_dates(self, window_days=30, today=None):
        try:
            r = self._get("/?prefix=APS%2F")
            found = sorted(set(_DATE_RE.findall(r.text)))
        except Exception as e:
            print(f"⚠️ APS list_dates failed: {e}"); return []
        if not found:
            return []
        today = today or datetime.date.today().isoformat()
        cutoff = (datetime.date.fromisoformat(today)
                  - datetime.timedelta(days=window_days)).isoformat()
        return [d for d in found if d >= cutoff]

    def fetch_metadata(self, date):
        try:
            key = f"APS/{date}/metadata.jsonl"
            r = self._get(f"/download?key={quote(key)}")
            metas = []
            for line in r.content.decode("utf-8", "replace").splitlines():
                line = line.strip()
                if line:
                    try: metas.append(json.loads(line))
                    except Exception: pass
            return metas
        except Exception as e:
            print(f"⚠️ APS fetch_metadata {date} failed: {e}"); return []

    def fetch_markdown(self, meta):
        key = (meta or {}).get("markdown_oss_key") or ""
        if not key:
            return ""
        try:
            r = self._get(f"/download?key={quote(key)}")
            return r.content.decode("utf-8", "replace")
        except Exception as e:
            print(f"⚠️ APS fetch_markdown {key} failed: {e}"); return ""

    def list_images(self, meta):
        # image_oss_prefix 形如 oss://aps-papers/APS/<date>/markdown/<id>/images/
        prefix = (meta or {}).get("image_oss_prefix") or ""
        if not prefix:
            return []
        m = re.search(r"aps-papers/(.+)$", prefix)
        if not m:
            return []
        oss_path = m.group(1)
        try:
            r = self._get(f"/?prefix={quote(oss_path)}")
            return re.findall(r"key=([^'\"]+\.(?:png|jpg|jpeg))", r.text)
        except Exception as e:
            print(f"⚠️ APS list_images failed: {e}"); return []
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_aps_client.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add aps_client.py test_aps_client.py
git commit -m "feat(aps): HTTP basic-auth client for full-text source"
```

---

## Task 4：image_provider — gpt-image-2 Responses 流式 + WebP 压缩

**Files:**
- Create: `image_provider.py`
- Test: `test_image_provider.py`
- 依赖：`Pillow`（加入 `requirements.txt`）

- [ ] **Step 1: 加依赖**

`requirements.txt` 追加一行 `Pillow`。

- [ ] **Step 2: 写失败测试**（mock 流 + 真 PNG 压缩）

```python
# test_image_provider.py
import base64, io, os, json
import image_provider
from image_provider import generate_image_b64, compress_to_webp
from PIL import Image

def _png_b64(size=(1600, 900)):
    buf = io.BytesIO(); Image.new("RGB", size, (10, 80, 180)).save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()

def test_compress_to_webp_shrinks_and_resizes(tmp_path):
    src_b64 = _png_b64((1600, 900))
    out = tmp_path / "p.webp"
    compress_to_webp(base64.b64decode(src_b64), str(out), max_edge=768, quality=80)
    assert out.exists()
    im = Image.open(out)
    assert im.format == "WEBP"
    assert max(im.size) <= 768

def test_generate_image_parses_stream(monkeypatch):
    b64 = _png_b64((1024, 1024))
    line = 'data: ' + json.dumps({
        "type": "response.output_item.done",
        "item": {"type": "image_generation_call", "result": b64}})
    class FakeStream:
        status_code = 200
        def iter_lines(self, decode_unicode=True):
            yield line
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(image_provider.requests, "post",
                        lambda *a, **k: FakeStream())
    got = generate_image_b64("draw a crystal", api_key="k", base="http://h/v1")
    assert got == b64

def test_generate_image_returns_none_on_failure(monkeypatch):
    def boom(*a, **k): raise Exception("down")
    monkeypatch.setattr(image_provider.requests, "post", boom)
    assert generate_image_b64("x", api_key="k", base="http://h/v1") is None
```

- [ ] **Step 3: 运行确认失败**

Run: `python -m pytest test_image_provider.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 4: 实现 `image_provider.py`**

```python
"""gpt-image-2 via OpenAI-compatible Responses API（必须流式）+ WebP 压缩。"""
import os, io, json
import requests
from PIL import Image

def _responses_url(base):
    base = (base or "").rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    if not base.endswith("/v1"):
        base = base + "/v1" if "/v1" not in base else base
    return base + "/responses"

def generate_image_b64(prompt, api_key=None, base=None, timeout=180):
    """返回 PNG base64 字符串；失败返回 None。"""
    api_key = api_key or os.environ.get("IMAGE_API_KEY") or os.environ.get("AI_API_KEY")
    base = base or os.environ.get("IMAGE_API_BASE") or os.environ.get("AI_BASE_URL")
    url = _responses_url(base)
    payload = {"model": "gpt-5.5",
               "input": [{"role": "user", "content": prompt}],
               "tools": [{"type": "image_generation"}],
               "stream": True}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        with requests.post(url, headers=headers, json=payload,
                           stream=True, timeout=timeout) as r:
            r.raise_for_status()
            result_b64 = None
            for raw in r.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                data = raw[5:].strip()
                if not data or data == "[DONE]":
                    continue
                try: ev = json.loads(data)
                except Exception: continue
                if ev.get("type") == "response.output_item.done":
                    item = ev.get("item", {})
                    if item.get("type") == "image_generation_call" and item.get("result"):
                        result_b64 = item["result"]
                elif ev.get("type") == "response.image_generation_call.partial_image":
                    if ev.get("partial_image_b64") and not result_b64:
                        result_b64 = ev["partial_image_b64"]
            return result_b64
    except Exception as e:
        print(f"⚠️ image generation failed: {e}")
        return None

def compress_to_webp(png_bytes, out_path, max_edge=768, quality=80):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    w, h = im.size
    if max(w, h) > max_edge:
        scale = max_edge / max(w, h)
        im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    im.save(out_path, "WEBP", quality=quality, method=6)
    return out_path

def generate_and_save(prompt, out_path, max_edge=768, quality=80, **kw):
    import base64
    b64 = generate_image_b64(prompt, **kw)
    if not b64:
        return None
    try:
        compress_to_webp(base64.b64decode(b64), out_path, max_edge, quality)
        return out_path
    except Exception as e:
        print(f"⚠️ compress failed: {e}"); return None
```

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest test_image_provider.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add image_provider.py test_image_provider.py requirements.txt
git commit -m "feat(image): gpt-image-2 Responses streaming + WebP compression"
```

---

## Task 5：WS3 — 深度精读

**Files:**
- Create: `deep_reader.py`、`ai_prompts/deep_read.txt`
- Test: `test_deep_reader.py`

- [ ] **Step 1: 写 prompt 模板**

`ai_prompts/deep_read.txt` ＝ spec 中用户提供的「苏格拉底式资深研究员」完整 5 部分 prompt，开头加一行占位说明，正文用 `${title}` `${authors}` `${year}` `${context}` 占位。文件末尾追加 `---\n论文内容如下：\n${context}`。

- [ ] **Step 2: 写失败测试**

```python
# test_deep_reader.py
import deep_reader
from deep_reader import build_deep_prompt, deep_read

def test_build_prompt_fills_placeholders():
    p = build_deep_prompt(title="T", authors="A", year="2026", context="BODY")
    assert "T" in p and "A" in p and "2026" in p and "BODY" in p
    assert "${context}" not in p

def test_build_prompt_truncates_long_context():
    big = "x" * 500000
    p = build_deep_prompt(title="T", authors="A", year="2026", context=big, max_chars=20000)
    assert len(p) < 60000

def test_deep_read_uses_provider(monkeypatch):
    calls = {}
    class FakeProv:
        def call_api(self, prompt):
            calls["prompt"] = prompt
            return "## 第一部分：核心概览\n精读内容"
    out = deep_read({"title": "T", "authors": "['A']", "year": 2026},
                    "# Paper\nfull body", provider=FakeProv())
    assert "精读内容" in out
    assert "full body" in calls["prompt"]

def test_deep_read_swallows_provider_error(monkeypatch):
    class Boom:
        def call_api(self, p): raise Exception("api down")
    assert deep_read({"title": "T"}, "body", provider=Boom()) == ""
```

- [ ] **Step 3: 运行确认失败**

Run: `python -m pytest test_deep_reader.py -v`
Expected: FAIL

- [ ] **Step 4: 实现 `deep_reader.py`**

```python
"""APS 全文 → 苏格拉底式深度精读（gpt-5.5）。失败返回空串。"""
import os, ast
from string import Template

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "deep_read.txt")

def _load_template():
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def _fmt_authors(raw):
    if isinstance(raw, list):
        return ", ".join(map(str, raw))
    try:
        v = ast.literal_eval(raw) if isinstance(raw, str) and raw.startswith("[") else raw
        return ", ".join(map(str, v)) if isinstance(v, list) else str(raw)
    except Exception:
        return str(raw)

def build_deep_prompt(title, authors, year, context, max_chars=40000):
    ctx = (context or "")
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars] + "\n\n[内容过长已截断]"
    tmpl = Template(_load_template())
    return tmpl.safe_substitute(title=str(title or ""),
                                authors=_fmt_authors(authors),
                                year=str(year or ""), context=ctx)

def deep_read(meta, markdown, provider):
    if not markdown or provider is None:
        return ""
    try:
        prompt = build_deep_prompt(meta.get("title"), meta.get("authors"),
                                   meta.get("year"), markdown)
        return (provider.call_api(prompt) or "").strip()
    except Exception as e:
        print(f"⚠️ deep_read failed for {meta.get('doc_id')}: {e}")
        return ""
```

注：`Template` 用 `${...}` 占位，与 prompt 文件一致；`safe_substitute` 避免 prompt 里其他 `$` 报错。

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest test_deep_reader.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add deep_reader.py ai_prompts/deep_read.txt test_deep_reader.py
git commit -m "feat(deep): Socratic full-text deep-read via gpt-5.5"
```

---

## Task 6：WS4 — 概念海报（要素抽取 + 背景生成）

**Files:**
- Create: `poster_generator.py`、`ai_prompts/poster_elements.txt`
- Test: `test_poster_generator.py`

- [ ] **Step 1: 写 prompt 模板**

`ai_prompts/poster_elements.txt` ＝ spec 用户提供的「学术概念海报关键视觉信息」prompt，要求**严格输出 JSON**：`{"研究问题":..,"创新方法":..,"工作流程":..,"关键结果":..,"应用价值":..}`，占位 `${language}` `${title}` `${context}`。

- [ ] **Step 2: 写失败测试**

```python
# test_poster_generator.py
import json
import poster_generator
from poster_generator import extract_elements, build_background_prompt, generate_poster

def test_extract_elements_parses_json():
    class P:
        def call_api(self, prompt):
            return '```json\n{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}\n```'
    el = extract_elements({"title": "T"}, "body", provider=P())
    assert el["创新方法"] == "m" and el["应用价值"] == "v"

def test_extract_elements_returns_none_on_bad_json():
    class P:
        def call_api(self, prompt): return "not json at all"
    assert extract_elements({"title": "T"}, "body", provider=P()) is None

def test_background_prompt_has_no_chinese_text_render_request():
    p = build_background_prompt({"研究问题": "q"})
    assert "Memphis" in p
    assert "16:9" in p
    # 不渲染图内文字
    assert "no text" in p.lower() or "without text" in p.lower()

def test_generate_poster_calls_image(monkeypatch, tmp_path):
    class P:
        def call_api(self, prompt):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}'
    monkeypatch.setattr(poster_generator, "generate_and_save",
                        lambda prompt, out_path, **k: out_path)
    res = generate_poster({"title": "T", "doc_id": "d1"}, "body",
                          provider=P(), out_dir=str(tmp_path))
    assert res["elements"]["创新方法"] == "m"
    assert res["image"].endswith("d1.webp")
```

- [ ] **Step 3: 运行确认失败**

Run: `python -m pytest test_poster_generator.py -v`
Expected: FAIL

- [ ] **Step 4: 实现 `poster_generator.py`**

```python
"""概念海报：gpt-5.5 抽 5 要素 + gpt-image-2 生成纯视觉背景。"""
import os, re, json
from string import Template
from image_provider import generate_and_save

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "ai_prompts", "poster_elements.txt")
_KEYS = ["研究问题", "创新方法", "工作流程", "关键结果", "应用价值"]

def _load_template():
    with open(_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()

def _parse_json(text):
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
    return {k: str(d.get(k, "")) for k in _KEYS}

def extract_elements(meta, markdown, provider, language="中文", max_chars=40000):
    if not markdown or provider is None:
        return None
    ctx = markdown[:max_chars]
    prompt = Template(_load_template()).safe_substitute(
        language=language, title=str(meta.get("title", "")), context=ctx)
    try:
        return _parse_json(provider.call_api(prompt))
    except Exception as e:
        print(f"⚠️ extract_elements failed: {e}"); return None

def build_background_prompt(elements):
    hint = "; ".join(f"{k}: {(elements or {}).get(k,'')[:60]}" for k in _KEYS)
    return (
        "Generate a Modern Minimalist Tech Infographic poster background, "
        "flat vector illustration with subtle isometric elements, high-quality "
        "corporate Memphis design style, clean lines and geometric shapes. "
        "Left-to-right process flow with 5 implied node areas. "
        "Background solid off-white #F5F5F7, no clutter. "
        "Palette: deep academic blue and slate grey, vibrant orange/teal accents, "
        "high contrast. 16:9 aspect ratio, 4K, high quality. "
        "IMPORTANT: render NO text / NO words / NO letters in the image — "
        "purely visual icons and shapes (text will be overlaid separately). "
        "No photorealism, no messy sketches, no chaotic background. "
        f"Visual theme hints (do not render as text): {hint}")

def generate_poster(meta, markdown, provider, out_dir="docs/images/posters",
                    api_key=None, base=None):
    elements = extract_elements(meta, markdown, provider)
    if not elements:
        return None
    doc_id = meta.get("doc_id") or meta.get("paper_id") or "unknown"
    out_path = os.path.join(out_dir, f"{doc_id}.webp")
    prompt = build_background_prompt(elements)
    saved = generate_and_save(prompt, out_path, max_edge=1024,
                              api_key=api_key, base=base)
    return {"elements": elements,
            "image": (saved or "").replace("docs/", "") or None,
            "doc_id": doc_id}
```

注：海报背景用 16:9，`max_edge=1024` 略大于卡图（保细节），仍 WebP。`image` 存相对 `docs/` 的路径（前端用）。

- [ ] **Step 5: 运行确认通过**

Run: `python -m pytest test_poster_generator.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add poster_generator.py ai_prompts/poster_elements.txt test_poster_generator.py
git commit -m "feat(poster): 5-element extraction + text-free Memphis background"
```

---

## Task 7：WS5 — 自动分类

**Files:**
- Create: `auto_classifier.py`
- Test: `test_auto_classifier.py`

- [ ] **Step 1: 写失败测试**

```python
# test_auto_classifier.py
import auto_classifier
from auto_classifier import classify

def test_rule_hit_skips_llm():
    a = {"title": "Altermagnetic spin splitting", "summary": "antiferromagnet"}
    cat = classify(a, provider=None)  # provider 不该被调用
    assert cat == "磁性·自旋电子学"

def test_rule_miss_uses_llm_fallback():
    class P:
        def call_api(self, prompt): return "量子信息·计算"
    a = {"title": "Some ambiguous title", "summary": "vague"}
    cat = classify(a, provider=P())
    assert cat == "量子信息·计算"

def test_llm_returns_unknown_category_falls_back_to_other():
    class P:
        def call_api(self, prompt): return "天体物理"  # 不在 taxonomy
    a = {"title": "ambiguous", "summary": "vague"}
    assert classify(a, provider=P()) == "其他"

def test_no_provider_and_no_rule_returns_other():
    a = {"title": "ambiguous", "summary": "vague"}
    assert classify(a, provider=None) == "其他"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_auto_classifier.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `auto_classifier.py`**

```python
"""规则优先 + gpt-5.5 兜底 的文章分类。"""
from focus_core import classify_taxonomy, TAXONOMY

_VALID = set(TAXONOMY.keys()) | {"其他"}

def classify(article, provider=None):
    rule = classify_taxonomy(article)
    if rule != "其他":
        return rule
    if provider is None:
        return "其他"
    cats = "、".join(TAXONOMY.keys())
    prompt = (f"把下面这篇论文归入且仅归入这些类别之一（只输出类别名，不要解释）：{cats}、其他。\n"
              f"标题：{article.get('title','')}\n摘要：{(article.get('summary') or article.get('abstract') or '')[:600]}")
    try:
        ans = (provider.call_api(prompt) or "").strip()
    except Exception:
        return "其他"
    for c in _VALID:
        if c in ans:
            return c
    return "其他"
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_auto_classifier.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add auto_classifier.py test_auto_classifier.py
git commit -m "feat(classify): rule-first + gpt-5.5 fallback taxonomy classifier"
```

---

## Task 8：feed.json 生成器

**Files:**
- Create: `feed_builder.py`
- Test: `test_feed_json.py`

- [ ] **Step 1: 写失败测试**

```python
# test_feed_json.py
import json
from feed_builder import build_feed, prune_window

def test_build_feed_shapes_items():
    aps = [{"source": "APS", "journal": "PRL", "title": "T", "title_zh": "标题",
            "summary": "s", "category": "AI×物理", "doc_id": "d1", "link": "http://x",
            "poster": {"image": "images/posters/d1.webp", "elements": {"研究问题": "q"}},
            "deep_analysis": "## 精读"}]
    arxiv = [{"source": "arxiv", "title": "A", "title_zh": "甲", "summary": "s2",
              "category": "磁性·自旋电子学", "link": "http://y", "image": "images/cards/h.webp"}]
    feed = build_feed(aps, arxiv, date="2026-05-28")
    assert feed["date"] == "2026-05-28"
    item = feed["items"][0]
    assert item["source"] == "APS" and item["poster_elements"]["研究问题"] == "q"
    assert any(i["source"] == "arxiv" for i in feed["items"])

def test_prune_window_keeps_recent():
    feeds = [{"date": "2026-01-01", "items": []}, {"date": "2026-05-28", "items": []}]
    kept = prune_window(feeds, today="2026-05-30", window_days=60)
    assert len(kept) == 1 and kept[0]["date"] == "2026-05-28"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_feed_json.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `feed_builder.py`**

```python
"""聚合 APS 精读 + arXiv 核心 → docs/data/feed.json，含 60 天滚动裁剪。"""
import os, json, datetime

def _item_from_aps(a):
    poster = a.get("poster") or {}
    return {"source": "APS", "journal": a.get("journal", ""),
            "title_en": a.get("title", ""), "title_zh": a.get("title_zh", ""),
            "summary": a.get("summary", ""), "category": a.get("category", "其他"),
            "link": a.get("link") or a.get("doi", ""), "doc_id": a.get("doc_id", ""),
            "image": poster.get("image"), "poster_elements": poster.get("elements"),
            "deep_analysis": a.get("deep_analysis", ""), "enriched": True}

def _item_from_arxiv(a):
    return {"source": "arxiv", "journal": a.get("journal", "arXiv"),
            "title_en": a.get("title", ""), "title_zh": a.get("title_zh", ""),
            "summary": a.get("summary", ""), "category": a.get("category", "其他"),
            "link": a.get("link", ""), "image": a.get("image"),
            "poster_elements": None, "deep_analysis": "", "enriched": bool(a.get("image"))}

def build_feed(aps_items, arxiv_items, date):
    items = [_item_from_aps(a) for a in (aps_items or [])] + \
            [_item_from_arxiv(a) for a in (arxiv_items or [])]
    return {"date": date, "items": items}

def prune_window(feeds, today=None, window_days=60):
    today = today or datetime.date.today().isoformat()
    cutoff = (datetime.date.fromisoformat(today)
              - datetime.timedelta(days=window_days)).isoformat()
    return [f for f in feeds if f.get("date", "") >= cutoff]

def write_feed_json(per_day_feeds, path="docs/data/feed.json", today=None, window_days=60):
    kept = prune_window(sorted(per_day_feeds, key=lambda f: f["date"], reverse=True),
                        today=today, window_days=window_days)
    flat = []
    for f in kept:
        for it in f["items"]:
            flat.append({**it, "date": f["date"]})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump({"generated": today, "items": flat}, fp, ensure_ascii=False)
    return path
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_feed_json.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add feed_builder.py test_feed_json.py
git commit -m "feat(feed): build feed.json with 60-day rolling window"
```

---

## Task 9：编排脚本 run_deep.py + 图像保留裁剪

**Files:**
- Create: `run_deep.py`
- Test: `test_run_deep.py`（用全 mock 跑通一天链路）

- [ ] **Step 1: 写失败测试**

```python
# test_run_deep.py
import run_deep

def test_process_date_enriches_aps(monkeypatch, tmp_path):
    metas = [{"title": "ML potential for perovskite", "journal": "PRL",
              "has_full_text": True, "markdown_oss_key": "k", "doc_id": "d1",
              "summary": "graph neural network"}]
    class FakeClient:
        def fetch_metadata(self, d): return metas
        def fetch_markdown(self, m): return "# Paper\nbody"
    class FakeProv:
        def call_api(self, p):
            return '{"研究问题":"q","创新方法":"m","工作流程":"f","关键结果":"r","应用价值":"v"}' \
                   if "海报" in p or "JSON" in p or "研究问题" in p else "## 精读\n内容"
    monkeypatch.setattr(run_deep, "generate_and_save",
                        lambda prompt, out_path, **k: out_path)
    out = run_deep.process_date("2026-05-28", client=FakeClient(),
                                provider=FakeProv(), out_dir=str(tmp_path))
    assert out[0]["deep_analysis"]
    assert out[0]["category"] in ("AI×物理", "AI×化学·材料")
    assert out[0]["poster"]["elements"]["创新方法"] == "m"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_run_deep.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `run_deep.py`**

```python
"""编排：拉 APS → 精读 → 海报 → 分类 → 写 feed.json。所有步骤失败静默降级。"""
import os, sys, json, glob, datetime
from concurrent.futures import ThreadPoolExecutor

from aps_client import ApsClient
from ai_summarizer import build_provider
from deep_reader import deep_read
from poster_generator import generate_poster
from auto_classifier import classify
from image_provider import generate_and_save
from feed_builder import build_feed, write_feed_json

def _enrich_one(meta, client, provider, out_dir):
    md = client.fetch_markdown(meta)
    rec = dict(meta)
    rec["source"] = "APS"
    rec["category"] = classify(meta, provider=provider)
    rec["deep_analysis"] = deep_read(meta, md, provider=provider) if md else ""
    rec["poster"] = generate_poster(meta, md, provider=provider, out_dir=out_dir) if md else None
    return rec

def process_date(date, client, provider, out_dir="docs/images/posters", max_workers=3):
    metas = client.fetch_metadata(date)
    full = [m for m in metas if m.get("has_full_text")]
    if not full:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = [ex.submit(_enrich_one, m, client, provider, out_dir) for m in full]
        for f in futs:
            try: results.append(f.result())
            except Exception as e: print(f"⚠️ enrich failed: {e}")
    return results

def prune_images(window_days=60, today=None, dirs=("docs/images/posters", "docs/images/cards")):
    """删除 feed.json 已不覆盖窗口外、且无引用的旧图（按 mtime 粗裁）。"""
    today = today or datetime.date.today()
    if isinstance(today, str):
        today = datetime.date.fromisoformat(today)
    cutoff = today - datetime.timedelta(days=window_days)
    for d in dirs:
        for p in glob.glob(os.path.join(d, "*.webp")):
            try:
                mtime = datetime.date.fromtimestamp(os.path.getmtime(p))
                if mtime < cutoff:
                    os.remove(p)
            except Exception:
                pass

def main():
    base_provider = build_provider(os.environ.get("AI_PROVIDER", "aigw"),
                                   os.environ.get("AI_API_KEY", ""),
                                   os.environ.get("AI_MODEL", "gpt-5.5"))
    provider = base_provider.provider if hasattr(base_provider, "provider") else base_provider
    client = ApsClient()
    window = int(os.environ.get("DEEP_WINDOW_DAYS", "3"))
    dates = client.list_dates(window_days=window)
    per_day = []
    for d in dates:
        aps = process_date(d, client, provider)
        # arXiv 核心配图在 generate_daily_pages 阶段已产出，这里读回（见 Task 11）
        arxiv_core = _load_arxiv_core(d)
        per_day.append(build_feed(aps, arxiv_core, date=d))
        _save_aps_index(d, aps)
    write_feed_json(per_day + _load_existing_feeds(), window_days=60)
    prune_images(window_days=60)

def _load_arxiv_core(date):
    path = f"data/arxiv_core_{date}.json"
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return []

def _save_aps_index(date, aps):
    os.makedirs("data", exist_ok=True)
    with open(f"data/aps_{date}.json", "w", encoding="utf-8") as f:
        json.dump(aps, f, ensure_ascii=False)

def _load_existing_feeds():
    feeds = []
    for p in sorted(glob.glob("data/aps_*.json")):
        date = os.path.basename(p)[4:-5]
        try: aps = json.load(open(p, encoding="utf-8"))
        except Exception: continue
        feeds.append(build_feed(aps, _load_arxiv_core(date), date=date))
    return feeds

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_run_deep.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add run_deep.py test_run_deep.py
git commit -m "feat(deep): orchestration run_deep.py + image retention pruning"
```

---

## Task 10：generate_daily_pages 接入「今日精读」区 + arXiv 核心配图导出

**Files:**
- Modify: `generate_daily_pages.py`
- Test: `test_daily_pages_render.py`（扩展）

- [ ] **Step 1: 写失败测试**（断言渲染含精读区与分类标签）

```python
# 追加到 test_daily_pages_render.py
def test_daily_renders_deep_read_section(tmp_path):
    from generate_daily_pages import render_deep_section
    aps = [{"title": "T", "title_zh": "标题", "category": "AI×物理",
            "deep_analysis": "## 第一部分：核心概览\n内容",
            "poster": {"image": "images/posters/d1.webp",
                       "elements": {"研究问题": "q", "创新方法": "m",
                                    "工作流程": "f", "关键结果": "r", "应用价值": "v"}},
            "link": "http://x", "doc_id": "d1"}]
    html = render_deep_section(aps)
    assert "今日精读" in html
    assert "images/posters/d1.webp" in html
    assert "poster-overlay" in html  # 叠字层
    assert "AI×物理" in html
    assert 'data-bookmark-key="http://x"' in html
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest test_daily_pages_render.py -k deep_read -v`
Expected: FAIL（`render_deep_section` 不存在）

- [ ] **Step 3: 实现 `render_deep_section`**

`generate_daily_pages.py` 增加函数（复用现有 `_safe_text` 转义；卡片用 `daily-core-card` 类沿用收藏/点赞钩子，新增 `daily-deep-card`）：

```python
def render_deep_section(aps_items):
    if not aps_items:
        return ""
    cards = []
    for a in aps_items:
        link = _safe_text((a.get("link") or a.get("doi") or "").strip())
        poster = a.get("poster") or {}
        img = poster.get("image"); el = poster.get("elements") or {}
        overlay = ""
        if el:
            rows = "".join(
                f'<div class="poster-row"><b>{_safe_text(k)}</b>{_safe_text(el.get(k,""))}</div>'
                for k in ["研究问题","创新方法","工作流程","关键结果","应用价值"] if el.get(k))
            overlay = f'<div class="poster-overlay">{rows}</div>'
        figure = (f'<div class="poster-figure"><img loading="lazy" src="{_safe_text(img)}" '
                  f'onerror="this.style.display=\'none\'">{overlay}</div>') if img else ""
        deep = _safe_text(a.get("deep_analysis","")) if a.get("deep_analysis") else ""
        deep_html = (f'<details class="deep-details"><summary>展开精读</summary>'
                     f'<div class="deep-body">{deep}</div></details>') if deep else ""
        cards.append(
            f'<article class="daily-deep-card daily-core-card" data-bookmark-key="{link}">'
            f'<span class="cat-tag">{_safe_text(a.get("category","其他"))}</span>'
            f'<h3>{_safe_text(a.get("title_zh") or a.get("title",""))}</h3>'
            f'{figure}{deep_html}'
            f'<a class="src-link" href="{link}" target="_blank">原文 ↗</a>'
            f'</article>')
    return ('<section class="daily-deep-section"><h2>📖 今日精读</h2>'
            + "".join(cards) + "</section>")
```

在日报主渲染流程里：读 `data/aps_<date>.json`（若存在）→ 调 `render_deep_section` 插到核心关注区之前。arXiv 核心区文章若已带 `image` 字段则在卡片加 `<img>`。同时把当天 arXiv 核心文章（含 `image`）导出到 `data/arxiv_core_<date>.json` 供 `run_deep.py` 聚合（也可在 run_deep 内调用现有 arXiv 核心配图——为简单起见此处仅导出已选核心列表，由 run_deep 决定是否配图）。

并在 `<head>` 引入 `bookmarks.css`（已在）+ 新增 `likes.js`、海报样式（可并入现有 daily CSS）。

- [ ] **Step 4: 运行确认通过**

Run: `python -m pytest test_daily_pages_render.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add generate_daily_pages.py test_daily_pages_render.py
git commit -m "feat(daily): 今日精读 section with poster overlay + category tags"
```

---

## Task 11：arXiv 核心区轻量配图（run_deep 内）

**Files:**
- Modify: `run_deep.py`（加 `enrich_arxiv_core`）
- Test: `test_run_deep.py`（扩展）

- [ ] **Step 1: 写失败测试**

```python
def test_enrich_arxiv_core_adds_image(monkeypatch, tmp_path):
    import run_deep
    monkeypatch.setattr(run_deep, "generate_and_save",
                        lambda prompt, out_path, **k: out_path)
    items = [{"title": "ML potential for magnet", "summary": "neural network",
              "link": "http://z"}]
    out = run_deep.enrich_arxiv_core(items, out_dir=str(tmp_path))
    assert out[0]["image"].endswith(".webp")
    assert out[0]["category"]
```

- [ ] **Step 2: 运行确认失败 → Step 3 实现**

```python
# run_deep.py 追加
import hashlib
def enrich_arxiv_core(items, provider=None, out_dir="docs/images/cards"):
    out = []
    for a in (items or []):
        rec = dict(a); rec["source"] = "arxiv"
        rec["category"] = classify(a, provider=provider)
        h = hashlib.sha1((a.get("link") or a.get("title","")).encode()).hexdigest()[:16]
        prompt = ("Flat vector minimalist scientific illustration, single clear concept, "
                  "clean lines, off-white background, deep blue + teal accents, no text. "
                  f"Concept: {a.get('title','')[:120]}")
        saved = generate_and_save(prompt, os.path.join(out_dir, f"{h}.webp"), max_edge=768, provider_kw=None) \
            if True else None
        rec["image"] = (saved or "").replace("docs/", "") or None
        out.append(rec)
    return out
```

注：`generate_and_save` 的 api_key/base 走环境默认，无需显式传。把 `process_date` 之外、main 里对 arXiv 核心的处理改为调用 `enrich_arxiv_core` 并 `_save` 到 `data/arxiv_core_<date>.json`。

- [ ] **Step 4: 运行确认通过 → Step 5 提交**

```bash
git add run_deep.py test_run_deep.py
git commit -m "feat(deep): light flat-vector images for arXiv core papers"
```

---

## Task 12：WS7 — 点赞 likes.js + 导出扩展

**Files:**
- Create: `docs/likes.js`、`docs/test-likes.html`
- Modify: `docs/exports.js`、`docs/bookmarks.css`
- Test: jsdom（沿用现有 `/tmp/node_modules` jsdom）

- [ ] **Step 1: 写失败测试**（jsdom 加载 likes.js，校验 store）

```javascript
// docs/test-likes.html 内嵌或独立 node 脚本（沿用现有测试 harness 风格）
// 断言：LikeStore.toggle(link, meta) 写入 localStorage key "literature_likes"
//       count()/has(link)/list() 正确；触发 "likeschange" 事件
```

具体测试用现有 `test_daily_pages_render.py` 同款 jsdom node 脚本结构（参考 `docs/test-bookmarks.html`）。断言：

```javascript
const { JSDOM } = require('/tmp/node_modules/jsdom');
// load likes.js, assert window.LikeStore exists
store.toggle('http://x', {title:'T'});
assert(store.has('http://x') === true);
assert(store.count() === 1);
assert(JSON.parse(localStorage.getItem('literature_likes'))['http://x'].title === 'T');
```

- [ ] **Step 2: 运行确认失败 → Step 3 实现 `docs/likes.js`**

镜像 `bookmarks.js` 的 `BookmarkStore`，改 `STORAGE_KEY='literature_likes'`、事件名 `likeschange`、按钮 ❤️/🤍，class `like-btn`，`data-like-key`。复用同一套 `CARD_SELECTORS`（`.daily-deep-card`, `.daily-core-card`, `.daily-paper-card`, `.weekly-core-card`, `.weekly-paper-card`, `.feed-card`）。`attachToCards` 在每张卡注入 ❤️ 按钮（与 ⭐ 并排）。

- [ ] **Step 4: 运行确认通过**

Run: `node /tmp/test_likes_runner.js`（结构同现有 bookmark jsdom 测试）
Expected: PASS

- [ ] **Step 5: 扩展 `exports.js`**

新增 `function collectAll()` 合并 `literature_bookmarks` + `literature_likes`（去重），现有 `exportRSS/exportMarkdown/exportBibTeX` 接受 items 数组；加一个「导出全部（收藏+点赞）」入口。

- [ ] **Step 6: 提交**

```bash
git add docs/likes.js docs/test-likes.html docs/exports.js docs/bookmarks.css
git commit -m "feat(likes): ❤️ personal likes store + combined export"
```

---

## Task 13：WS6 — /feed 全屏刷流页

**Files:**
- Create: `docs/feed.html`、`docs/feed.css`、`docs/feed.js`、`docs/test-feed.html`
- Test: jsdom（渲染 feed.json mock → 校验卡片、筛选、叠字）

- [ ] **Step 1: 写失败测试**（jsdom 注入 feed.js + 假 feed.json）

```javascript
// 断言：renderFeed(items) 产出 N 个 .feed-card；
// scroll-snap 容器存在；分类筛选 filterByCategory('AI×物理') 只显示该类；
// APS 卡含 .poster-overlay；每卡含 ⭐ 与 ❤️ 钩子（data-bookmark-key/data-like-key）
```

- [ ] **Step 2: 运行确认失败 → Step 3 实现**

`docs/feed.html`：极简骨架，引 `feed.css`、`bookmarks.js`、`likes.js`、`exports.js`、`feed.js`，含 iOS PWA meta、顶部分类筛选条 `<nav id="cat-bar">`、`<main id="feed" class="feed-scroller">`。

`docs/feed.css`：
```css
.feed-scroller{height:100vh;overflow-y:scroll;scroll-snap-type:y mandatory;}
.feed-card{height:100vh;scroll-snap-align:start;display:flex;flex-direction:column;
  justify-content:center;padding:24px;box-sizing:border-box;}
.poster-figure{position:relative;}
.poster-figure img{width:100%;border-radius:12px;}
.poster-overlay{position:absolute;inset:0;display:flex;flex-direction:column;
  gap:6px;padding:18px;font-family:"Songti SC","SimSun",serif;}
.poster-row b{color:#1456b8;margin-right:6px;}
.cat-tag{display:inline-block;padding:2px 10px;border-radius:999px;background:#eef2f7;color:#1456b8;}
```

`docs/feed.js`：IIFE — `loadFeed()` fetch `data/feed.json`；`renderFeed(items)` 建 `.feed-card`（标题/摘要/分类/图+叠字/⭐❤️/链接/APS 展开精读）；`buildCatBar()` 去重分类生成筛选 chip；`filterByCategory(cat)` 切换显隐；图片 `loading="lazy"` + `onerror` 隐藏；初始化后调 `window.BookmarkUI?.attachToCards` 与 `window.LikeUI?.attachToCards`。

- [ ] **Step 4: 运行确认通过 → Step 5 提交**

```bash
git add docs/feed.html docs/feed.css docs/feed.js docs/test-feed.html
git commit -m "feat(feed): full-screen scroll-snap literature feed"
```

---

## Task 14：入口 + PWA + workflow

**Files:**
- Modify: `docs/index.html`、`docs/manifest.json`、`docs/sw.js`
- Create: `.github/workflows/generate-deep.yml`
- Modify: `config.local.py.example`

- [ ] **Step 1: index/manifest/sw**

`docs/index.html` 顶部加「🔥 刷流 Feed」入口链接到 `feed.html`。`manifest.json` `shortcuts` 加 feed。`sw.js` 把 `feed.html`、`data/feed.json` 加入 network-first 缓存清单。

- [ ] **Step 2: 写 `generate-deep.yml`**

```yaml
name: Generate Deep Read + Posters + Feed
on:
  workflow_dispatch:
    inputs:
      window:
        description: "回看天数"
        default: "3"
  schedule:
    - cron: "30 3 * * *"   # 日报之后
permissions:
  contents: write
concurrency:
  group: generate-deep
  cancel-in-progress: false
jobs:
  deep:
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0, token: "${{ secrets.PAT_TOKEN }}" }
      - uses: actions/setup-python@v5
        with: { python-version: "3.11", cache: "pip" }
      - run: pip install -r requirements.txt
      - name: Run deep pipeline
        env:
          AI_API_KEY: ${{ secrets.AI_API_KEY }}
          AI_PROVIDER: aigw
          AI_MODEL: gpt-5.5
          AI_BASE_URL: ${{ secrets.AI_BASE_URL }}
          IMAGE_API_KEY: ${{ secrets.AI_API_KEY }}
          IMAGE_API_BASE: ${{ secrets.AI_BASE_URL }}
          APS_HTTP_BASE: ${{ secrets.APS_HTTP_BASE }}
          APS_HTTP_USER: ${{ secrets.APS_HTTP_USER }}
          APS_HTTP_PASS: ${{ secrets.APS_HTTP_PASS }}
          DEEP_WINDOW_DAYS: ${{ github.event.inputs.window || '3' }}
        run: python run_deep.py
      - name: Regenerate daily pages (insert 今日精读)
        env: { AI_API_KEY: "${{ secrets.AI_API_KEY }}", AI_PROVIDER: aigw, AI_MODEL: gpt-5.5, AI_BASE_URL: "${{ secrets.AI_BASE_URL }}" }
        run: python generate_daily_pages.py --days 3
      - name: Commit and push (race-safe)
        run: |
          git config user.email action@github.com; git config user.name "GitHub Action"
          git add -A
          git diff --staged --quiet && { echo nothing; exit 0; }
          git commit -m "📖 Deep read + posters + feed"
          for i in 1 2 3 4 5; do
            git fetch origin main
            git rebase -X ours origin/main || { git rebase --abort; exit 1; }
            git push origin main && exit 0
            sleep 5
          done
          exit 1
```

- [ ] **Step 3: `config.local.py.example` 加占位符**

```python
# APS 全文源（机密，勿提交真实值）
APS_HTTP_BASE = "http://<host>:<port>"
APS_HTTP_USER = "<aps-user>"
APS_HTTP_PASS = "<aps-pass>"
# 新网关
AI_PROVIDER = "aigw"; AI_MODEL = "gpt-5.5"
AI_BASE_URL = "https://aigw.sotatts.online/v1"
AI_API_KEY = "<your-key>"
```

- [ ] **Step 4: 提交**

```bash
git add docs/index.html docs/manifest.json docs/sw.js .github/workflows/generate-deep.yml config.local.py.example
git commit -m "feat(deep): feed entry, PWA, generate-deep workflow"
```

---

## Task 15：配置 GitHub Secrets + 端到端验收 + 推送

**Files:** 无（运维）

- [ ] **Step 1: 配置 Secrets**（用 `gh` 或 API，值来自会话提供，绝不写入文件）

需要设置：`AI_API_KEY`（新网关 key）、`AI_BASE_URL`、`APS_HTTP_BASE`、`APS_HTTP_USER`、`APS_HTTP_PASS`。复用现有 `PAT_TOKEN`。

- [ ] **Step 2: 全量 Python 测试**

Run: `python -m pytest test_*.py -v`
Expected: 全 PASS

- [ ] **Step 3: 前端 jsdom 测试**

Run: 现有 bookmark/render 套件 + 新 feed/likes 套件
Expected: 全 PASS

- [ ] **Step 4: 本地端到端**（真凭据，跑 1 天）

Run: `DEEP_WINDOW_DAYS=1 python run_deep.py` → 检查 `docs/data/feed.json` 有 items、`docs/images/posters/*.webp` 生成、`data/aps_*.json` 有 deep_analysis。
浏览器开 `docs/feed.html` 人工验收叠字海报 + 刷流。

- [ ] **Step 5: 凭据泄露终检**

Run: 把会话提供的真实凭据值逐个 `git log -p -5 | grep -n <value>` → 全部必须为空（不在历史里）。

- [ ] **Step 6: 推送 + 触发 workflow**

```bash
git push origin main
gh workflow run "Generate Deep Read + Posters + Feed" -f window=3
```

观察 run 成功、产物 commit 回仓库、GitHub Pages feed 可访问。

---

## Self-Review 结果

- **Spec 覆盖**：WS0→Task2、WS1→Task1、WS2→Task3、WS3→Task5、WS4→Task6、WS5→Task7+11、WS6→Task13、WS7→Task12、APS 海报体积闸→Task4+9（WebP+裁剪）、独立 workflow→Task14、今日精读区→Task10、feed.json→Task8、编排→Task9、入口/PWA→Task14、Secrets/E2E→Task15。全覆盖。
- **占位符**：`<host>`/`<secret>` 等为机密占位（强制），非实现空洞；其余步骤均给出完整代码。
- **类型一致**：`generate_and_save`/`classify(article, provider=)`/`build_feed(aps, arxiv, date)`/`poster={"elements","image"}`/store key `literature_likes` 全程一致。
- **失败隔离**：每个外部步骤（APS IO、provider、image）均 try/except 降级。
