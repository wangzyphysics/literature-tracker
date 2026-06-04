# 设计：删除 TikTok Feed + 日报条目富化（列表 → 展开）

日期：2026-06-04
状态：已批准设计（待 spec review）

## 背景与动机

v2 引入的 TikTok 式 `/feed`（一屏一篇、滑动浏览）实测**不好用**，用户决定删除。但 Feed 背后的富化数据（深度分析、英文信息图、中文 5 要素）很有价值——只是目前**只喂给 `feed.json`，从未进入日报列表**。这正是「日报每一条介绍很少、就一个简单摘要」的根因：`render_daily_html` 的「完整速览」只渲染 `full_list` 的纯摘要，而 `arxiv_core_<date>.json`（AI 交叉 arxiv 的深析+配图+要素）和 `aps_<date>.json`（APS 全文）的富化从没合并进去。

**目标**：删掉 Feed，把富化数据合并回日报**每一条**，做成「浏览标题列表 → 一句话亮点+标签即可分拣 → 点开看具体分析+一张图」的单列表交互。用户原话：「我看日报开始的标题 list，浏览标题时就知道要不要关注，关注了点进去就能看到具体分析和一张图」。

## 关键决策（已与用户确认）

1. **覆盖范围 = 维持分层**：APS 全文 + AI 交叉/核心 arxiv 才生成深析+配图；普通 arxiv 仅更丰富的中文要点（无图）。不全量出图（成本/时长不可行，且多数非交叉论文价值低）。
2. **列表态 = 标题 + 一句话亮点 + 标签**：未展开时每条显示中文标题、一句话核心亮点、分类/期刊标签、以及「📊 含图深析」徽标，一眼可分拣。
3. **收藏 = 保留收藏 + 收藏页**：复用现有 `bookmarks.js`（已自动注入 ⭐ 按钮 + 「我的收藏」FAB 汇总浮层），零新组件。
4. **布局 = 纯单列表**：所有文章（APS 全文 + arxiv）并成一个列表，含图深析的置顶、统一可展开。

## 非目标（YAGNI）

- 不保留 Feed 的任何前端（滑动手势、进度条、点赞 like、按天分组都随 Feed 删除）。点赞 `likes.js/likes.css` 仅 Feed 使用 → 一并删除引用。
- 不改 prompt / 深析 schema / 信息图生成逻辑（运行良好）。
- 不动 `feed.xml`（这是**全站 RSS**，与 TikTok Feed 无关，保留）。
- 不重写 run_deep 的富化/预算/幂等逻辑——只去掉 `write_feed_json` 这一个出口。

## 架构与数据流

### 现状
```
generate_daily_pages.py  --(写)--> data/arxiv_tier2_<date>.json  (AI交叉候选)
run_deep.py              --(读候选, 富化)--> data/arxiv_core_<date>.json  (深析+poster+category)
                         --(APS全文)-------> data/aps_<date>.json
                         --(汇总)----------> docs/data/feed.json   ← 删除此出口
render_daily_html        --(只读)----------> summary.full_list (纯摘要)   ← 富化没进来
```

### 目标
```
render_daily_html 渲染时:
  1. 读 summary.full_list (基础条目)
  2. 读 data/arxiv_core_<date>.json → 按 normalize_link(link) 建富化 map
  3. 读 data/aps_<date>.json → APS 全文富化条目 (不在 full_list 中)
  4. 合并: 每个 full_list 条目查富化 map; APS 条目并入列表
  5. 排序: 含图深析(APS全文 > AI交叉arxiv) 置顶, 普通文章随后
  6. 渲染单列表, 富化条目可 <details> 展开看图+要素+深析
```

### 数据合并键
- arxiv tier-2：`arxiv_core` 的 `link` 来自 `build_tier2_candidates(full_list)`，与 full_list 条目同 `link` → `normalize_link(link)` join。
- APS：`aps_<date>.json` 条目源自 APS 全文，**不在** full_list 中 → 直接并入列表，无需 dedup。

## 组件改动

### 1. 删除 Feed（A）
| 删除 | 说明 |
|---|---|
| `docs/feed.html` `docs/feed.js` `docs/feed.css` | TikTok 前端 |
| `docs/data/feed.json` | Feed 数据 |
| `feed_builder.py` `test_feed_json.py` | Feed 构建 + 测试 |
| `docs/test-feed.html` | Feed 前端测试页 |
| `docs/likes.js` `docs/likes.css` `docs/test-likes.html` | 点赞仅 Feed 用 |

| 修改 | 说明 |
|---|---|
| `run_deep.py` | 去掉 `write_feed_json` 调用 + 函数（保留 arxiv_core/aps 富化）；去掉对 `feed_builder` 的 import |
| `docs/index.html` | 删 `feed-hero`，换成醒目「📰 每日摘要」入口卡；去掉 `likes.css/js` 引用 |
| `docs/style.css` | 删 `.feed-hero*` 样式 |
| `generate_daily_pages.py` | `render_deep_section` 删「在 Feed 中查看 ↗」链接；去掉 `likes.css` 注入 |
| `weekly_summary.py` | 去掉 `likes.css` 引用 |
| `docs/sw.js` | precache 列表去掉 `feed.html/feed.js/feed.css/likes.*` |
| `.github/workflows/generate-deep.yml` | 无需改（run_deep 内部不再写 feed.json） |

**保留**：`feed.xml`（RSS）、`bookmarks.js/css`（收藏）、所有 `arxiv_core/aps` 富化。

