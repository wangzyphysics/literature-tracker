# 设计：手机端书签收藏 + 多格式导出

> 作者：Claude (Opus 4.7) + 于宏宇
> 日期：2026-05-01
> 状态：待实现

## Context

`literature-tracker` 的核心阅读路径是 GitHub Pages 上的日报 / 周报 HTML 页面。用户主要在手机上浏览，但当前体验有三个痛点：

1. **手机端排版不友好**：日报/周报模板的移动端 CSS 单薄，卡片点击区小，中英文标题互相挤压，没有粘性目录跳转
2. **想"标记一下回头看"做不到**：日报/周报页面是纯静态 HTML（Python 模板渲染），没有任何 JS 交互，主页 `app.js` 已有的 ⭐ 收藏系统压根没接进来
3. **跨日报/周报的"我看过的好文"无法集中导出**：用户需要按时间持续把多篇文章打包，做成 RSS 给阅读器、做成 Markdown 贴笔记、做成 BibTeX 写论文

目标：日报/周报每张 card 上加 ⭐ 按钮 + 长按/右滑手势，底部 FAB 显示收藏数 + 一键打开收藏面板，面板支持 RSS / Markdown / BibTeX 三种导出。**纯前端实现**：无后端、无账号，localStorage 单设备存储。

非目标：跨设备同步、JSON 导出、BibTeX 自动补全 CrossRef、收藏分类标签、收藏内全文搜索。

---

## 架构总览

```
┌──────────────────────────────────────────────────┐
│  日报 HTML       周报 HTML       主页 index.html │
│  (Python 渲染)   (Python 渲染)    (静态)         │
│      ↓               ↓                 ↓         │
│  <link  rel="stylesheet" href="/bookmarks.css">  │
│  <script src="/bookmarks.js" defer></script>     │
└────────────────────────┬─────────────────────────┘
                         ↓ 扫描 DOM 注入交互
            ┌────────────┴────────────┐
            │  bookmarks.js (新增)     │
            │  - BookmarkStore         │
            │    (localStorage 单源)   │
            │  - BookmarkUI            │
            │    ⭐ 按钮 / 手势 / FAB   │
            │    / 收藏面板             │
            └────────────┬─────────────┘
                         ↓
                ┌────────┴────────┐
                │ exports.js (新)  │
                │ RSS / MD / BibTeX│
                └──────────────────┘
```

每个 card 根节点带 `data-bookmark-key="<link URL>"`（Python 模板加），其余 title-zh / title-en / abstract / journal 文本由 JS 在 toggle 时**直接从 DOM 读取**——无需在 data 属性里冗余。

---

## 数据模型（localStorage）

**Key**：`literature_bookmarks`
**值结构**：

```json
{
  "https://arxiv.org/abs/2604.11578": {
    "title_zh": "二维范德华 NbOI2 中的室温铁电性",
    "title_en": "Room-temperature ferroelectricity in two-dimensional...",
    "journal": "Nature",
    "abstract_zh": "在二维 NbOI2 薄层中观测到稳定的面外铁电翻转...",
    "summary": "首次在二维 NbOI2 中实现室温稳定的面外铁电翻转。",
    "authors": ["A. Zhou", "B. Li"],
    "source_type": "daily",
    "source_date": "2026-04-15",
    "added_at": 1746115200000
  },
  ...
}
```

**冲突**：同 URL 重复 add → 静默忽略，保留首次记录的 `source_date` / `added_at`。
**版本迁移**：检测到旧 key `literature_favorites`（主页 app.js 的简单 ID set）则一次性合并并删除——但只在 URL 可推断时；不可推断的 ID 跳过 + 一行 console.warn。

---

## 文件清单

### 新增

| 文件 | LOC（约） | 责任 |
|---|---|---|
| `docs/bookmarks.js` | 350 | `BookmarkStore` + `BookmarkUI`：扫描 DOM、注入 ⭐、绑定手势、FAB、收藏面板 |
| `docs/exports.js` | 150 | 三个导出器：`exportRSS`、`exportMarkdown`、`exportBibTeX` 各返回 Blob |
| `docs/bookmarks.css` | 180 | ⭐ 按钮、FAB、面板、移动卡片 + 粘性目录的样式 |

### 修改

