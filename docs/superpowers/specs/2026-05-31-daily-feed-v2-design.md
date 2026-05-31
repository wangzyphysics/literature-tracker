# 设计：日报 × Feed v2 — 英文信息图 + 分层深析 + 强耦合 + 交互修复

日期：2026-05-31
状态：已批准设计，待 spec 评审

## 背景

literature-tracker 已具备：gpt-5.5 接入、APS 全文源、苏格拉底深读、概念海报（纯视觉背景+HTML 叠中文）、`/feed` 刷流页、收藏/点赞、自动分类。但实地测绘（2026-05-31）发现多处不完善，本设计为 v2 改造。

### 测绘确认的根因（证据基线）
- **配图看不清**：`docs/feed.css:17-19` 的 `.poster-overlay{position:absolute;inset:0;background:linear-gradient(180deg,rgba(245,245,247,.86),rgba(245,245,247,.66))}` 用 86%→66% 白蒙版铺满整张 1024×576 图，再叠约 1079 字 5 要素 → 底图被洗白埋没。本质矛盾：图与长文抢同一块区域。
- **AI 交叉=0**：线上 feed 56 条 `AI×物理=0`、`AI×化学·材料=0`，16 篇 arxiv 全 `其他`。根因：`generate_daily_pages.py` 的 `core_export`（约 :1019-1033）只写 `{title,title_zh,summary,link,journal}`，**不写 category 也无 abstract**；唯一打 category 的 `enrich_arxiv_core`（`run_deep.py:81`）被默认关闭的 `DEEP_ENABLE_ARXIV_IMAGES` 闸住。
- **收藏在 Feed 实际坏**：⭐/❤️ 会 attach（CARD_SELECTORS 含 `.feed-card`），但 `.feed-card` 无 `position:relative` → 绝对定位按钮上溯到视口失锚；⭐/❤️ 同 `top:8px/right:8px` 重叠；`.like-btn` 全站无 CSS 且 `feed.html` 不加载 `style.css`；`renderFeed` 只调 `attachToCards`，未调 `renderFab`/`bindGestures`（且 autoInit 早于异步插卡）→ 无 FAB、无长按、无计数。
- **死链 40/56**：`feed_builder.py:9` `link=a.get("link") or a.get("doi","")`，APS 存裸 DOI（如 `10.1103/766t-tqsy`）→ 前端当相对路径 → 404。
- **中文覆盖 28%**：40/56 卡无 `title_zh` 无 `summary`。
- **无进度/分组**：feed.json 每条带 `date` 但前端 `buildCard` 未用；`generated:null`（`write_feed_json` 调用未传 today）。
- **入口不显眼**：`index.html` 一条与其它并列的 `nav-link` 文字链接。
- **gpt-image-2 能力**：现有产物已自发画出柱状图/网络图/5 节点骨架，被 `NO text` 压掉标签；中文必乱码（设计已记录）→ 英文标签信息图为正解。

### 约束（设计时必须守）
1. CI 硬上限 90min（`generate-deep.yml: timeout-minutes: 90`）。任何扩配图必须走 `DEEP_MAX_NEW_PER_RUN` 预算 + 幂等多轮回填，不能一轮全量。
2. gpt-image-2 图内中文必乱码 → 图内只能英文短标签；中文走图外文档流。
3. arXiv 只有 abstract（无全文）→ arXiv 深析天花板是"摘要级"，不承诺 APS 级全文深读。
4. 全部 60 篇升级到 APS 级深析+配图**不可行**（无全文 + 120 次重调用 > 90min）。
5. 信息图英文清晰度本地无密钥未实测 → 全量前先 CI 手动 dispatch 跑 1 张验证。
6. 安全：所有凭据仅在 GitHub Secrets + 本地 gitignored config，提交文件只用占位符（沿用既有规范）。

## 目标（用户决策）

1. **分层覆盖**深析+配图；2. **英文信息图 + 图下中文要素**（根治看不清）；3. **同源数据 + 补全字段**强耦合；4. 四项增强：修死链+收藏全套、进度+按天分组、AI 交叉置顶+显眼入口、中文兜底+质量。

## 架构与工作流

```
WS-H 摘要级解析 prompt ─┐
WS-A 英文信息图 ────────┼─→ WS-B 分层深析+配图(预算/幂等) ─┐
WS-C core_export 补全 ──┘                                  ├─→ feed.json(补全) ─→ WS-D Feed 前端重构
WS-F 死链/元信息/中文兜底 ──────────────────────────────────┤                      ├─ WS-E 显眼入口
                                                            └─ WS-G 日报↔Feed 双向跳转
```

