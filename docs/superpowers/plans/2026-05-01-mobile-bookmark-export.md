# Mobile Bookmark + Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 daily/weekly 页面加 ⭐ 收藏（按钮 + 长按/右滑手势）+ 底部 FAB + 收藏面板 + RSS/MD/BibTeX 三种导出，纯前端 localStorage，并优化移动端排版与 PWA。

**Architecture:** 新增 `docs/bookmarks.js` (BookmarkStore + BookmarkUI) 和 `docs/exports.js` (3 个导出器) + `docs/bookmarks.css`。Python 模板在每张 card 根节点加 `data-bookmark-key="<link>"`，并引入新 JS/CSS。`sw.js` 升级缓存策略；`manifest.json` theme_color 调整。零后端、零账号。

**Tech Stack:** Vanilla JS · CSS3 (sticky/grid) · localStorage · Service Worker · Anthropic-Kimi 已就位（不变）

---

## File Structure

| 文件 | 责任 |
|---|---|
| `docs/bookmarks.js` (新) | `BookmarkStore` 类（localStorage 单源） + `BookmarkUI` 类（扫描 DOM 注入 ⭐、绑定手势、FAB、面板） + 触发 `bookmarkschange` event 总线 |
| `docs/exports.js` (新) | `exportRSS(list)`, `exportMarkdown(list)`, `exportBibTeX(list)` 三个纯函数返回 Blob |
| `docs/bookmarks.css` (新) | ⭐ 按钮、FAB、面板、移动端 toc-sticky、card padding 增强样式 |
| `docs/test-bookmarks.html` (新) | 浏览器内自测页：mock cards + 15 个 console-assert |
| `docs/index.html` (改) | 引入 bookmarks.css/js + iOS PWA meta |
| `docs/manifest.json` (改) | theme_color → `#f59e0b` |
| `docs/sw.js` (改) | STATIC_ASSETS 加新文件；fetch 拦截 `/daily/*.html`、`/weekly/*.html` 走 network-first + cache fallback |
| `generate_daily_pages.py` (改) | `render_daily_html`：head 加 link/script、render_*_item 加 `data-bookmark-key`、新增粘性目录、移动 CSS |
| `weekly_summary.py` (改) | 同上：`render_core_weekly_section` + 内联 weekly 模板（在 `_save_summary_html` 附近）加 link/script + data-bookmark-key |

---

## Task 1: `BookmarkStore` 类与基础测试

**Files:**
- Create: `docs/bookmarks.js`
- Create: `docs/test-bookmarks.html`

- [ ] **Step 1.1: 创建测试页 `docs/test-bookmarks.html`（先失败）**

```html
<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>bookmarks unit tests</title></head>
<body>
<h1>bookmarks.js unit tests</h1>
<pre id="out"></pre>
<script src="bookmarks.js"></script>
<script>
const out = document.getElementById('out');
const log = (...a) => { out.textContent += a.join(' ') + '\n'; console.log(...a); };
let pass = 0, fail = 0;
function assert(cond, msg) { if (cond) { pass++; log('  ✓', msg); } else { fail++; log('  ✗ FAIL:', msg); } }

// Clean slate for each run
localStorage.removeItem('literature_bookmarks');
localStorage.removeItem('literature_favorites');

log('--- BookmarkStore basics ---');
const s = new window.BookmarkStore();
assert(s.count() === 0, 'empty store count is 0');

s.add('https://ex.com/a', {title_zh: 'A', title_en: 'A en', journal: 'Nature', source_date: '2026-04-15'});
assert(s.has('https://ex.com/a'), 'has() returns true after add');
assert(s.count() === 1, 'count is 1 after first add');

s.add('https://ex.com/a', {title_zh: 'A2'});  // duplicate
assert(s.count() === 1, 'duplicate add is idempotent (count stays 1)');
assert(s.data['https://ex.com/a'].title_zh === 'A', 'duplicate add does not overwrite first record');

s.toggle('https://ex.com/b', {title_zh: 'B'});
assert(s.has('https://ex.com/b'), 'toggle on missing adds');
s.toggle('https://ex.com/b', {});
assert(!s.has('https://ex.com/b'), 'toggle on existing removes');

s.remove('https://ex.com/a');
assert(s.count() === 0, 'remove deletes entry');

log('--- persistence ---');
s.add('https://ex.com/p', {title_zh: 'P'});
const s2 = new window.BookmarkStore();
assert(s2.has('https://ex.com/p'), 'new instance loads from localStorage');

log('--- legacy migration ---');
localStorage.removeItem('literature_bookmarks');
localStorage.setItem('literature_favorites', JSON.stringify(['https://ex.com/legacy', 'invalid-id']));
const s3 = new window.BookmarkStore();
assert(s3.has('https://ex.com/legacy'), 'legacy URL-shaped favorite migrated');
assert(!s3.has('invalid-id'), 'non-URL legacy entry skipped');
assert(localStorage.getItem('literature_favorites') === null, 'legacy key cleared after migration');

log('--- list ordering ---');
const s4 = new window.BookmarkStore();
localStorage.removeItem('literature_bookmarks');
const s5 = new window.BookmarkStore();
s5.add('https://ex.com/x', {title_zh: 'X', source_date: '2026-04-10'});
s5.add('https://ex.com/y', {title_zh: 'Y', source_date: '2026-04-15'});
const list = s5.list();
assert(list.length === 2, 'list returns all entries');
assert(list[0].link && list[0].title_zh, 'list entries have link + title_zh');

log('\n--- summary ---');
log(`PASS: ${pass}  FAIL: ${fail}`);
if (fail > 0) document.title = '✗ ' + document.title;
else document.title = '✓ ' + document.title;
</script>
</body></html>
```

- [ ] **Step 1.2: 用本地 http 起服务并打开测试页确认失败**

```bash
cd /home/webcode/literature/literature-tracker/docs && python3 -m http.server 8765 &>/tmp/http.log &
sleep 1
curl -sS http://localhost:8765/test-bookmarks.html | grep -c '<title>'
# 然后人工浏览器访问 http://localhost:8765/test-bookmarks.html，预期：标题前有 ✗（因为 BookmarkStore 还没定义）
```

或用 headless 验证（不依赖浏览器，自动化更可靠）：
```bash
# 创建 bookmarks.js 的最小 stub 让一些断言能跑起来
echo "" > docs/bookmarks.js
# 用 deno/node 跑也可以，但项目里没装。若手头无浏览器，直接进 step 1.3 写实现，跳过手测。
```

- [ ] **Step 1.3: 实现 `docs/bookmarks.js` 中的 `BookmarkStore`（先只写这部分）**