| 文件 | 变更 |
|---|---|
| `docs/index.html` | 引入 bookmarks.css/js；加 iOS PWA meta |
| `docs/manifest.json` | theme_color → `#f59e0b`；icons 保留现有内联 SVG emoji（不引入新文件） |
| `docs/sw.js` | 在 `STATIC_ASSETS` 里加 `/bookmarks.js`、`/bookmarks.css`、`/exports.js`；`fetch` handler 对 `/daily/*.html` 与 `/weekly/*.html` 走 network-first + offline fallback |
| `generate_daily_pages.py:render_daily_html` | (a) 加 `<link rel="stylesheet" href="../bookmarks.css">` + `<script src="../bookmarks.js" defer>` + `<script src="../exports.js" defer>`；(b) `render_focus_item` / `render_item` / `render_core_section` 在 `<li>` 根节点加 `data-bookmark-key="{safe_text(link)}"`；(c) 加粘性目录 `<nav class="daily-toc-sticky">`；(d) 在内联 CSS 块补移动端字号/行距增强 |
| `weekly_summary.py` | 同 daily：脚本/样式引入、card 根节点 `data-bookmark-key`、粘性目录、移动 CSS |

---

## UI 详细规格

### ⭐ 按钮（每张 card）
- 位置：card 右上角，position absolute
- 尺寸：32×32 px 命中区，视觉 18×18 ⭐ 字符
- 样式：未收藏 `opacity:0.45 color:#9ca3af`；已收藏 `opacity:1 color:#f59e0b filter:drop-shadow(0 1px 2px rgba(245,158,11,0.45))`
- 已收藏的 card 整体加 `border-left: 3px solid #f59e0b` 与核心关注一致

### 手势
- **长按**：`pointerdown` → 350ms 内不动（阈值 10px）→ 触发 toggle + `navigator.vibrate?.(30)`
- **右滑**：`pointermove` → `dx > 50 && |dy| < 30` → 触发 toggle + 卡片右侧短金光动画（`@keyframes flash-bookmark`）
- 同时存在时只触发一次（用 `event.preventDefault()` 与 flag 互斥）
- 触发后 toast 顶部短提示"已收藏 / 已取消"，1.5s 自动消失

### FAB（floating action button）
- 位置：`position: fixed; bottom: 18px; right: 16px`
- 内容：`⭐ 收藏 <span class="badge">12</span>`
- 计数 0 时：变灰 + 文字"收藏"（无 badge）
- 点击 → 打开收藏面板

### 收藏面板（modal，移动全屏；桌面居中浮层 max-width 720px）
- Header：✕ 关闭、"我的收藏 (N)"、"📤 导出 ▾"（点击展开 RSS / MD / BibTeX 选项）
- Body：按 `source_date` 倒序分组：每组 `📅 2026-04-15 (3 篇)`，下面列每条收藏：标题（点击 → 在新 tab 打开 link）、journal · 域名、删除按钮
- Empty state：金色 ⭐ + "还没有收藏任何文章。在日报/周报里点击 ⭐ 或长按卡片即可。"

### 粘性目录（移动 ≤ 720px）
- `<nav class="daily-toc-sticky">` 由 **Python 模板**在 hero 区块之后渲染（不是 JS 注入），与现有 `daily-nav` 同级
- `position: sticky; top: 0`，CSS 在 `≤ 720px` 时显示、`≥ 721px` 时 `display: none`
- 锚点：`摘要 · 核心关注 · 完整速览`（核心关注无内容时由 Python 跳过该 `<a>`），允许横向滚动
- 桌面端右侧已有的 `.daily-toc` 不动

### PWA "添加到主屏幕"
- iOS Safari：`<meta name="apple-mobile-web-app-capable" content="yes">`、`<meta name="apple-mobile-web-app-status-bar-style" content="default">`、`<meta name="apple-mobile-web-app-title" content="文献追踪">`
- Android Chrome：`manifest.json` 已有 standalone display；只改 theme_color 为金色
- 离线缓存：`sw.js` 加 daily/weekly HTML 的 network-first + cache fallback；最多保留 14 天数据

---

## 导出格式

### RSS 2.0 (`bookmarks-YYYY-MM-DD.xml`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>我的文献收藏 · 2026-05-01</title>
    <link>https://hongyu-yu.github.io/literature-tracker/</link>
    <description>从 literature-tracker 导出的 12 篇收藏</description>
    <generator>literature-tracker bookmarks export</generator>
    <item>
      <title><![CDATA[二维范德华 NbOI2 中的室温铁电性 / Room-temperature ferroelectricity in 2D vdW NbOI2]]></title>
      <link>https://arxiv.org/abs/2604.11578</link>
      <description><![CDATA[在二维 NbOI2 薄层中观测到稳定的面外铁电翻转...]]></description>
      <pubDate>Wed, 15 Apr 2026 00:00:00 +0800</pubDate>
      <source>Nature</source>
      <guid isPermaLink="true">https://arxiv.org/abs/2604.11578</guid>
    </item>
    ...
  </channel>
