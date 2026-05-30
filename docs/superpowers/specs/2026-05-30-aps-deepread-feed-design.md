# 设计：APS 全文精读 + 概念海报 + 刷流 Feed + gpt-5.5 迁移

日期：2026-05-30
状态：已批准骨架，待 spec 评审

## 背景与目标

literature-tracker 现状：每日抓 arXiv RSS → gpt（原 Kimi）做翻译/摘要 → 生成日报/周报 HTML → GitHub Pages。已具备核心关注区、移动端收藏（localStorage）、PWA。

本次在此之上做七件事：

1. **WS0 关注重点更新**：用户重点改为 **AI×物理、AI×物理/化学/材料交叉为主，其他最重要的凝聚态物理（CMP）工作次之**。
2. **WS1 迁移 chat 模型**：从 Kimi 切到新网关 `gpt-5.5`（OpenAI 兼容），Kimi 保留为可选 fallback。
3. **WS2 接入 APS 全文源**：复旦×创智合作站，每天产出 PRL/PRX 等带版权文献的处理后 markdown 全文 + 论文内图 + 元数据。
4. **WS3 深度精读**：对每篇 APS 全文跑「苏格拉底式资深研究员」prompt，产出富结构中文精读。
5. **WS4 概念海报**：抽取论文 5 要素 → gpt-image-2 生成纯视觉孟菲斯风背景 → 前端 HTML/CSS 叠加中文要素文字（规避图内中文乱码）。
6. **WS5 自动分类 + arXiv 核心区轻量配图**。
7. **WS6 /feed 全屏刷流页** + **WS7 收藏⭐/点赞❤️**。

非目标：不重写现有 arXiv RSS 抓取与日报/周报 prompt 体系（运行良好，仅换底层模型）；不引入后端/数据库（点赞/收藏继续纯前端 localStorage 单设备）；不做 OSS 直连 SDK（HTTP 浏览器够用，SDK 仅备用）。

## 安全约束（强制）

APS HTTP basic-auth 凭据与阿里云 OSS Access Key 属于**不可外传**机密：

- 一律只存入 **GitHub Secrets** 与本地 **`config.local.py`（已 gitignored）**。
- **任何提交进 git 的文件（代码、spec、plan、workflow yaml）只能出现 Secret 名称占位符**，不得出现明文凭据。
- Secret 名称约定：
  - `APS_HTTP_BASE`（站点根 URL，不含凭据）
  - `APS_HTTP_USER` / `APS_HTTP_PASS`（basic-auth）
  - `APS_OSS_KEY_ID` / `APS_OSS_KEY_SECRET` / `APS_OSS_BUCKET`（备用直连，可暂不接）

## 数据源调研结论（已实测）

新网关 `https://aigw.sotatts.online/v1`（OpenAI 兼容）：

| 能力 | 结果 |
|---|---|
| `gpt-5.5` chat `/v1/chat/completions` | ✅ 可直接复用 `OpenRouterProvider` |
| 直接调 `gpt-image-2` `/v1/images/generations` | ❌ 网关拒绝（ChatGPT/Codex 账号不支持） |
| 图像生成：`/v1/responses` + `tools:[{type:image_generation}]` + **`stream:true`** | ✅ base64 从流事件 `response.output_item.done` 的 `image_generation_call.result` 取出；实测单张 ~880KB PNG，~50-60s |

APS HTTP 浏览器（basic-auth）：

- 列日期目录：`GET {base}/?prefix=APS%2F<YYYY-MM-DD>%2F` → HTML，含 `markdown/`、`pdf/`、`metadata.jsonl` 链接。
- 取元数据：`GET {base}/download?key=APS/<date>/metadata.jsonl` → **302 重定向到 OSS 签名 URL**（须 `-L` 跟随）→ JSONL，每行一篇。
- 每天 ~12 篇，全部 `has_full_text=True`、journal ∈ {PRL, PRX, …}。
- 关键字段：`title, abstract, authors, doi, journal, journal_slug, arxiv_id, categories, keywords, year, has_full_text, markdown_oss_key, image_oss_prefix, doc_id, paper_id`。
- 取全文：`GET {base}/download?key=<markdown_oss_key>` → 302 → md（实测 PRX 全文 103KB）。
- 数据滞后约 1-2 天（今天 2026-05-30，最新目录 2026-05-28）——拉取需回看窗口。

## 架构与工作流

```
WS0 focus 更新 ─┐
WS1 gpt-5.5 ────┼─→ WS2 APS 接入 ─→ WS3 精读 ─┬─→ WS4 海报 ─┐
                │                              │            ├─→ WS6 /feed
                └─→ WS5 分类 + arXiv 核心配图 ─┴────────────┤
                                                            └─→ WS7 收藏/点赞
```

### WS0 — 关注重点更新（`focus_core.py` / `config.py`）

重写权重，新增 taxonomy（供 WS5 分类与 WS0 排序共用）：