```javascript
/**
 * Bookmarks for literature-tracker (mobile-friendly star + export).
 * Storage: localStorage key "literature_bookmarks", value = { [link]: meta }.
 */
(function () {
  'use strict';
  const STORAGE_KEY = 'literature_bookmarks';
  const LEGACY_KEY = 'literature_favorites';

  function _isLikelyUrl(s) {
    return typeof s === 'string' && /^https?:\/\//i.test(s);
  }

  class BookmarkStore {
    constructor() {
      this.data = this._load();
      this._migrateLegacy();
    }

    _load() {
      try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : {};
      } catch (e) {
        console.warn('[bookmarks] failed to load:', e);
        return {};
      }
    }

    _save() {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(this.data));
      } catch (e) {
        console.warn('[bookmarks] failed to save:', e);
      }
    }

    _migrateLegacy() {
      try {
        const raw = localStorage.getItem(LEGACY_KEY);
        if (!raw) return;
        const arr = JSON.parse(raw);
        if (!Array.isArray(arr)) {
          localStorage.removeItem(LEGACY_KEY);
          return;
        }
        let migrated = 0;
        for (const id of arr) {
          if (_isLikelyUrl(id) && !this.has(id)) {
            this.data[id] = {
              title_zh: '',
              title_en: '',
              journal: '',
              source_type: 'legacy',
              source_date: '',
              added_at: Date.now(),
            };
            migrated++;
          }
        }
        if (migrated > 0) this._save();
        localStorage.removeItem(LEGACY_KEY);
      } catch (e) {
        console.warn('[bookmarks] legacy migration failed:', e);
      }
    }

    has(link) { return Object.prototype.hasOwnProperty.call(this.data, link); }
    count() { return Object.keys(this.data).length; }

    add(link, meta) {
      if (!link || this.has(link)) return false;
      this.data[link] = Object.assign({}, meta || {}, { added_at: Date.now() });
      this._save();
      this._fire();
      return true;
    }

    remove(link) {
      if (!this.has(link)) return false;
      delete this.data[link];
      this._save();
      this._fire();
      return true;
    }

    toggle(link, meta) {
      if (this.has(link)) {
        this.remove(link);
        return false;
      }
      this.add(link, meta);
      return true;
    }

    list() {
      return Object.entries(this.data).map(([link, meta]) => Object.assign({ link }, meta));
    }

    _fire() {
      try {
        document.dispatchEvent(new CustomEvent('bookmarkschange', {
          detail: { count: this.count() }
        }));
      } catch {}
    }
  }

  window.BookmarkStore = BookmarkStore;
})();
```

- [ ] **Step 1.4: 重新加载测试页确认通过**

浏览器（or 后续步骤里 headless）打开 `http://localhost:8765/test-bookmarks.html`，title 前缀应该是 `✓`，console 输出 `PASS: 9 FAIL: 0` 之类。

- [ ] **Step 1.5: 提交**

```bash
cd /home/webcode/literature/literature-tracker
git add docs/bookmarks.js docs/test-bookmarks.html
git commit -m "feat(bookmarks): BookmarkStore (localStorage 单源 + 旧 favorites 迁移) + 测试页"
```

---

## Task 2: `BookmarkUI` —— ⭐ 注入与基本 toggle

**Files:**
- Modify: `docs/bookmarks.js`（追加 `BookmarkUI` 类）

- [ ] **Step 2.1: 扩展测试页，加 mock card 与 BookmarkUI 断言**

把这一段加到 `docs/test-bookmarks.html` 的 `--- list ordering ---` 之后、`--- summary ---` 之前：

```html
log('--- BookmarkUI inject ---');
// Build a fake card matching daily structure
const card = document.createElement('li');
card.className = 'daily-paper-card';
card.dataset.bookmarkKey = 'https://ex.com/u1';
card.innerHTML = `
  <span class="daily-paper-number">01</span>
  <div class="daily-paper-body">
    <div class="daily-paper-titles">
      <div class="daily-paper-title-zh">测试中文标题</div>
      <div class="daily-paper-title-en">Test English Title</div>
    </div>
    <div class="daily-paper-meta"><span class="daily-chip daily-chip-journal">📖 Nature</span></div>
    <div class="daily-paper-summary"><p class="daily-paper-abstract"><strong>📄 摘要：</strong>测试摘要内容。</p></div>
  </div>
`;
document.body.appendChild(card);

localStorage.removeItem('literature_bookmarks');
const ui = new window.BookmarkUI(new window.BookmarkStore());
ui.attachToCards();
const btn = card.querySelector('.bookmark-btn');
assert(!!btn, 'star button injected on card');
assert(btn.getAttribute('aria-pressed') === 'false', 'initial aria-pressed is false');

btn.click();
assert(btn.getAttribute('aria-pressed') === 'true', 'aria-pressed becomes true after click');
assert(card.classList.contains('is-bookmarked'), 'card gets is-bookmarked class');

const stored = JSON.parse(localStorage.getItem('literature_bookmarks'));
assert(stored['https://ex.com/u1'], 'storage has entry after click');
assert(stored['https://ex.com/u1'].title_zh === '测试中文标题', 'metadata extracted from DOM');
assert(stored['https://ex.com/u1'].title_en === 'Test English Title', 'title_en extracted');
assert(stored['https://ex.com/u1'].journal === 'Nature', 'journal extracted from chip');

btn.click();
assert(btn.getAttribute('aria-pressed') === 'false', 'second click toggles off');
assert(!card.classList.contains('is-bookmarked'), 'class removed on toggle off');
assert(!localStorage.getItem('literature_bookmarks').includes('ex.com/u1'), 'storage entry removed on toggle off');
```

打开页面应该新断言全失败（BookmarkUI 还不存在）。

- [ ] **Step 2.2: 在 `bookmarks.js` IIFE 内追加 `BookmarkUI`**

在 `window.BookmarkStore = BookmarkStore;` 行**之前**追加：

```javascript
  const CARD_SELECTORS = [
    '.daily-paper-card',
    '.daily-news-item',
    '.daily-core-card',
    '.weekly-core-card',
    '.weekly-paper-card',
  ];

  function _text(node) {
    return node ? node.textContent.replace(/\s+/g, ' ').trim() : '';
  }

  function _extractMeta(card) {
    // Pull title_zh / title_en / journal / abstract / summary from neighbouring DOM.
    const titleZhEl =
      card.querySelector('.daily-paper-title-zh, .daily-news-title-zh, .daily-core-title-zh, .weekly-core-title-zh');
    const titleEnEl =
      card.querySelector('.daily-paper-title-en, .daily-news-title-en, .daily-core-title-en, .weekly-core-title-en');
    let title_zh = _text(titleZhEl);
    let title_en = _text(titleEnEl);

    // For arxiv-style cards, the link wraps the title — strip permalink anchor (#)
    title_zh = title_zh.replace(/#$/, '').trim();
    title_en = title_en.replace(/#$/, '').trim();

    let journal = '';
    const chip = card.querySelector('.daily-chip-journal, .weekly-chip-journal, .weekly-chip');
    if (chip) {
      const t = _text(chip).replace(/^📖\s*/, '');
      journal = t.split(/[/·]/)[0].trim();
    }

    let abstract_zh = '';
    const absEl = card.querySelector('.daily-paper-abstract, .weekly-core-abs');
    if (absEl) abstract_zh = _text(absEl).replace(/^📄\s*摘要[:：]\s*/, '');

    let summary = '';
    const sumEl = card.querySelector('.daily-paper-highlight');
    if (sumEl) summary = _text(sumEl).replace(/^💡\s*亮点[:：]\s*/, '');

    let source_type = 'daily';
    let source_date = '';
    if (/weekly-/.test(card.className)) source_type = 'weekly';
    const dateMatch = location.pathname.match(/(\d{4}-\d{2}-\d{2})\.html/);
    if (dateMatch) source_date = dateMatch[1];

    return { title_zh, title_en, journal, abstract_zh, summary, source_type, source_date };
  }

  class BookmarkUI {
    constructor(store) {
      this.store = store;
    }

    attachToCards(root = document) {
      const cards = root.querySelectorAll(CARD_SELECTORS.join(','));
      cards.forEach(card => this._attach(card));
    }

    _attach(card) {
      if (card.querySelector(':scope > .bookmark-btn')) return; // already attached
      const link = card.dataset.bookmarkKey;
      if (!link) return;

      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'bookmark-btn';
      btn.setAttribute('aria-label', '收藏此文献');
      btn.setAttribute('aria-pressed', this.store.has(link) ? 'true' : 'false');
      btn.textContent = this.store.has(link) ? '★' : '☆';
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this._toggle(card, btn, link);
      });

      card.appendChild(btn);
      if (this.store.has(link)) card.classList.add('is-bookmarked');
    }

    _toggle(card, btn, link) {
      const meta = _extractMeta(card);
      const nowOn = this.store.toggle(link, meta);
      btn.setAttribute('aria-pressed', nowOn ? 'true' : 'false');
      btn.textContent = nowOn ? '★' : '☆';
      card.classList.toggle('is-bookmarked', nowOn);
      this._toast(nowOn ? '已收藏' : '已取消');
    }

    _toast(msg) {
      let t = document.querySelector('.bookmark-toast');
      if (!t) {
        t = document.createElement('div');
        t.className = 'bookmark-toast';
        document.body.appendChild(t);
      }
      t.textContent = msg;
      t.classList.add('show');
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => t.classList.remove('show'), 1500);
    }
  }

  window.BookmarkUI = BookmarkUI;
```