</rss>
```

### Markdown (`bookmarks-YYYY-MM-DD.md`)
```markdown
# 我的文献收藏 · 2026-05-01（共 12 篇）

## 二维范德华 NbOI2 中的室温铁电性
**EN**：Room-temperature ferroelectricity in two-dimensional...
**期刊**：Nature  ·  收录日期：2026-04-15
**摘要**：在二维 NbOI2 薄层中观测到稳定的面外铁电翻转，矫顽场约 0.3 V/nm...
[原文 ↗](https://arxiv.org/abs/2604.11578)

---

## ...
```

### BibTeX (`bookmarks-YYYY-MM-DD.bib`)
- 启发式 1：URL 匹配 `arxiv.org/abs/(\S+)` → `@misc{arxiv:<id>, title={...}, author={...}, year={2026}, eprint={<id>}, archivePrefix={arXiv}, url={...}}`
- 启发式 2：其他 URL → `@misc{<short-hash>, title={...}, howpublished={\url{...}}, year={2026}, note={Journal: <journal>}}`
- 缺 author → `author={Unknown}`；缺 year → 用 source_date 取 4 位

---

## 关键代码骨架

`bookmarks.js`：

```js
const STORAGE_KEY = 'literature_bookmarks';

class BookmarkStore {
  constructor() { this.data = this._load(); }
  _load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch { return {}; }
  }
  _save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data)); }
  has(link) { return !!this.data[link]; }
  add(link, meta) { if (this.has(link)) return; this.data[link] = {...meta, added_at: Date.now()}; this._save(); this._fire(); }
  remove(link) { delete this.data[link]; this._save(); this._fire(); }
  toggle(link, meta) { return this.has(link) ? this.remove(link) || false : (this.add(link, meta), true); }
  count() { return Object.keys(this.data).length; }
  list() { return Object.entries(this.data).map(([link, m]) => ({link, ...m})); }
  _fire() { document.dispatchEvent(new CustomEvent('bookmarkschange', {detail: this.data})); }
}

class BookmarkUI {
  constructor(store) { this.store = store; }
  init() {
    this.attachToCards();
    this.bindGestures();
    this.renderFab();
    document.addEventListener('bookmarkschange', () => this.refreshAll());
  }
  attachToCards() {
    const sels = ['.daily-paper-card', '.daily-news-item', '.daily-core-card', '.weekly-core-card'];
    document.querySelectorAll(sels.join(',')).forEach(card => this._attach(card));
  }
  _attach(card) { /* extract metadata from DOM, inject ⭐ button */ }
  bindGestures() { /* pointerdown long-press + pointermove right-swipe */ }
  renderFab() { /* fixed bottom-right element */ }
  openPanel() { /* full-screen modal */ }
}

window.addEventListener('DOMContentLoaded', () => {
  const store = new BookmarkStore();
  const ui = new BookmarkUI(store);
  ui.init();
});
```

---

## 验证方式

1. **单元（浏览器内自测）**：`docs/test-bookmarks.html` 加载 bookmarks.js + 一组 mock cards，跑 ~15 个 console-assert 测试：add/remove/toggle/count/persist/migration/dedup
2. **集成**：在本地 `python3 -m http.server` 起 docs/ 目录，浏览器打开任意一篇 daily html，验证：
   - 每张卡片右上角有 ⭐
   - 长按 ≥ 350ms toggle 收藏（视觉 + localStorage 检查）
   - 右滑 toggle 收藏
   - FAB 实时计数
   - 面板能列出收藏并导出 RSS/MD/BibTeX，下载文件内容正确
3. **手机实测**：iOS Safari + Android Chrome 各测一次
4. **PWA**：iPhone 添加到主屏幕，确认 standalone 启动 + 离线打开最近一篇 daily 仍可用
5. **回归**：原有 `docs/index.html` 主页的 ⭐ 系统保持工作；旧 `literature_favorites` key 自动迁移；如有冲突的 ID 收藏，迁移逻辑日志写清

## 明确不做的事

- 跨设备同步（GitHub Gist / iCloud）
- JSON 导出格式
- 收藏分类 / 标签 / 备注
- 收藏内搜索
- 编辑（修改字段）已收藏内容
- BibTeX 通过 CrossRef API 补全字段
- 收藏分享 URL（拷链接给好友）
- 服务端 RSS endpoint（生成完整 feed）