- **一级（最高权重）**：`AI×物理`、`AI×化学·材料`（机器学习/神经网络/生成模型/基础模型 × 物理/化学/材料）
- **二级（重要 CMP）**：`磁性·自旋电子学`、`铁电·极化`、`拓扑·电子结构`、`超导`、`量子信息·计算`
- **三级**：`软物质·流体·统计`、`其他凝聚态`、`其他`

`core_score()` 提高一级关键词权重；`is_core_focus()` 命中一级或二级判为核心。保留现有 None/空 dict 守卫。

### WS1 — 迁移 gpt-5.5（`ai_summarizer.py` / `config.py`）

- `build_provider` 新增 provider key `aigw`：内部复用 `OpenRouterProvider`（已是 OpenAI chat 格式 + JSON 修复 + 长度约束），base_url 取 `AI_BASE_URL`，model `gpt-5.5`。
- 默认配置切到 `AI_PROVIDER=aigw`、`AI_MODEL=gpt-5.5`、`AI_BASE_URL=https://aigw.sotatts.online/v1`、`AI_API_KEY=<secret>`。
- `KimiClaudeCodeProvider` 保留，配置可切回。
- GitHub Secrets 更新 `AI_API_KEY` / `AI_PROVIDER` / `AI_MODEL` / `AI_BASE_URL`。

### WS2 — APS 客户端（新 `aps_client.py`）

单一职责的 HTTP 客户端，接口清晰可独立测试：

- `list_dates(window_days)` → 最近 N 天里 OSS 上实际存在的日期列表。
- `fetch_metadata(date)` → `list[dict]`（解析 metadata.jsonl，跟随 302）。
- `fetch_markdown(meta)` → 全文 str（按 `markdown_oss_key` 下载，跟随 302）。
- `list_images(meta)` → 论文内图 key 列表（按 `image_oss_prefix`，可选，feed 备用插图）。
- 依赖：`requests`（已有）+ basic-auth from env。所有外部 IO 可 mock。
- 失败（站点不可达/某篇缺失）→ 记日志、跳过该篇，不抛断主流程。

数据落地：APS 篇目并入文章数据模型（`data/index.json` 或独立 `data/aps_index.json`），打 `source="APS"` 标记，带 `deep_analysis`、`poster`（image 路径 + 5 要素 JSON）、`category` 字段。

### WS3 — 深度精读（新 `deep_reader.py`）

- 输入：APS 全文 md + 元数据（title/authors/year）。
- prompt：用户提供的「苏格拉底式资深研究员」5 部分模板（核心概览 / 结构化快速回顾 / 逐章节冷凝解析含英文原文引述 / 术语与疑难 / 创新评估），存为 `ai_prompts/deep_read.txt`，运行时填充 `${title}/${authors}/${year}/${context}`。
- 全文可能超长 → 截断/分块策略：优先保留 abstract + 正文主体，按模型上下文上限裁剪（`_clamp_text` 复用）。
- 输出：富结构中文 markdown，存进文章数据 `deep_analysis`；日报「今日精读」区可折叠展开，可导出。
- 范围：**每篇 PRL/PRX 全文都精读，不设数量上限**；置于独立 workflow（见下），单篇超时（默认 180s）跳过。

### WS4 — 概念海报（新 `poster_generator.py` + 前端叠字）

两段式，彻底规避图内中文乱码：

1. **要素抽取**（gpt-5.5）：用户提供的「学术概念海报关键视觉信息」prompt → 严格 JSON `{研究问题, 创新方法, 工作流程, 关键结果, 应用价值}`（中文）。存进文章数据 `poster.elements`。
2. **背景生成**（gpt-image-2 via Responses 流式）：用户提供的海报设计 prompt，但**去掉"渲染中文文字"诉求，改为生成纯视觉背景**——孟菲斯风、扁平矢量+微等距、深学术蓝+板岩灰+橙/青高亮、`#F5F5F7` 底、16:9、几何图标暗示 5 个流程节点但不写字。negative prompt 保留（无写实/无草图/无乱字）。
3. **压缩落地**：PNG → Pillow 降采样到长边 768px → WebP（q≈80）→ `docs/images/posters/<doc_id>.webp`（~80-120KB）。
4. **前端叠字**：海报卡片 = `<img>` 背景 + 绝对定位的 HTML/CSS 层，渲染 5 要素中文（web 字体近 SimSun，清晰可选中可翻译）。布局：左→右流程或居中。

失败任一步 → 该篇无海报，降级为纯文字精读卡，不阻塞。

### WS5 — 自动分类（新 `auto_classifier.py`）+ arXiv 核心配图

- 分类：先跑 WS0 taxonomy 关键词规则（免费、零延迟）；规则置信度低的少数篇再批量丢 gpt-5.5 归一类。结果写 `category`。
- arXiv 核心区（🎯，AI×物理/化学/材料）配**轻量扁平矢量科学示意图**（gpt-image-2 流式，单个对象/概念，无叠字），同压缩落 `docs/images/cards/<hash>.webp`。
- 范围确认：**APS 精读出海报 + arXiv 核心区出轻量图**两类都配。

### WS6 — /feed 全屏刷流（新 `docs/feed.html` / `feed.js` / `feed.css`）