### WS-A：英文信息图配图（替代纯背景海报）
- `poster_generator.py`：
  - `extract_elements` 升级：除现有中文 5 要素 JSON，新增英文短标签 `elements_en`（5 个，如 `{"research_question":"...", "method":"GNN potential", ...}`，每个 ≤6 词），供信息图标签用。沿用 `safe_substitute` 容错。
  - 新增 `build_infographic_prompt(elements_en, title)`：产出英文信息图 prompt——现代极简科技信息图、左→右 5 节点流程（用 elements_en 的英文短标签）、允许柱状/折线/网络示意、深学术蓝+板岩灰+橙/青、`#F5F5F7` 底、16:9。**明确"schematic/illustrative chart, do NOT invent specific numeric values"**；negative prompt 保留 `no Chinese characters, no garbled text, no photorealism`。
  - `generate_poster` 改为生成信息图：`max_edge=1280`（小字清晰）、WebP q≈82。返回 `{elements(中文), elements_en, image, doc_id}`。
- 复用 `image_provider.generate_and_save`（流式 + 压缩）不变。
- 失败任一步 → 该篇无图，降级为纯文字卡，不阻塞。

### WS-H：摘要级解析（arXiv T2）
- 新增 `ai_prompts/abstract_analysis.txt`：轻量结构化中文解析，输入仅 abstract——`核心概览 / 方法要点 / 关键结果 / 创新性判断`，开头声明"基于摘要，不臆测未给出的数值"。占位 `${title}/${authors}/${abstract}`。
- `deep_reader.py` 增 `abstract_read(meta, abstract, provider) -> str`：填 `abstract_analysis.txt` 调 gpt-5.5，失败返回 ""。与全文 `deep_read` 并存。

### WS-B：分层深析+配图（控成本）
- `run_deep.py`：
  - T1 APS 全文：现状 `process_date` 不变（全文深读 + 信息图）。
  - T2 arXiv：新增 `process_arxiv_tier2(date, candidates, provider, budget, cache)`——对候选做 `abstract_read` + 英文信息图，写回 `data/arxiv_core_<date>.json` 的 `deep_analysis`/`poster`/`image` 字段。幂等：`_deep_complete` 判定（复用），已完成跳过。
  - T2 候选 = core_items ∪ classify_taxonomy 命中 AI×物理/AI×化学·材料 的常规文章（来自 core_export 导出的候选列表，见 WS-C）。
  - 统一预算：`DEEP_MAX_NEW_PER_RUN` 同时覆盖 T1+T2 的新增深析数（先 T1 后 T2，预算累减）。
  - T3 常规：不进 run_deep，仅 daily 渲染中文摘要+分类。
- 删除 `DEEP_ENABLE_ARXIV_IMAGES` 开关（T2 默认启用，受预算控制）。

### WS-C：core_export 补全 + 候选导出（耦合根治）
- `generate_daily_pages.py` core_export（约 :1019-1033）：每条增 `category=classify_taxonomy(it)`、`abstract`(英文原摘要)、`summary`(更长中文摘要，复用已生成的 zh 字段)、规范 `link`（arXiv 用 arxiv abs URL）。
- 新增导出 `data/arxiv_tier2_<date>.json`：当天 `is_core_focus` 或 classify 命中 AI× 的文章列表（title/title_zh/abstract/summary/link/category），供 `run_deep` 的 T2 消费。
- 不再瘦身：保证 Feed 的 arXiv 内容有 category + 中文 + 可用链接。

### WS-D：Feed 前端重构（`docs/feed.js` / `feed.css` / `feed.html`）
- **卡片结构**（图字分离）：`poster-figure`(信息图 `<img>`，**移除 overlay**) → `feed-title-zh`(中文标题，兜底英文) → `summary`(一句话) → `poster-elements`(中文 5 要素**独立文档流块**，非 APS 无则省) → `cat-tag`(分类) → ⭐/❤️ → `src-link`(修复链接) → `deep-details`(展开精读)。
- **修收藏/点赞**：`.feed-card{position:relative}`；⭐ 定位 `top:8px;right:8px`、❤️ `top:8px;right:48px`（错开）；新增 `.like-btn` CSS（参照 `.bookmark-btn` 角标）；`renderFeed` 末尾补调 `BookmarkUI.renderFab()` + `bindGestures(container)` 与 `LikeUI` 对应方法（若存在），实现右下 FAB+计数+长按。
- **分类条**：`buildCatBar` 按 `TAXONOMY` tier 排序，`AI×物理`/`AI×化学·材料` chip 置顶 + 高亮 class。
- **进度+分组**：顶部进度条（`第 N / 共 M`，随 scroll 更新）；按 `date` 分组插日期标头（轻量 sticky 标签，非占满屏的分隔卡）；未读计数（localStorage 键 `literature_feed_read` 记已读 doc_id/link）。
- **中文兜底**：`title_zh||title_en`；无 `summary` 时渲染 `abstract`(截断) 占位，避免空卡。
- **样式自包含**：所有 Feed 所需样式（含 `.like-btn`/`.bookmark-btn` 在 `.feed-card` 内的角标定位）写进 `feed.css`，不依赖 `style.css`（`feed.html` 只引 `feed.css`+`bookmarks.css`），避免缺样式/404。

