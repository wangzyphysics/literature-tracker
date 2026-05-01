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