- 数据源：生成期产出紧凑 `docs/data/feed.json`，聚合最近 N 天：每篇 `{source, journal, title_zh, title_en, summary, category, image, poster_elements?, deep_analysis?, link, doc_id}`。
- 交互：移动端全屏、CSS `scroll-snap` 竖向一屏一篇。每屏：配图/海报（叠字，懒加载，无图则纯文字卡）+ 中文标题 + 一句话摘要 + 彩色分类标签 + ⭐收藏 + ❤️点赞 + 原文链接 + APS 篇「展开精读」。
- 顶部分类筛选条。复用 `bookmarks.js` store。PWA manifest 加 feed 入口。

### WS7 — 点赞（扩展 `docs/bookmarks.js` 或新 `docs/likes.js`）

- 镜像收藏结构，localStorage 键 `literature_likes`，值 `{[link]: meta}`。❤️ 切换/计数/`likeschange` 事件。
- 注入日报/周报/feed 卡片，与 ⭐ 并排。
- 导出（`exports.js`）扩展：可同时导出收藏+点赞为 RSS/Markdown/BibTeX。

## CI / 体积 / 失败隔离（三道闸）

1. **独立 workflow `generate-deep.yml`**：日报主流程跑完后（`workflow_run` 触发或串接），独立做 APS 拉取→精读→海报→arXiv 配图→写 feed.json→commit。日报主流程不被拖慢（仍 5-25 分钟）。并发 3-4 张图，单篇/单图超时跳过。
2. **体积**：所有生成图 WebP+768px；`docs/images/` 与 feed.json 走 **60 天滚动裁剪**（可配），旧图自动 prune。稳态 ≈ (12 海报 + ~13 卡图)/天 × 60 天 × ~100KB ≈ 150MB，可接受。图均为装饰增强，feed 与日报页对 404 优雅降级。
3. **失败隔离**：APS 不可达 / 精读失败 / 海报失败 / 分类失败 → 各自静默降级（日志 + 跳过），日报与 feed 永远能出。`summaries.json` 已有 `generated_by`，feed.json 篇目带 `enriched` 标记便于监控。

## 测试策略（沿用现有框架）

- **Python 单元**：`aps_client`（mock HTTP/302）、`deep_reader`（mock provider，校验 prompt 填充与截断）、`poster_generator`（mock 流式 + 校验 WebP 压缩尺寸）、`auto_classifier`（规则+兜底）、`focus_core` 更新、`feed.json` 生成、provider 切换。
- **前端 jsdom**：`feed.js`（scroll-snap 渲染、筛选、懒加载）、`likes.js`（store/事件/导出）、海报叠字层；真渲染集成（用 Python 产出的真 HTML/feed.json）。
- **端到端**：本地跑一天 `generate-deep` 全链路（APS→精读→海报→feed），人工验收日报「今日精读」区与 /feed。

## 受影响 / 新增文件

| 文件 | 改动 |
|---|---|
| `focus_core.py`, `config.py` | WS0 taxonomy + 权重 |
| `ai_summarizer.py`, `config.py` | WS1 `aigw` provider |
| `aps_client.py` (新) | WS2 APS HTTP 客户端 |
| `deep_reader.py` (新), `ai_prompts/deep_read.txt` (新) | WS3 精读 |
| `poster_generator.py` (新), `ai_prompts/poster_elements.txt` (新) | WS4 海报抽要素+生成 |
| `image_provider.py` (新) | gpt-image-2 Responses 流式封装（WS4/WS5 共用） |
| `auto_classifier.py` (新) | WS5 分类 |
| `generate_daily_pages.py` | 接入「今日精读」区 + arXiv 核心配图 + 分类标签 |
| `docs/feed.html` / `feed.js` / `feed.css` (新) | WS6 |
| `docs/data/feed.json` (生成物) | WS6 数据源 |
| `docs/likes.js` (新), `docs/bookmarks.css`, `docs/exports.js` | WS7 |
| `docs/index.html`, `manifest.json`, `sw.js` | feed 入口 + 缓存 |
| `.github/workflows/generate-deep.yml` (新) | 独立精读/海报/feed workflow |
| `config.local.py.example` | APS/OSS/网关 占位符示例 |

## 复用的现有设施

- `OpenRouterProvider` + `normalize_chat_completions_url`（WS1 直接复用）。
- `_clamp_text` / `_cjk_ratio`（WS3 截断、质量复检）。
- `bookmarks.js` store + `exports.js`（WS7 镜像/扩展）。
- 现有 jsdom 测试框架（103 测试）+ 真渲染集成 harness。
- race-safe push（rebase -X ours + 5 重试）用于 `generate-deep.yml`。

## 明确不做（YAGNI）

- 不直连 OSS SDK（HTTP 浏览器够用；OSS 凭据仅作未来备用，记入 Secrets）。
- 不做后端/账号/跨设备同步（收藏/点赞继续本地）。
- 海报不强求图内渲染中文（叠字方案已解决）。
- 不给 arXiv 非核心区配图（成本）。
- 不改现有周报 prompt（仅换模型 + 加点赞钩子）。