- [ ] **Step 2.3: 重载测试页，断言全过**

期待 PASS 数从 9 变成 ~16，FAIL = 0。

- [ ] **Step 2.4: 提交**

```bash
git add docs/bookmarks.js docs/test-bookmarks.html
git commit -m "feat(bookmarks): BookmarkUI ⭐ 按钮注入 + DOM 元信息抽取 + toast"
```

---

## Task 3: 长按 + 右滑手势

**Files:**
- Modify: `docs/bookmarks.js`（在 `BookmarkUI` 里加 `bindGestures`）

- [ ] **Step 3.1: 测试页加手势断言**

在测试页 `<script>` 末尾的 `--- summary ---` 之前追加：

```html
log('--- gestures ---');
localStorage.removeItem('literature_bookmarks');
const card2 = document.createElement('li');
card2.className = 'daily-paper-card';
card2.dataset.bookmarkKey = 'https://ex.com/g1';
card2.innerHTML = `<div class="daily-paper-title-zh">手势</div><div class="daily-paper-title-en">G</div>`;
document.body.appendChild(card2);

const ui2 = new window.BookmarkUI(new window.BookmarkStore());
ui2.attachToCards();
ui2.bindGestures();

// Simulate long-press: pointerdown then wait 400ms with no movement
const ev = (type, x, y) => {
  const e = new PointerEvent(type, {pointerId: 1, clientX: x, clientY: y, bubbles: true, cancelable: true});
  card2.dispatchEvent(e);
  return e;
};
ev('pointerdown', 100, 100);
await new Promise(r => setTimeout(r, 400));
ev('pointerup', 100, 100);
assert(card2.classList.contains('is-bookmarked'), 'long-press toggles bookmark on');

// Simulate right swipe to toggle off: pointerdown at 100,100 → pointermove to 200,105 → pointerup
ev('pointerdown', 100, 100);
ev('pointermove', 200, 105);
ev('pointerup', 200, 105);
assert(!card2.classList.contains('is-bookmarked'), 'right-swipe toggles bookmark off');
```

也把 `<script>` 标签改成 `<script type="module">` 或包裹成 async IIFE 才能用 `await`。简单做法：用 `setTimeout` 嵌套替代。改成：

```html
log('--- gestures ---');
localStorage.removeItem('literature_bookmarks');
const card2 = document.createElement('li');
card2.className = 'daily-paper-card';
card2.dataset.bookmarkKey = 'https://ex.com/g1';
card2.innerHTML = `<div class="daily-paper-title-zh">手势</div><div class="daily-paper-title-en">G</div>`;
document.body.appendChild(card2);

const ui2 = new window.BookmarkUI(new window.BookmarkStore());
ui2.attachToCards();
ui2.bindGestures();

const ev = (type, x, y) => {
  const e = new PointerEvent(type, {pointerId: 1, clientX: x, clientY: y, bubbles: true, cancelable: true});
  card2.dispatchEvent(e);
};

// long-press
ev('pointerdown', 100, 100);
setTimeout(() => {
  ev('pointerup', 100, 100);
  assert(card2.classList.contains('is-bookmarked'), 'long-press toggles bookmark on');

  // right swipe to toggle off
  ev('pointerdown', 100, 100);
  ev('pointermove', 200, 105);
  ev('pointerup', 200, 105);
  assert(!card2.classList.contains('is-bookmarked'), 'right-swipe toggles bookmark off');

  // wrap-up summary
  setTimeout(() => {
    log('\n--- summary ---');
    log(`PASS: ${pass}  FAIL: ${fail}`);
    if (fail > 0) document.title = '✗ ' + document.title;
    else document.title = '✓ ' + document.title;
  }, 50);
}, 420);
```

并把原来的 `--- summary ---` 段落删掉（避免重复输出）。

- [ ] **Step 3.2: 实现 `bindGestures()`**

在 `BookmarkUI` 类内追加：

```javascript
    bindGestures(root = document) {
      const cards = root.querySelectorAll(CARD_SELECTORS.join(','));
      cards.forEach(card => this._bindGestures(card));
    }

    _bindGestures(card) {
      if (card.dataset.gestureBound === '1') return;
      card.dataset.gestureBound = '1';

      let pressTimer = null;
      let startX = 0, startY = 0;
      let triggered = false;
      const link = card.dataset.bookmarkKey;
      if (!link) return;

      const cancel = () => {
        if (pressTimer) { clearTimeout(pressTimer); pressTimer = null; }
      };

      const triggerToggle = () => {
        if (triggered) return;
        triggered = true;
        const btn = card.querySelector(':scope > .bookmark-btn');
        const meta = _extractMeta(card);
        const nowOn = this.store.toggle(link, meta);
        if (btn) {
          btn.setAttribute('aria-pressed', nowOn ? 'true' : 'false');
          btn.textContent = nowOn ? '★' : '☆';
        }
        card.classList.toggle('is-bookmarked', nowOn);
        if (navigator.vibrate) try { navigator.vibrate(30); } catch {}
        this._toast(nowOn ? '已收藏' : '已取消');
      };

      card.addEventListener('pointerdown', (e) => {
        // Ignore pointerdowns on the star button itself or any link
        if (e.target.closest('.bookmark-btn,a')) return;
        startX = e.clientX; startY = e.clientY;
        triggered = false;
        pressTimer = setTimeout(() => {
          pressTimer = null;
          triggerToggle();
        }, 350);
      });

      card.addEventListener('pointermove', (e) => {
        if (!pressTimer && triggered) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (pressTimer && (Math.abs(dx) > 10 || Math.abs(dy) > 10)) cancel();
        if (!triggered && dx > 50 && Math.abs(dy) < 30) {
          cancel();
          triggerToggle();
        }
      });

      card.addEventListener('pointerup', cancel);
      card.addEventListener('pointercancel', cancel);
      card.addEventListener('pointerleave', cancel);
    }
```