### 2. 日报渲染合并富化（B，核心）
改 `generate_daily_pages.py`：
- 新增纯函数 `load_enrichment(date_str) -> dict`：读 `arxiv_core_<date>.json`，返回 `{normalize_link(link): {deep_analysis, poster, category, title_zh}}`。文件缺失 → `{}`（页面与改动前一致，安全降级）。
- 新增纯函数 `build_unified_items(full_list, enrich_map, aps_items) -> list`：合并 + 附富化标记 `_enriched`/`_tier`/`_poster`/`_deep`，按 tier 排序（APS 全文=0，AI 交叉含图=1，普通=2）。
- 新增 `render_unified_item(item, index) -> str`：
  - 列表态：`daily-paper-number` + 中文标题 + 一句话亮点 + meta chips +（富化时）`<span class="enrich-badge">📊 含图深析</span>`
  - 富化时追加 `<details class="enrich-details"><summary>展开分析 + 配图</summary>` → `<div class="poster-figure"><img …></div>` + 5 要素块 `.daily-deep-elements` + 深析正文 `.deep-body`。
  - `data-bookmark-key={link}`（收藏自动生效）。
- 用 `build_unified_items` 替换原「完整速览」分组渲染；删除/合并独立的 `render_deep_section`（APS 并入单列表）。保留现有 `#core-focus`（core_items，ML×ferro 文字深析）不动——它是另一套字段，正常工作；与单列表互补。

> 注：core_items（ML×ferro 核心关注，含 method_point/related_work/implication 文字字段）与 arxiv tier-2 可能重叠，但本次**不合并** core_items 段（避免过度重构）。tier-2 富化在单列表内以图+要素形式呈现，core_items 段保留其文字深析。

### 3. 收藏（C）
- 确认 `daily/<date>.html` 与 `weekly/<date>.html` 都 `<script defer src="../bookmarks.js">` + `bookmarks.css`（多数已有，逐页核对）。
- `docs/index.html` 导航加「⭐ 我的收藏」提示文案（FAB 已由 bookmarks.js 注入，无新页面）。
- 无新组件、无新存储键。

### 4. 同日富化可见性（D，时序）
工作流现序：`daily(--days 4 --force, 写 tier2 候选)` → `run_deep(富化 arxiv_core)`。当天 daily 渲染时 arxiv_core 未生成 → 当天列表无图。
**修复**：`generate-deep.yml` 在 run_deep 之后加一步「重渲染日报」。
- 新增 `generate_daily_pages.py --rerender-only`（或复用现有参数）：**仅重渲染 HTML**，读 `summaries.json` 缓存的 overview/trends（不再调 AI）+ 新鲜 `arxiv_core/aps` 富化 merge。避免重复 AI 调用。
- 过去几天本就随 `--days 4` 自然带富化（arxiv_core 已存在）。

## 测试

| 测试 | 验证 |
|---|---|
| `test_daily_pages_render.py`（扩展） | `load_enrichment` 读 arxiv_core 建 map；`build_unified_items` 合并+排序（APS 置顶、AI交叉次之、普通在后）；`render_unified_item` 富化条目含 `enrich-badge`+`<details>`+`poster-figure`+5 要素+deep-body，普通条目不含 details；缺 arxiv_core 文件时降级为纯摘要列表 |
| `test_daily_pages_render.py`（改） | 删除/改写依赖 `render_deep_section` 独立段与「在 Feed」链接的断言 |
| 删除 `test_feed_json.py` | Feed 测试随功能删除 |
| `test_run_deep.py`（改） | 去掉 `write_feed`/feed.json 相关断言（若有）；保留 arxiv_core/aps 富化测试 |
| 前端（jsdom，`docs/test-bookmarks.html`） | 日报单列表卡片仍被 bookmarks.js 识别并注入 ⭐；FAB 汇总正常 |

本地：`python3 run_tests.py`（stdlib，无 pip）+ node jsdom 跑前端。bs4 相关测试本地失败属正常（无 bs4）。

## 受影响文件清单

| 文件 | 改动 |
|---|---|
| `docs/feed.html` `docs/feed.js` `docs/feed.css` `docs/data/feed.json` `docs/test-feed.html` | 删除 |
| `feed_builder.py` `test_feed_json.py` | 删除 |
| `docs/likes.js` `docs/likes.css` `docs/test-likes.html` | 删除 |
| `run_deep.py` | 去 `write_feed_json` + feed_builder import |
| `generate_daily_pages.py` | 新增 `load_enrichment`/`build_unified_items`/`render_unified_item`；合并单列表；删 Feed 链接；`--rerender-only` |
| `docs/index.html` | 删 feed-hero → 每日摘要入口卡；加收藏提示；去 likes 引用 |
| `docs/style.css` | 删 `.feed-hero*` |
| `docs/sw.js` | precache 去 feed/likes |
| `weekly_summary.py` | 去 likes.css |
| `.github/workflows/generate-deep.yml` | run_deep 后加「重渲染日报」步骤 |
| `test_daily_pages_render.py` `test_run_deep.py` | 扩展/修正断言 |

## 验证方式

1. 本地 `python3 run_tests.py` 全绿（bs4 失败除外）。
2. `grep -rl "feed.html\|feed.js\|likes.js\|write_feed_json" docs/ *.py` 仅剩 `daily/*.html` 历史归档（不影响），无活跃引用。
3. 渲染一天日报，确认单列表：含图深析条目有 `enrich-badge` + `<details>`，展开见 `<img>` + 5 要素 + 深析；普通条目仅标题+亮点+标签。
4. 浏览器打开日报，点 ⭐ 收藏 → FAB「我的收藏」浮层列出。
5. CI 端到端：run_deep 后重渲染步骤让当天日报即含图。
6. `feed.xml`（RSS）仍 200、index 入口指向每日摘要。

## 安全

APS 源凭据仅在 GitHub Secrets + 本地 gitignore 配置，提交文件用占位符。本次不涉及凭据改动。
