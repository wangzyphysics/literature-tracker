/**
 * FeedUI — TikTok-style full-screen literature feed.
 * Renders one full-screen card per paper, with concept-poster overlay for APS
 * items, a sticky category filter bar, and reuses BookmarkUI / LikeUI for the
 * ⭐ / ❤️ buttons. Dependency-free vanilla JS.
 */
(function () {
  'use strict';

  const POSTER_ROWS = ['研究问题', '创新方法', '工作流程', '关键结果', '应用价值'];
  const READ_KEY = 'literature_feed_read';
  function getRead() {
    try { return JSON.parse(localStorage.getItem(READ_KEY) || '[]'); } catch (e) { return []; }
  }
  function markRead(id) {
    if (!id) return;
    const r = getRead();
    if (r.indexOf(id) === -1) { r.push(id); try { localStorage.setItem(READ_KEY, JSON.stringify(r)); } catch (e) {} }
  }
  function updateProgress(total) {
    const p = document.getElementById('feed-progress');
    if (!p) return;
    p.textContent = '已读 ' + getRead().length + ' / 共 ' + total + ' 篇';
  }
  const ALL_CAT = '全部';
  const CAT_ORDER = ['AI×物理', 'AI×化学·材料', '磁性·自旋电子学', '铁电·极化', '拓扑·电子结构',
    '超导', '量子信息·计算', '软物质·流体·统计', '其他凝聚态', '其他'];

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = (s == null ? '' : String(s));
    return d.innerHTML;
  }

  function el(tag, cls, html) {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  }

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
    const eb = buildElementsBlock(item);
    if (eb) card.appendChild(eb);

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

  function renderFeed(items, container) {
    if (!container) return;
    container.innerHTML = '';
    let lastDate = null;
    (items || []).forEach(function (item) {
      if (item.date && item.date !== lastDate) {
        lastDate = item.date;
        const dayCount = (items || []).filter(function (x) { return x.date === item.date; }).length;
        container.appendChild(el('div', 'feed-day-header',
          '📅 ' + esc(item.date) + '（共 ' + dayCount + ' 篇）'));
      }
      container.appendChild(buildCard(item));
    });
    updateProgress((items || []).length);
    if (window.literatureBookmarks && window.literatureBookmarks.ui) {
      const bu = window.literatureBookmarks.ui;
      bu.attachToCards(container);
      if (bu.renderFab) { try { bu.renderFab(); } catch (e) {} }
      if (bu.bindGestures) { try { bu.bindGestures(container); } catch (e) {} }
    } else if (window.BookmarkUI && window.BookmarkStore) {
      new window.BookmarkUI(new window.BookmarkStore()).attachToCards(container);
    }
    if (window.LikeUI && window.likeStore) {
      new window.LikeUI(window.likeStore).attachToCards(container);
    }
  }

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

  function buildCatBar(items, barEl) {
    const bar = barEl || document.getElementById('cat-bar');
    if (!bar) return null;
    bar.innerHTML = '';
    const cats = [ALL_CAT].concat(distinctCategories(items));
    cats.forEach(function (cat, i) {
      const chip = el('button', 'chip');
      chip.type = 'button';
      chip.textContent = cat;
      chip.dataset.cat = cat;
      if (cat === 'AI×物理' || cat === 'AI×化学·材料') chip.classList.add('chip-ai');
      if (i === 0) chip.classList.add('active');
      chip.addEventListener('click', function () {
        bar.querySelectorAll('.chip').forEach(function (c) {
          c.classList.toggle('active', c === chip);
        });
        filterByCategory(cat);
      });
      bar.appendChild(chip);
    });
    return bar;
  }

  function filterByCategory(cat) {
    const showAll = (cat == null || cat === ALL_CAT);
    document.querySelectorAll('.feed-card').forEach(function (card) {
      const match = showAll || card.dataset.category === cat;
      card.classList.toggle('hidden', !match);
    });
  }

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

  function loadFeed() {
    const main = document.getElementById('feed');
    const bar = document.getElementById('cat-bar');
    if (!main) return;
    fetch('data/feed.json')
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        const items = (data && data.items) || [];
        if (!items.length) {
          main.innerHTML = '<div class="feed-empty">暂无文献，请稍后再来 ✨</div>';
          return;
        }
        renderFeed(items, main);
        buildCatBar(items, bar);
        let ticking = false;
        main.addEventListener('scroll', function () {
          if (ticking) return; ticking = true;
          requestAnimationFrame(function () {
            const cards = main.querySelectorAll('.feed-card');
            for (const c of cards) {
              const r = c.getBoundingClientRect();
              if (r.top >= 0 && r.top < window.innerHeight * 0.5) {
                markRead(c.dataset.doc || c.dataset.bookmarkKey); break;
              }
            }
            updateProgress((data.items || []).length);
            ticking = false;
          });
        });
        const sp = new URLSearchParams(location.search);
        applyDeepLink({ doc: sp.get('doc'), date: sp.get('date') });
      })
      .catch(function (err) {
        console.warn('[feed] load failed:', err);
        main.innerHTML = '<div class="feed-empty">无法加载文献流，请稍后重试。</div>';
      });
  }

  window.FeedUI = {
    renderFeed: renderFeed,
    buildCatBar: buildCatBar,
    filterByCategory: filterByCategory,
    applyDeepLink: applyDeepLink,
    loadFeed: loadFeed,
    markRead: markRead,
    getRead: getRead,
  };

  function _autoInit() {
    if (window.__feedInited) return;
    if (!document.getElementById('feed')) return;
    window.__feedInited = true;
    loadFeed();
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', _autoInit);
    } else {
      _autoInit();
    }
  }
})();