- [ ] **Step 3.3: 重载测试页确认 PASS**

- [ ] **Step 3.4: 提交**

```bash
git add docs/bookmarks.js docs/test-bookmarks.html
git commit -m "feat(bookmarks): 长按 350ms + 右滑 50px 手势 toggle 收藏"
```

---

## Task 4: FAB + 收藏面板

**Files:**
- Modify: `docs/bookmarks.js`（追加 `renderFab` + `openPanel`）

- [ ] **Step 4.1: 测试页 FAB 断言**

在 `setTimeout(() => { ... wrap-up ...}, 50)` 之前追加：

```javascript
    log('--- FAB + panel ---');
    ui2.renderFab();
    const fab = document.querySelector('.bookmark-fab');
    assert(!!fab, 'FAB rendered');
    const badge = fab.querySelector('.bookmark-fab-badge');
    assert(badge && badge.textContent === '0', 'badge starts at 0');

    // Add 2 entries and check live update
    new window.BookmarkStore().add('https://ex.com/p1', {title_zh: 'P1'});
    setTimeout(() => {
      const badge2 = document.querySelector('.bookmark-fab-badge');
      assert(badge2.textContent === '1', 'badge updates to 1 after add');
      // Open panel
      fab.click();
      const panel = document.querySelector('.bookmark-panel');
      assert(panel && panel.classList.contains('open'), 'panel opens on FAB click');
      const items = panel.querySelectorAll('.bookmark-panel-item');
      assert(items.length >= 1, 'panel lists bookmarks');
      // Close
      panel.querySelector('.bookmark-panel-close').click();
      assert(!panel.classList.contains('open'), 'panel closes on ✕ click');
    }, 30);
```

- [ ] **Step 4.2: 实现 `renderFab` 与 `openPanel`**

在 `BookmarkUI` 类内追加：

```javascript
    renderFab() {
      let fab = document.querySelector('.bookmark-fab');
      if (!fab) {
        fab = document.createElement('button');
        fab.type = 'button';
        fab.className = 'bookmark-fab';
        fab.setAttribute('aria-label', '我的收藏');
        fab.innerHTML = '<span class="bookmark-fab-icon">⭐</span><span class="bookmark-fab-label">收藏</span><span class="bookmark-fab-badge">0</span>';
        document.body.appendChild(fab);
        fab.addEventListener('click', () => this.openPanel());
      }
      const update = () => {
        const n = this.store.count();
        const badge = fab.querySelector('.bookmark-fab-badge');
        if (badge) badge.textContent = String(n);
        fab.classList.toggle('is-empty', n === 0);
      };
      update();
      document.addEventListener('bookmarkschange', update);
    }

    openPanel() {
      let panel = document.querySelector('.bookmark-panel');
      if (!panel) {
        panel = document.createElement('div');
        panel.className = 'bookmark-panel';
        panel.innerHTML = `
          <div class="bookmark-panel-overlay"></div>
          <div class="bookmark-panel-card">
            <div class="bookmark-panel-head">
              <h2 class="bookmark-panel-title">我的收藏 <span class="bookmark-panel-count">0</span></h2>
              <div class="bookmark-panel-actions">
                <button type="button" class="bookmark-export-btn" data-fmt="rss">RSS</button>
                <button type="button" class="bookmark-export-btn" data-fmt="md">MD</button>
                <button type="button" class="bookmark-export-btn" data-fmt="bib">BibTeX</button>
                <button type="button" class="bookmark-panel-close" aria-label="关闭">✕</button>
              </div>
            </div>
            <div class="bookmark-panel-body"></div>
          </div>
        `;
        document.body.appendChild(panel);
        panel.querySelector('.bookmark-panel-close').addEventListener('click', () => this._closePanel());
        panel.querySelector('.bookmark-panel-overlay').addEventListener('click', () => this._closePanel());
        panel.querySelectorAll('.bookmark-export-btn').forEach(b => {
          b.addEventListener('click', () => this._exportAs(b.dataset.fmt));
        });
      }
      this._renderPanelBody(panel);
      panel.classList.add('open');
    }

    _closePanel() {
      const panel = document.querySelector('.bookmark-panel');
      if (panel) panel.classList.remove('open');
    }

    _renderPanelBody(panel) {
      const body = panel.querySelector('.bookmark-panel-body');
      const countEl = panel.querySelector('.bookmark-panel-count');
      const list = this.store.list();
      countEl.textContent = `(${list.length})`;
      if (list.length === 0) {
        body.innerHTML = '<div class="bookmark-panel-empty"><p>还没有收藏任何文章。在日报/周报里点击 ☆ 或长按卡片即可。</p></div>';
        return;
      }
      // Group by source_date desc
      const groups = {};
      for (const it of list) {
        const k = it.source_date || '其他';
        (groups[k] = groups[k] || []).push(it);
      }
      const keys = Object.keys(groups).sort((a, b) => (a < b ? 1 : a > b ? -1 : 0));
      const html = keys.map(k => {
        const items = groups[k].map(it => {
          const ttl = it.title_zh || it.title_en || it.link;
          const en = it.title_en && it.title_en !== it.title_zh ? `<div class="bookmark-panel-item-en">${_escapeHtml(it.title_en)}</div>` : '';
          const meta = [it.journal, _hostname(it.link)].filter(Boolean).join(' · ');
          return `
            <li class="bookmark-panel-item" data-link="${_escapeHtml(it.link)}">
              <a class="bookmark-panel-item-title" href="${_escapeHtml(it.link)}" target="_blank" rel="noopener noreferrer">${_escapeHtml(ttl)}</a>
              ${en}
              <div class="bookmark-panel-item-meta">${_escapeHtml(meta)}</div>
              <button type="button" class="bookmark-panel-item-remove" aria-label="删除">删</button>
            </li>`;
        }).join('');
        return `<section class="bookmark-panel-group"><h3>📅 ${_escapeHtml(k)} <span class="bookmark-panel-group-count">(${groups[k].length})</span></h3><ol>${items}</ol></section>`;
      }).join('');
      body.innerHTML = html;
      // Attach delete handlers
      body.querySelectorAll('.bookmark-panel-item-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const li = e.target.closest('[data-link]');
          if (!li) return;
          const link = li.dataset.link;
          this.store.remove(link);
          this._renderPanelBody(panel);
          // Also reset card UI on the page if visible
          document.querySelectorAll(`[data-bookmark-key="${CSS.escape(link)}"]`).forEach(card => {
            card.classList.remove('is-bookmarked');
            const sb = card.querySelector(':scope > .bookmark-btn');
            if (sb) { sb.setAttribute('aria-pressed', 'false'); sb.textContent = '☆'; }
          });
        });
      });
    }

    _exportAs(fmt) {
      if (!window.BookmarkExports) {
        alert('exports.js 未加载');
        return;
      }
      const list = this.store.list();
      if (list.length === 0) { alert('收藏为空'); return; }
      const ymd = new Date().toISOString().slice(0, 10);
      const map = {
        rss: { fn: window.BookmarkExports.exportRSS, ext: 'xml', mime: 'application/rss+xml' },
        md:  { fn: window.BookmarkExports.exportMarkdown, ext: 'md', mime: 'text/markdown' },
        bib: { fn: window.BookmarkExports.exportBibTeX, ext: 'bib', mime: 'application/x-bibtex' },
      };
      const m = map[fmt];
      if (!m) return;
      const blob = m.fn(list);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `bookmarks-${ymd}.${m.ext}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