### WS-E：显眼入口（`docs/index.html`）
- Feed 给一个**显眼 hero 卡/置顶 banner**（大按钮 + 文案"📱 刷流模式：一屏一篇·信息图·收藏点赞"），置于首屏主视觉区，而非 `nav-links` 里的小字。

### WS-F：死链 / 元信息 / 中文兜底（数据侧）
- `feed_builder.py`：`link` 规范化——非 `http(s)` 开头视为 DOI，包成 `https://doi.org/{doi}`（同步覆盖日报渲染的原文链接与 `data-bookmark-key`）。
- `run_deep.py` 调 `write_feed_json(..., today=<北京今天>)` 修 `generated:null`。
- feed item 增 `daily_url`(当日日报页 `daily/<date>.html`)，供 WS-G 反向跳转。

### WS-G：日报 ↔ Feed 双向跳转
- 日报每张卡（精读/核心）增「在 Feed 中查看 ↗」链接 → `../feed.html?date=<date>&doc=<doc_id 或 link 锚>`。
- Feed 每张卡增「当日日报 ↗」→ `daily/<date>.html`。
- `feed.js` 解析 `location.search` 的 `date`/`doc`：渲染后自动 `scrollIntoView` 到匹配卡并高亮。

## 受影响 / 新增文件

| 文件 | 改动 |
|---|---|
| `poster_generator.py` | WS-A：`elements_en` + `build_infographic_prompt` + 信息图生成 |
| `ai_prompts/abstract_analysis.txt` (新) | WS-H：摘要级解析模板 |
| `deep_reader.py` | WS-H：`abstract_read` |
| `run_deep.py` | WS-B：`process_arxiv_tier2` + 统一预算；WS-F：`write_feed_json` 传 today；删 `DEEP_ENABLE_ARXIV_IMAGES` 闸 |
| `generate_daily_pages.py` | WS-C：core_export 补字段 + 导出 tier2 候选；WS-G：日报卡加 Feed 链接 |
| `feed_builder.py` | WS-F：link 规范化 + `daily_url`；T2 字段并入 |
| `docs/feed.js` / `feed.css` / `feed.html` | WS-D/E/G：卡片重构、收藏修复、分类置顶、进度分组、中文兜底、深链 |
| `docs/index.html` | WS-E：显眼入口 |
| `docs/bookmarks.css` / `likes.js` | WS-D：`.feed-card` 定位 + `.like-btn` 样式 |
| `.github/workflows/generate-deep.yml` | 适配（T2 默认开、预算保持） |

## 复用 vs 改造
- **直接复用**：`image_provider`（流式+压缩）、`classify_taxonomy`、预算/幂等/裁剪机制、`BookmarkUI/LikeUI.attachToCards`、no-text 规避策略（信息图仍禁中文字形）。
- **改造**：`poster_generator`（背景→信息图）、`.poster-overlay`（盖图→图下文档流）、`core_export`（补字段+候选）、`feed.js buildCard/buildCatBar`、`write_feed_json` 调用、link 生成。

## 测试
- **Python 单元**：`build_infographic_prompt`（含英文标签、禁中文、schematic 声明）、`abstract_read`（mock provider）、core_export 字段（category/abstract/link）、`classify_taxonomy` AI× 命中、`feed_builder` link 规范化（DOI→doi.org）+ `daily_url`、T2 预算/幂等。
- **前端 jsdom**（`node /tmp/run_fe.js`）：新卡片（图不盖字、5 要素在图下、兜底英文、链接修复）、收藏 FAB+❤️ 定位（`.feed-card` position、按钮不重叠）、分类条 AI× 置顶、进度条+按天分组+未读、深链滚动高亮。
- **端到端**：CI 先 dispatch 跑 1 张信息图验证英文清晰度 → 再全量；验证 feed.json 有 AI× 分类、中文覆盖提升、链接可点、日报↔Feed 跳转。

## 明确不做（YAGNI）
- 不给全部 60 篇 arXiv 做全文级深析+配图（不可行）。
- 不引入后端/账号（收藏/点赞/已读继续 localStorage 单设备）。
- 不做独立 feed 数据契约层（同源数据流 + 补字段即可，列为后续）。
- 不强求 arXiv 全文抓取（深度天花板=摘要级）。
- 中文翻译质量的系统性回填属内容管线，本次仅做"补 category/abstract + 前端兜底"，不重写翻译管线。