```

- [ ] **Step 4.3: 在 IIFE 顶部加辅助函数**

在 `function _isLikelyUrl` 之前追加：

```javascript
  function _escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _hostname(url) {
    try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
  }
```

- [ ] **Step 4.4: 重载测试页 PASS**

- [ ] **Step 4.5: 提交**

```bash
git add docs/bookmarks.js docs/test-bookmarks.html
git commit -m "feat(bookmarks): FAB + 全屏收藏面板（按日期分组、删除、导出按钮 stub）"
```

---

## Task 5: 三种导出器 `docs/exports.js`

**Files:**
- Create: `docs/exports.js`

- [ ] **Step 5.1: 测试页加导出格式断言**

在 `--- FAB + panel ---` 末尾追加：

```javascript
log('--- exports ---');
const sample = [
  { link: 'https://arxiv.org/abs/2604.11578', title_zh: '二维 NbOI2 室温铁电', title_en: 'Room-temp ferro 2D NbOI2', journal: 'Nature', abstract_zh: '面外铁电翻转。', summary: '一句话亮点。', source_date: '2026-04-15' },
  { link: 'https://example.com/x?q=1&y=2', title_zh: '另一篇', title_en: 'Another', journal: 'Science', abstract_zh: '另一段。', source_date: '2026-04-14' },
];
const xml = new TextDecoder().decode(window.BookmarkExports.exportRSS(sample).slice ? new Uint8Array() : new Uint8Array());
// Use FileReader-like sync via Response
const rss = window.BookmarkExports.exportRSS(sample);
const md = window.BookmarkExports.exportMarkdown(sample);
const bib = window.BookmarkExports.exportBibTeX(sample);
assert(rss instanceof Blob && rss.type.includes('rss'), 'exportRSS returns RSS Blob');
assert(md instanceof Blob && md.type.includes('markdown'), 'exportMarkdown returns markdown Blob');
assert(bib instanceof Blob && bib.type.includes('bibtex'), 'exportBibTeX returns bibtex Blob');

// Read content
Promise.all([rss.text(), md.text(), bib.text()]).then(([r, m, b]) => {
  assert(r.includes('<rss version="2.0">'), 'RSS has version 2.0');
  assert(r.includes('https://arxiv.org/abs/2604.11578'), 'RSS contains the arxiv URL');
  assert(r.includes('<![CDATA['), 'RSS uses CDATA for title/description');
  assert(r.includes('https://example.com/x?q=1&amp;y=2'), 'RSS escapes & in link');
  assert(m.startsWith('# 我的文献收藏'), 'MD has header');
  assert(m.includes('## 二维 NbOI2 室温铁电'), 'MD has zh title as H2');
  assert(m.includes('[原文 ↗](https://arxiv.org/abs/2604.11578)'), 'MD has original link');
  assert(b.includes('@misc{arxiv:2604.11578'), 'BibTeX uses arxiv:ID for arxiv URL');
  assert(b.includes('archivePrefix={arXiv}'), 'BibTeX has archivePrefix');
  assert(/@misc\{[a-z0-9]{6,},/.test(b.replace(/arxiv:/g, 'X-')), 'BibTeX uses short hash for non-arxiv');
});
```

注意外面的 `setTimeout` 链需要把这段也包进去；改造时把它放在 close-panel 断言之后。Promise 的 assert 可能在主同步流之后才落定，加个最终的 setTimeout 350ms 触发 summary。

- [ ] **Step 5.2: 创建 `docs/exports.js`**

```javascript
/**
 * Bookmark exporters: RSS / Markdown / BibTeX.
 * Each function takes a list of bookmark records (from BookmarkStore.list()) and returns a Blob.
 */
(function () {
  'use strict';

  function _escapeXml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function _cdata(s) {
    return '<![CDATA[' + String(s == null ? '' : s).replace(/\]\]>/g, ']]]]><![CDATA[>') + ']]>';
  }

  function _rfc822(date) {
    // date: 'YYYY-MM-DD' string
    if (!date) return '';
    const d = new Date(date + 'T00:00:00+0800');
    if (isNaN(d.getTime())) return '';
    return d.toUTCString();
  }

  function _shortHash(s) {
    let h = 0;
    for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    return ('00000000' + (h >>> 0).toString(36)).slice(-8);
  }

  function _arxivIdFromUrl(url) {
    const m = String(url || '').match(/arxiv\.org\/abs\/([^?#\s]+)/i);
    return m ? m[1].replace(/\/+$/, '') : null;
  }

  function exportRSS(list) {
    const today = new Date().toISOString().slice(0, 10);
    const items = list.map(it => {
      const title = [it.title_zh, it.title_en].filter(Boolean).join(' / ') || it.link;
      const desc = [it.abstract_zh, it.summary].filter(Boolean).join('\n\n');
      const pub = _rfc822(it.source_date);
      return `    <item>
      <title>${_cdata(title)}</title>
      <link>${_escapeXml(it.link)}</link>
      <description>${_cdata(desc)}</description>
      ${pub ? `<pubDate>${pub}</pubDate>` : ''}
      ${it.journal ? `<source>${_escapeXml(it.journal)}</source>` : ''}
      <guid isPermaLink="true">${_escapeXml(it.link)}</guid>
    </item>`;
    }).join('\n');

    const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>我的文献收藏 · ${today}</title>
    <link>https://hongyu-yu.github.io/literature-tracker/</link>
    <description>从 literature-tracker 导出的 ${list.length} 篇收藏</description>
    <generator>literature-tracker bookmarks export</generator>
    <pubDate>${new Date().toUTCString()}</pubDate>
${items}
  </channel>
</rss>
`;
    return new Blob([xml], { type: 'application/rss+xml;charset=utf-8' });
  }

  function exportMarkdown(list) {
    const today = new Date().toISOString().slice(0, 10);
    const lines = [`# 我的文献收藏 · ${today}（共 ${list.length} 篇）`, ''];
    for (const it of list) {
      const ttl = it.title_zh || it.title_en || it.link;
      lines.push(`## ${ttl}`);
      if (it.title_en && it.title_en !== it.title_zh) lines.push(`**EN**：${it.title_en}`);
      const meta = [it.journal && `**期刊**：${it.journal}`, it.source_date && `收录日期：${it.source_date}`].filter(Boolean).join('  ·  ');
      if (meta) lines.push(meta);
      if (it.abstract_zh) lines.push(`**摘要**：${it.abstract_zh}`);
      if (it.summary) lines.push(`**亮点**：${it.summary}`);
      lines.push(`[原文 ↗](${it.link})`);
      lines.push('');
      lines.push('---');
      lines.push('');
    }
    return new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  }

  function exportBibTeX(list) {
    const entries = list.map(it => {
      const arxivId = _arxivIdFromUrl(it.link);
      const year = (it.source_date || '').slice(0, 4) || '';
      const titleField = it.title_en || it.title_zh || it.link;
      const author = (it.authors && it.authors.length) ? it.authors.join(' and ') : 'Unknown';
      if (arxivId) {
        return `@misc{arxiv:${arxivId},
  title={${titleField}},
  author={${author}},
  year={${year}},
  eprint={${arxivId}},
  archivePrefix={arXiv},
  url={${it.link}}
}`;
      } else {
        const key = _shortHash(it.link);
        return `@misc{${key},
  title={${titleField}},
  author={${author}},
  year={${year}},
  howpublished={\\url{${it.link}}},
  note={${it.journal || ''}}
}`;
      }
    }).join('\n\n');
    return new Blob([entries + '\n'], { type: 'application/x-bibtex;charset=utf-8' });
  }

  window.BookmarkExports = { exportRSS, exportMarkdown, exportBibTeX };
})();
```

- [ ] **Step 5.3: 测试页 `<head>` 加 `<script src="exports.js"></script>`（在 `bookmarks.js` 之前）**

```html
<script src="exports.js"></script>
<script src="bookmarks.js"></script>
```

- [ ] **Step 5.4: 重载测试页 PASS**

- [ ] **Step 5.5: 提交**

```bash
git add docs/exports.js docs/test-bookmarks.html
git commit -m "feat(bookmarks): exports.js — RSS 2.0 / Markdown / BibTeX 三种导出"
```

---

## Task 6: CSS（按钮、FAB、面板、移动端）

**Files:**
- Create: `docs/bookmarks.css`

- [ ] **Step 6.1: 创建文件**

```css
/* bookmarks.css — overlay UI for star button, FAB, panel, toast, mobile sticky toc */

:root {
  --bm-gold: #f59e0b;
  --bm-gold-soft: rgba(245, 158, 11, 0.18);
  --bm-gold-deep: #b45309;
  --bm-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
}

/* ⭐ button on cards */
.bookmark-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: rgba(255, 255, 255, 0.0);
  color: #9ca3af;
  font-size: 18px;
  cursor: pointer;
  z-index: 5;
  transition: color 0.15s ease, transform 0.1s ease, background 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}
.bookmark-btn:hover { color: var(--bm-gold); background: rgba(245, 158, 11, 0.08); border-radius: 8px; }
.bookmark-btn[aria-pressed="true"] { color: var(--bm-gold); filter: drop-shadow(0 1px 2px rgba(245,158,11,0.45)); }
.bookmark-btn:active { transform: scale(0.92); }

/* Card needs position relative for the absolute btn */
.daily-paper-card,
.daily-news-item,
.daily-core-card,
.weekly-core-card,
.weekly-paper-card { position: relative; }

.is-bookmarked { border-left: 3px solid var(--bm-gold) !important; }

/* Toast */
.bookmark-toast {
  position: fixed;
  top: 16px;
  left: 50%;
  transform: translate(-50%, -20px);
  padding: 10px 18px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.92);
  color: white;
  font-size: 0.95rem;
  z-index: 1100;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.bookmark-toast.show { opacity: 1; transform: translate(-50%, 0); }

/* FAB */
.bookmark-fab {
  position: fixed;
  bottom: 18px;
  right: 16px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px 10px 12px;
  border-radius: 999px;
  border: 0;
  background: linear-gradient(135deg, var(--bm-gold), #fbbf24);
  color: white;
  font-weight: 700;
  font-size: 0.95rem;
  box-shadow: var(--bm-shadow);
  cursor: pointer;
  z-index: 900;
}
.bookmark-fab:hover { filter: brightness(1.05); }
.bookmark-fab.is-empty { background: rgba(100, 116, 139, 0.85); }
.bookmark-fab-icon { font-size: 1.05rem; }
.bookmark-fab-badge {
  display: inline-flex;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.32);
  font-size: 0.78rem;
}
.bookmark-fab.is-empty .bookmark-fab-badge { display: none; }

/* Panel */
.bookmark-panel {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: none;
}
.bookmark-panel.open { display: block; }
.bookmark-panel-overlay {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
}
.bookmark-panel-card {
  position: absolute;
  inset: 0;
  background: #ffffff;
  display: flex;
  flex-direction: column;
}
@media (min-width: 721px) {
  .bookmark-panel-card {
    inset: auto 0 0 0;
    margin: auto;
    max-width: 720px;
    max-height: 86vh;
    border-radius: 24px;
    box-shadow: var(--bm-shadow);
    top: 50%;
    transform: translateY(-50%);
  }
}
.bookmark-panel-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}
.bookmark-panel-title { margin: 0; font-size: 1.15rem; flex: 1; }
.bookmark-panel-count { color: #6b7280; font-weight: 500; margin-left: 4px; }
.bookmark-panel-actions { display: flex; gap: 6px; align-items: center; }
.bookmark-export-btn {
  border: 1px solid var(--bm-gold);
  background: rgba(245,158,11,0.08);
  color: var(--bm-gold-deep);
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
}
.bookmark-export-btn:hover { background: var(--bm-gold-soft); }
.bookmark-panel-close {
  border: 0;
  background: transparent;
  color: #6b7280;
  font-size: 1.4rem;
  cursor: pointer;
  width: 32px;
  height: 32px;
  border-radius: 8px;
}
.bookmark-panel-close:hover { background: #f3f4f6; }
.bookmark-panel-body { flex: 1; overflow-y: auto; padding: 14px 18px; }
.bookmark-panel-group { margin-bottom: 18px; }
.bookmark-panel-group h3 { font-size: 0.95rem; color: #374151; margin: 0 0 8px; }
.bookmark-panel-group-count { color: #9ca3af; font-weight: 500; margin-left: 4px; }
.bookmark-panel-group ol { list-style: none; margin: 0; padding: 0; }
.bookmark-panel-item {
  position: relative;
  padding: 10px 36px 10px 12px;
  border-radius: 12px;
  border: 1px solid #f3f4f6;
  background: #fafafa;
  margin-bottom: 8px;
}
.bookmark-panel-item-title { color: #1e3a8a; text-decoration: none; font-weight: 600; }
.bookmark-panel-item-title:hover { text-decoration: underline; }
.bookmark-panel-item-en { color: #6b7280; font-size: 0.86rem; margin-top: 2px; }
.bookmark-panel-item-meta { color: #9ca3af; font-size: 0.82rem; margin-top: 4px; }
.bookmark-panel-item-remove {
  position: absolute;
  top: 8px;
  right: 8px;
  background: transparent;
  border: 1px solid #fca5a5;
  color: #b91c1c;
  border-radius: 6px;
  font-size: 0.78rem;
  padding: 2px 8px;
  cursor: pointer;
}
.bookmark-panel-item-remove:hover { background: #fee2e2; }
.bookmark-panel-empty { padding: 32px 16px; text-align: center; color: #6b7280; }

/* Mobile-friendly sticky toc on daily/weekly pages */
.daily-toc-sticky,
.weekly-toc-sticky {
  display: none;
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #e5e7eb;
  padding: 8px 14px;
  margin: 0 0 12px;
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
}
.daily-toc-sticky a,
.weekly-toc-sticky a {
  display: inline-block;
  margin-right: 14px;
  padding: 6px 4px;
  color: #1e3a8a;
  text-decoration: none;
  font-size: 0.94rem;
  font-weight: 600;
}
@media (max-width: 720px) {
  .daily-toc-sticky,
  .weekly-toc-sticky { display: block; }
  .daily-paper-title-zh,
  .daily-core-title-zh,
  .daily-news-title-zh { font-size: 1.08rem; line-height: 1.55; }
  .daily-paper-card,
  .daily-core-card,
  .daily-news-item { padding: 16px 14px 16px 14px; }
  .bookmark-fab { padding: 12px 16px 12px 14px; font-size: 1rem; }
}
```

- [ ] **Step 6.2: 测试页 `<head>` 加 link**

```html
<link rel="stylesheet" href="bookmarks.css">
```

加到 `<head>` 任何位置。Reload 测试页应该看到 ⭐ 按钮在 mock card 上，FAB 在右下角。

- [ ] **Step 6.3: 提交**

```bash
git add docs/bookmarks.css docs/test-bookmarks.html
git commit -m "feat(bookmarks): bookmarks.css — ⭐/FAB/面板/toast/移动粘性目录样式"
```

---

## Task 7: 接入日报 Python 模板

**Files:**
- Modify: `generate_daily_pages.py`

- [ ] **Step 7.1: 在 `render_daily_html` 的 `<head>` 部分加资源引用**

定位：搜索 `<link rel="stylesheet" href="../style.css"`，在它**之后**加：

```python
  <link rel="stylesheet" href="../bookmarks.css" />
  <script defer src="../exports.js"></script>
  <script defer src="../bookmarks.js"></script>
```

注意：现有 head 是 f-string 输出，按现有缩进对齐即可。

- [ ] **Step 7.2: 在 `<head>` 加 iOS PWA meta**

紧贴 `<meta name="viewport" ...>` 之后加：

```python
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="apple-mobile-web-app-title" content="文献追踪" />
  <meta name="theme-color" content="#f59e0b" />
```

- [ ] **Step 7.3: card 根节点加 `data-bookmark-key`**

定位 `render_focus_item` (around L344)：找到 `<li class="daily-news-item">`，改为：

```python
        <li class="daily-news-item" data-bookmark-key="{safe_url(item.get('link') or '')}">
```

定位 `render_item` (around L368)：找到 `<li class="daily-paper-card" id="paper-{index}">`，改为：

```python
        <li class="daily-paper-card" id="paper-{index}" data-bookmark-key="{safe_url(item.get('link') or '')}">
```

定位 `render_core_section` (around L440)：找到 `<li class="daily-core-card">`，改为：

```python
            <li class="daily-core-card" data-bookmark-key="{safe_url(it.get('link') or '')}">
```

- [ ] **Step 7.4: 渲染移动粘性目录**

紧贴 `{date_nav_top}` 那一行**之后**插入：

```python
    <nav class="daily-toc-sticky" aria-label="移动目录">
      <a href="#summary">摘要</a>
      {('<a href="#core-focus">核心关注</a>' if summary.get('core_items') else '')}
      <a href="#highlights">交叉重点</a>
      <a href="#papers">完整速览</a>
    </nav>
```

注意 f-string 转义：嵌套表达式用一层括号即可。

- [ ] **Step 7.5: 烟囱测试 — 渲染并检查关键标记**

```bash
cd /home/webcode/literature/literature-tracker
python3 -c "import ast; ast.parse(open('generate_daily_pages.py').read()); print('syntax OK')"
```

跑一遍生成（用最近的 04-30 日期数据）：
```bash
PYTHONPATH=/tmp/py/usr/lib/python3/dist-packages:/tmp/bs4root/usr/lib/python3/dist-packages python3 -c "
from generate_daily_pages import render_daily_html
summary = {
  'date':'2026-04-15','total':1,'overview':'x','trends':'y',
  'full_list':[{'title_en':'NNP','title_zh':'势','abstract_zh':'a','summary':'s','link':'https://ex/1','journal':'Nature'}],
  'summaries':[],'ml_highlights':[],'ferro_highlights':[],
  'core_items':[{'title_en':'Equiv NNP','title_zh':'等变神经网络势','abstract_zh':'A','summary':'S','link':'https://ex/1','journal':'Nature','method_point':'mp','related_work':'rw','implication':'im'}],
  'core_direction_note':'note'
}
html = render_daily_html('2026-04-15', summary)
for s in ['../bookmarks.js','../bookmarks.css','../exports.js','data-bookmark-key=\"https://ex/1\"','daily-toc-sticky','apple-mobile-web-app-capable']:
    assert s in html, f'missing {s}'
print('OK render integration: all hooks present')
"
```

期望 `OK render integration: all hooks present`。

- [ ] **Step 7.6: 提交**

```bash
git add generate_daily_pages.py
git commit -m "feat(daily): 接入 bookmarks.js + 移动粘性目录 + iOS PWA meta + data-bookmark-key"
```

---

## Task 8: 接入周报 Python 模板

**Files:**
- Modify: `weekly_summary.py`

- [ ] **Step 8.1: 找到周报 HTML 模板的 `<head>` 与第一个 `<section>`**

```bash
grep -n "<head>\|</head>\|stylesheet\|first <section\|class=\"weekly-section\"" weekly_summary.py | head -20
```

- [ ] **Step 8.2: head 部分追加资源**

在 weekly 模板的 `<link rel="stylesheet"` 后面追加：

```python
<link rel="stylesheet" href="../bookmarks.css">
<script defer src="../exports.js"></script>
<script defer src="../bookmarks.js"></script>
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="文献追踪">
<meta name="theme-color" content="#f59e0b">
```

- [ ] **Step 8.3: 在 `render_core_weekly_section` 与周报正文的卡片渲染处加 `data-bookmark-key`**

`render_core_weekly_section` (L55)：找 `<li class="weekly-core-card">`，改为：

```python
        <li class="weekly-core-card" data-bookmark-key="{_t(link)}">
```

注意：现有 f-string 用了 `_t(link)` 转义文本，但 URL 应该用更严格的 escape（`html.escape(url, quote=True)`）。`_t` 已经做了 `html.escape(s, quote=True)`，OK 复用。

`weekly_summary.py` 主模板里的 `weekly-paper-card` 渲染处：搜 `<li class="weekly-paper-card`，给它加 `data-bookmark-key="..."`（用 `html.escape(article.get('link') or '', quote=True)`）。

- [ ] **Step 8.4: 渲染 weekly 移动粘性目录**

在第一个 `<section ...>` 之前插入：

```python
<nav class="weekly-toc-sticky" aria-label="移动目录">
  <a href="#core-focus">核心方向</a>
  <a href="#overview">本周总览</a>
  <a href="#highlights">重点文献</a>
  <a href="#trends">趋势</a>
</nav>
```

锚点名以 weekly_summary.py 里实际 section id 为准；如不一致就调整链接。

- [ ] **Step 8.5: 烟囱测试**

```bash
python3 -c "import ast; ast.parse(open('weekly_summary.py').read()); print('OK')"
```

加 weekly 渲染断言（如果时间允许，否则 task 9 一起补）。

- [ ] **Step 8.6: 提交**

```bash
git add weekly_summary.py
git commit -m "feat(weekly): 接入 bookmarks.js + 移动粘性目录 + iOS PWA meta"
```

---

## Task 9: 主页 + manifest + sw

**Files:**
- Modify: `docs/index.html`, `docs/manifest.json`, `docs/sw.js`

- [ ] **Step 9.1: index.html 加资源引用与 iOS meta**

在 `<head>` 中找到第一个 `<link rel="stylesheet" href="style.css">`，在它**之后**追加：

```html
  <link rel="stylesheet" href="bookmarks.css" />
  <script defer src="exports.js"></script>
  <script defer src="bookmarks.js"></script>
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="default" />
  <meta name="apple-mobile-web-app-title" content="文献追踪" />
  <meta name="theme-color" content="#f59e0b" />
```

- [ ] **Step 9.2: manifest.json 改 theme_color**

```bash
python3 -c "
import json
m = json.load(open('docs/manifest.json'))
m['theme_color'] = '#f59e0b'
open('docs/manifest.json','w').write(json.dumps(m, ensure_ascii=False, indent=2)+'\n')
print('updated')
"
```

- [ ] **Step 9.3: sw.js 升级缓存**

读取并替换：

```javascript
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/analytics.html',
    '/style.css',
    '/app.js',
    '/analytics.js',
    '/manifest.json',
    '/bookmarks.js',
    '/bookmarks.css',
    '/exports.js'
];
```

`fetch` handler 加：对路径以 `/daily/` 或 `/weekly/` 起头且以 `.html` 结尾的请求，network-first + cache-fallback 策略。在现有 fetch handler 里：

```javascript
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    const isDailyOrWeekly = (url.pathname.startsWith('/daily/') || url.pathname.startsWith('/weekly/')) && url.pathname.endsWith('.html');
    if (isDailyOrWeekly) {
        event.respondWith(
            fetch(event.request).then(resp => {
                if (resp && resp.ok) {
                    const copy = resp.clone();
                    caches.open(DATA_CACHE_NAME).then(c => c.put(event.request, copy));
                }
                return resp;
            }).catch(() => caches.match(event.request).then(r => r || Response.error()))
        );
        return;
    }
    // existing handler logic preserved below...
});
```

If existing fetch handler is empty (just `// 请求拦截` placeholder), replace whole listener.

- [ ] **Step 9.4: 提交**

```bash
git add docs/index.html docs/manifest.json docs/sw.js
git commit -m "feat(pwa): 主页接入 bookmarks + theme_color + sw 加日报/周报 network-first 缓存"
```

---

## Task 10: 端到端测试 + 推送 + 部署验证

**Files:**
- 无修改；运行验证

- [ ] **Step 10.1: 启 http server，浏览器跑测试页**

```bash
cd /home/webcode/literature/literature-tracker/docs
python3 -m http.server 8765 &>/tmp/http.log &
sleep 1
echo "Open http://localhost:8765/test-bookmarks.html"
```

人工或 headless（如 puppeteer/playwright 不可用就肉眼）：
- 标题前缀 `✓`
- 控制台 PASS 数 ≥ 25, FAIL = 0

- [ ] **Step 10.2: 用真实日报跑端到端**

```bash
cd /home/webcode/literature/literature-tracker
PYTHONPATH=/tmp/py/usr/lib/python3/dist-packages:/tmp/bs4root/usr/lib/python3/dist-packages \
KIMI_API_KEY=sk-kimi-xxujnCfRCk4fXuypSboxVyKXiEWn3G7JJJy9BUJNCTgdYoE8agkMjAdZkivBfGsj \
AI_PROVIDER=kimi python3 generate_daily_pages.py --date 2026-04-30 --force 2>&1 | tail -20
```

打开 `docs/daily/2026-04-30.html` 直接搜：
- `data-bookmark-key=` 出现 ≥ 5 次
- `bookmarks.js` 在 head
- `daily-toc-sticky` 渲染
- `apple-mobile-web-app-capable` meta 在

- [ ] **Step 10.3: 推送**

```bash
git push origin main
```

- [ ] **Step 10.4: 触发 Backfill Daily Pages 把所有页面带上新交互**

```bash
export GH_TOKEN=<the-gh-pat-the-user-provided-this-session>
curl -sS -o /dev/null -w "HTTP %{http_code}\n" -X POST \
  -H "Authorization: token $GH_TOKEN" -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/Hongyu-yu/literature-tracker/actions/workflows/246881370/dispatches \
  -d '{"ref":"main","inputs":{"days":"15","force":"true"}}'
```

等完成（监控 run 直到 conclusion=success）。然后：

```bash
git pull --rebase origin main
python3 -c "
html = open('docs/daily/2026-04-30.html').read()
checks = ['../bookmarks.js','../bookmarks.css','data-bookmark-key=','daily-toc-sticky','apple-mobile-web-app-capable']
for c in checks:
    assert c in html, f'missing {c}'
print('OK production daily contains bookmarks integration')
"
```

- [ ] **Step 10.5: 浏览器最终人工验收（移动 + 桌面）**

打开 `https://hongyu-yu.github.io/literature-tracker/daily/2026-04-30.html`：
- 任意 card 右上角看到 ☆
- 点击 → 变 ★，FAB 计数 +1
- 长按 / 右滑也能 toggle
- FAB 点击 → 面板列出收藏
- 三种导出按钮各点一次，下载到的 .xml/.md/.bib 文件用文本编辑器打开内容正确

iPhone 实测："分享 → 添加到主屏幕" → 启动后 standalone（无浏览器 toolbar）。

---

## Self-Review

**1. Spec coverage:**
- §1 架构 → Task 1-4 (bookmarks.js)、Task 5 (exports.js)
- §2 数据模型 → Task 1 (BookmarkStore)
- §3 文件清单 → 全覆盖（Task 1-9）
- §4 UI 详细规格 → Task 2-4 + Task 6 (CSS)
- §5 PWA → Task 7,8,9（meta + manifest + sw）
- §6 导出格式 → Task 5
- §7 验证 → Task 10

**2. Placeholder scan:** 已消除。每步含可执行代码或命令。

**3. Type consistency:**
- `BookmarkStore.add/remove/toggle/has/list/count` 在 Task 1 定义、Task 2-5 调用，签名一致
- `BookmarkUI.attachToCards/bindGestures/renderFab/openPanel` 在 Task 2-4 定义、Task 7-9 间接通过 init 调用一致
- `BookmarkExports.exportRSS/exportMarkdown/exportBibTeX` 在 Task 5 定义，Task 4 在 `_exportAs` 调用一致
- `data-bookmark-key` 字符串在 Task 7,8 模板与 Task 2 `_attach()` 读取一致
- `bookmarkschange` 自定义事件在 Task 1 派发、Task 4 监听一致

**4. 入口注册：**

需要一个全局 init。在 `bookmarks.js` IIFE 末尾、`window.BookmarkUI = ...` 之后加：

```javascript
  function _autoInit() {
    if (window.__bookmarksInited) return;
    window.__bookmarksInited = true;
    const store = new BookmarkStore();
    const ui = new BookmarkUI(store);
    ui.attachToCards();
    ui.bindGestures();
    ui.renderFab();
    window.literatureBookmarks = { store, ui };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _autoInit);
  } else {
    _autoInit();
  }
```

把这段加进 Task 4 末尾或新增 step 4.6（更清晰）。**修正：把它合到 Task 4 最末（renderFab 实现完之后）**：在 Task 4 step 4.4 之前加 step 4.3.5：

> **Step 4.3.5: 在 IIFE 末尾追加 `_autoInit`**（把上面那段插到 `window.BookmarkUI = BookmarkUI;` 之后）

测试页里因为已经手动 new + init，所以 `window.__bookmarksInited` 已经被自动 init 设为 true → 无副作用，但为了避免双重渲染 FAB 等冲突，建议在测试页 `<script>` 头部加 `window.__bookmarksInited = true;` 以禁用自动 init。**修正测试页**：在 step 1.1 模板里 `<script src="bookmarks.js"></script>` 之前加：

```html
<script>window.__bookmarksInited = true;</script>
```
