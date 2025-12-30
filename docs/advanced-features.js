/**
 * 高级功能模块 - 布局管理、字体调节、快捷键自定义等
 */

// ========================================
// 布局管理器（简化版 - 只保留列表布局）
// ========================================

class LayoutManager {
    constructor() {
        this.currentLayout = 'list';
        this.layouts = {
            list: { columns: 1, spacing: 'normal', details: 'full' }
        };
        this.storageKey = 'literature_layout';
    }

    init() {
        // 强制使用列表布局，不创建切换UI
        this.currentLayout = 'list';
        this.applyLayout();
    }

    createUI() {
        // 不再创建布局切换UI
    }

    setLayout(layoutName) {
        // 只支持列表布局
        this.currentLayout = 'list';
        this.applyLayout();
    }

    applyLayout() {
        const articleList = document.getElementById('articleList');
        if (!articleList) return;

        // 移除所有布局类，只添加列表布局
        articleList.classList.remove('layout-list', 'layout-grid', 'layout-compact');
        articleList.classList.add('layout-list');
    }

    updateGridColumns() {
        // 不再需要
    }

    updateUI() {
        // 不再需要
    }

    saveLayout() {
        // 不再需要保存
    }

    restoreLayout() {
        // 不再需要恢复
    }

    getLayout() {
        return this.layouts['list'];
    }
}

// ========================================
// 字体管理器
// ========================================

class FontManager {
    constructor() {
        this.sizes = ['xs', 'sm', 'md', 'lg', 'xl'];
        this.currentSize = 'md';
        this.baseSizes = {
            xs: 12,
            sm: 14,
            md: 16,
            lg: 18,
            xl: 20
        };
        this.storageKey = 'literature_font_size';
    }

    init() {
        this.restoreFontSize();
        this.createUI();
        this.applyFontSize();
        this.setupKeyboardShortcuts();
    }

    createUI() {
        const controls = document.querySelector('.controls');
        if (!controls) return;

        const fontSection = document.createElement('div');
        fontSection.className = 'font-controls';
        fontSection.innerHTML = `
            <div class="font-size-controls">
                <span class="font-label">字体:</span>
                <button class="font-btn" id="fontDecrease" title="减小字体 (Ctrl/Cmd + -)">A-</button>
                <span class="font-size-indicator" id="fontSizeIndicator">${this.currentSize.toUpperCase()}</span>
                <button class="font-btn" id="fontIncrease" title="增大字体 (Ctrl/Cmd + +)">A+</button>
                <button class="font-btn" id="fontReset" title="重置字体">重置</button>
            </div>
        `;

        // 插入到 layout-controls 之后
        const layoutControls = controls.querySelector('.layout-controls');
        if (layoutControls) {
            layoutControls.after(fontSection);
        } else {
            const filters = controls.querySelector('.filters');
            if (filters) {
                controls.insertBefore(fontSection, filters);
            } else {
                controls.appendChild(fontSection);
            }
        }

        // 绑定事件
        document.getElementById('fontDecrease')?.addEventListener('click', () => this.decreaseFontSize());
        document.getElementById('fontIncrease')?.addEventListener('click', () => this.increaseFontSize());
        document.getElementById('fontReset')?.addEventListener('click', () => this.resetFontSize());
    }

    setFontSize(size) {
        if (!this.sizes.includes(size)) return;

        this.currentSize = size;
        this.saveFontSize();
        this.applyFontSize();
        this.updateUI();
    }

    increaseFontSize() {
        const currentIndex = this.sizes.indexOf(this.currentSize);
        if (currentIndex < this.sizes.length - 1) {
            this.setFontSize(this.sizes[currentIndex + 1]);
        }
    }

    decreaseFontSize() {
        const currentIndex = this.sizes.indexOf(this.currentSize);
        if (currentIndex > 0) {
            this.setFontSize(this.sizes[currentIndex - 1]);
        }
    }

    resetFontSize() {
        this.setFontSize('md');
    }

    applyFontSize() {
        const baseSize = this.baseSizes[this.currentSize];
        const lineHeight = 1.6 + (this.sizes.indexOf(this.currentSize) - 2) * 0.05;

        document.documentElement.style.setProperty('--font-size-base', `${baseSize}px`);
        document.documentElement.style.setProperty('--line-height-base', lineHeight);

        // 应用到body
        document.body.style.fontSize = `${baseSize}px`;
        document.body.style.lineHeight = lineHeight;
    }

    updateUI() {
        const indicator = document.getElementById('fontSizeIndicator');
        if (indicator) {
            indicator.textContent = this.currentSize.toUpperCase();
        }
    }

    saveFontSize() {
        try {
            localStorage.setItem(this.storageKey, this.currentSize);
        } catch (e) {
            console.warn('无法保存字体设置:', e);
        }
    }

    restoreFontSize() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved && this.sizes.includes(saved)) {
                this.currentSize = saved;
            }
        } catch (e) {
            console.warn('无法加载字体设置:', e);
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Plus
            if ((e.ctrlKey || e.metaKey) && (e.key === '=' || e.key === '+')) {
                e.preventDefault();
                this.increaseFontSize();
            }
            // Ctrl/Cmd + Minus
            if ((e.ctrlKey || e.metaKey) && e.key === '-') {
                e.preventDefault();
                this.decreaseFontSize();
            }
            // Ctrl/Cmd + 0
            if ((e.ctrlKey || e.metaKey) && e.key === '0') {
                e.preventDefault();
                this.resetFontSize();
            }
        });
    }
}

// ========================================
// 快捷键管理器
// ========================================

class ShortcutManager {
    constructor() {
        this.shortcuts = new Map();
        this.defaultShortcuts = {
            'nextArticle': { keys: 'j', description: '下一篇文章', category: '导航' },
            'prevArticle': { keys: 'k', description: '上一篇文章', category: '导航' },
            'toggleExpand': { keys: 'Enter', description: '展开/折叠', category: '操作' },
            'openLink': { keys: 'o', description: '打开原文', category: '操作' },
            'toggleFavorite': { keys: 's', description: '收藏/取消收藏', category: '操作' },
            'toggleRead': { keys: 'r', description: '标记已读/未读', category: '操作' },
            'toggleReadLater': { keys: 'l', description: '稍后阅读', category: '操作' },
            'increaseFontSize': { keys: 'Ctrl+=', description: '增大字体', category: '界面' },
            'decreaseFontSize': { keys: 'Ctrl+-', description: '减小字体', category: '界面' },
            'search': { keys: '/', description: '搜索模式切换', category: '搜索' },
            'toggleTheme': { keys: 't', description: '切换主题', category: '界面' }
        };
        this.storageKey = 'literature_shortcuts';
        this.isEditing = false;
        this.editingAction = null;
    }

    init() {
        this.restoreShortcuts();
        this.createUI();
    }

    createUI() {
        // 创建快捷键配置按钮
        const controls = document.querySelector('.controls');
        if (!controls) return;

        const shortcutBtn = document.createElement('button');
        shortcutBtn.className = 'shortcut-config-btn';
        shortcutBtn.innerHTML = '⌨️ 快捷键';
        shortcutBtn.title = '配置快捷键';
        shortcutBtn.onclick = () => this.showConfigPanel();

        // 添加到控制面板
        const fontControls = controls.querySelector('.font-controls');
        if (fontControls) {
            fontControls.after(shortcutBtn);
        } else {
            controls.appendChild(shortcutBtn);
        }
    }

    showConfigPanel() {
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'shortcut-modal';
        modal.innerHTML = `
            <div class="shortcut-modal-content">
                <div class="shortcut-modal-header">
                    <h3>⌨️ 快捷键配置</h3>
                    <button class="shortcut-modal-close" onclick="this.closest('.shortcut-modal').remove()">✕</button>
                </div>
                <div class="shortcut-modal-body">
                    <div class="shortcut-search">
                        <input type="text" placeholder="搜索快捷键..." id="shortcutSearch">
                    </div>
                    <div class="shortcut-list" id="shortcutList"></div>
                </div>
                <div class="shortcut-modal-footer">
                    <button class="shortcut-reset-btn" onclick="shortcutManager.resetShortcuts()">恢复默认</button>
                    <button class="shortcut-close-btn" onclick="this.closest('.shortcut-modal').remove()">关闭</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        this.renderShortcutList();

        // 点击外部关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // 搜索功能
        document.getElementById('shortcutSearch')?.addEventListener('input', (e) => {
            this.filterShortcuts(e.target.value);
        });
    }

    renderShortcutList() {
        const listEl = document.getElementById('shortcutList');
        if (!listEl) return;

        const categories = {};
        for (const [action, config] of this.shortcuts) {
            const category = config.category || '其他';
            if (!categories[category]) {
                categories[category] = [];
            }
            categories[category].push({ action, ...config });
        }

        let html = '';
        for (const [category, items] of Object.entries(categories)) {
            html += `<div class="shortcut-category">
                <h4>${category}</h4>
                <div class="shortcut-items">`;

            items.forEach(item => {
                const isEditing = this.isEditing && this.editingAction === item.action;
                html += `
                    <div class="shortcut-item ${isEditing ? 'editing' : ''}" data-action="${item.action}">
                        <span class="shortcut-description">${item.description}</span>
                        <div class="shortcut-keys">
                            ${isEditing ?
                        `<input type="text" class="shortcut-input" value="${item.keys}" placeholder="按下新快捷键...">` :
                        `<kbd>${item.keys}</kbd>`
                    }
                            <button class="shortcut-edit-btn" onclick="shortcutManager.editShortcut('${item.action}')">
                                ${isEditing ? '保存' : '编辑'}
                            </button>
                        </div>
                    </div>
                `;
            });

            html += `</div></div>`;
        }

        listEl.innerHTML = html;
    }

    editShortcut(action) {
        if (this.isEditing && this.editingAction === action) {
            // 保存
            const input = document.querySelector(`.shortcut-item[data-action="${action}"] .shortcut-input`);
            if (input) {
                const newKeys = input.value.trim();
                if (newKeys) {
                    const conflicts = this.getConflicts(newKeys, action);
                    if (conflicts.length > 0) {
                        alert(`快捷键冲突: ${conflicts.join(', ')}`);
                        return;
                    }
                    this.updateShortcut(action, newKeys);
                }
            }
            this.isEditing = false;
            this.editingAction = null;
        } else {
            // 编辑
            this.isEditing = true;
            this.editingAction = action;
        }
        this.renderShortcutList();

        // 聚焦输入框
        if (this.isEditing) {
            const input = document.querySelector(`.shortcut-item[data-action="${action}"] .shortcut-input`);
            if (input) {
                input.focus();
                input.addEventListener('keydown', (e) => {
                    e.preventDefault();
                    const keys = [];
                    if (e.ctrlKey) keys.push('Ctrl');
                    if (e.altKey) keys.push('Alt');
                    if (e.shiftKey) keys.push('Shift');
                    if (e.metaKey) keys.push('Meta');
                    if (e.key && !['Control', 'Alt', 'Shift', 'Meta'].includes(e.key)) {
                        keys.push(e.key);
                    }
                    input.value = keys.join('+');
                });
            }
        }
    }

    updateShortcut(action, newKeys) {
        const config = this.shortcuts.get(action);
        if (config) {
            config.keys = newKeys;
            this.saveShortcuts();
        }
    }

    getConflicts(keys, excludeAction = null) {
        const conflicts = [];
        for (const [action, config] of this.shortcuts) {
            if (action !== excludeAction && config.keys === keys) {
                conflicts.push(config.description);
            }
        }
        return conflicts;
    }

    filterShortcuts(query) {
        const items = document.querySelectorAll('.shortcut-item');
        const lowerQuery = query.toLowerCase();

        items.forEach(item => {
            const description = item.querySelector('.shortcut-description').textContent.toLowerCase();
            const keys = item.querySelector('kbd')?.textContent.toLowerCase() || '';
            const matches = description.includes(lowerQuery) || keys.includes(lowerQuery);
            item.style.display = matches ? '' : 'none';
        });
    }

    resetShortcuts() {
        if (confirm('确定要恢复默认快捷键设置吗？')) {
            this.shortcuts = new Map(Object.entries(this.defaultShortcuts));
            this.saveShortcuts();
            this.renderShortcutList();
        }
    }

    saveShortcuts() {
        try {
            const data = {};
            for (const [action, config] of this.shortcuts) {
                data[action] = config;
            }
            localStorage.setItem(this.storageKey, JSON.stringify(data));
        } catch (e) {
            console.warn('无法保存快捷键设置:', e);
        }
    }

    restoreShortcuts() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const data = JSON.parse(saved);
                this.shortcuts = new Map(Object.entries(data));
            } else {
                this.shortcuts = new Map(Object.entries(this.defaultShortcuts));
            }
        } catch (e) {
            console.warn('无法加载快捷键设置:', e);
            this.shortcuts = new Map(Object.entries(this.defaultShortcuts));
        }
    }

    getShortcut(action) {
        return this.shortcuts.get(action);
    }
}

// ========================================
// 预览系统增强
// ========================================

class PreviewSystem {
    constructor() {
        this.tooltip = null;
        this.hoverTimer = null;
        this.hideTimer = null;
        this.hoverDelay = 500;
        this.hideDelay = 200;
        this.currentArticleId = null;
    }

    init() {
        this.createTooltip();
    }

    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'preview-tooltip-enhanced';
        document.body.appendChild(this.tooltip);
    }

    showPreview(event, articleId, article) {
        // 移动端不显示
        if (window.innerWidth < 768) return;

        // 如果卡片已展开，不显示预览
        if (expandedCards && expandedCards.has(articleId)) return;

        this.currentArticleId = articleId;

        clearTimeout(this.hoverTimer);
        clearTimeout(this.hideTimer);

        this.hoverTimer = setTimeout(() => {
            if (!article) return;

            const content = `
                <div class="preview-header">
                    <strong>${article.title_zh || article.title}</strong>
                </div>
                <div class="preview-meta">
                    <span>📅 ${article.pub_date || '未知日期'}</span>
                    <span>📖 ${article.journal || '未知期刊'}</span>
                </div>
                <div class="preview-authors">
                    👤 ${(article.authors || []).slice(0, 3).join(', ')}${article.authors && article.authors.length > 3 ? ' et al.' : ''}
                </div>
                <div class="preview-abstract">
                    ${article.abstract_zh || article.abstract || '暂无摘要'}
                </div>
                <div class="preview-footer">
                    <small>点击卡片查看完整内容</small>
                </div>
            `;

            this.tooltip.innerHTML = content;
            this.tooltip.classList.add('visible');

            this.positionTooltip(event.target);
        }, this.hoverDelay);
    }

    hidePreview() {
        clearTimeout(this.hoverTimer);
        clearTimeout(this.hideTimer);

        this.hideTimer = setTimeout(() => {
            if (this.tooltip) {
                this.tooltip.classList.remove('visible');
            }
            this.currentArticleId = null;
        }, this.hideDelay);
    }

    positionTooltip(target) {
        if (!this.tooltip || !target) return;

        const rect = target.getBoundingClientRect();
        const tooltipRect = this.tooltip.getBoundingClientRect();

        let left = rect.left;
        let top = rect.bottom + 10;

        // 避免超出右边界
        if (left + tooltipRect.width > window.innerWidth - 20) {
            left = window.innerWidth - tooltipRect.width - 20;
        }

        // 避免超出左边界
        if (left < 20) {
            left = 20;
        }

        // 避免超出底部
        if (top + tooltipRect.height > window.innerHeight - 20) {
            top = rect.top - tooltipRect.height - 10;
        }

        // 避免超出顶部
        if (top < 20) {
            top = 20;
        }

        this.tooltip.style.left = `${left}px`;
        this.tooltip.style.top = `${top}px`;
    }
}

// ========================================
// 全局实例
// ========================================

let layoutManager = null;
let fontManager = null;
let shortcutManager = null;
let previewSystem = null;

// 初始化所有高级功能
function initAdvancedFeatures() {
    layoutManager = new LayoutManager();
    layoutManager.init();

    fontManager = new FontManager();
    fontManager.init();

    shortcutManager = new ShortcutManager();
    shortcutManager.init();

    previewSystem = new PreviewSystem();
    previewSystem.init();

    // 监听窗口大小变化，更新网格布局
    let resizeTimer;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (layoutManager && layoutManager.currentLayout === 'grid') {
                layoutManager.updateGridColumns();
            }
        }, 250);
    });
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.layoutManager = layoutManager;
    window.fontManager = fontManager;
    window.shortcutManager = shortcutManager;
    window.previewSystem = previewSystem;
    window.initAdvancedFeatures = initAdvancedFeatures;
}


// ========================================
// 虚拟滚动管理器
// ========================================

class VirtualScrollManager {
    constructor() {
        this.enabled = false;
        this.container = null;
        this.items = [];
        this.renderItem = null;
        this.visibleRange = { start: 0, end: 0 };
        this.itemHeight = 200; // 平均高度
        this.buffer = 10;
        this.threshold = 50; // 启用虚拟滚动的最小项目数
        this.scrollTimeout = null;
        this.itemHeights = new Map();
    }

    init(container, items, renderItem) {
        this.container = container;
        this.items = items;
        this.renderItem = renderItem;

        // 只有超过阈值才启用虚拟滚动
        if (items.length > this.threshold) {
            this.enabled = true;
            this.setupScrollListener();
            this.calculateVisibleRange();
            this.render();
        } else {
            this.enabled = false;
        }
    }

    setupScrollListener() {
        window.addEventListener('scroll', () => {
            clearTimeout(this.scrollTimeout);
            this.scrollTimeout = setTimeout(() => {
                this.onScroll();
            }, 16); // ~60fps
        });
    }

    onScroll() {
        if (!this.enabled) return;

        const oldRange = { ...this.visibleRange };
        this.calculateVisibleRange();

        // 只有范围变化时才重新渲染
        if (oldRange.start !== this.visibleRange.start ||
            oldRange.end !== this.visibleRange.end) {
            this.render();
        }
    }

    calculateVisibleRange() {
        if (!this.container) return;

        const scrollTop = window.pageYOffset;
        const viewportHeight = window.innerHeight;

        // 计算可见范围
        let start = Math.floor(scrollTop / this.itemHeight) - this.buffer;
        let end = Math.ceil((scrollTop + viewportHeight) / this.itemHeight) + this.buffer;

        start = Math.max(0, start);
        end = Math.min(this.items.length, end);

        this.visibleRange = { start, end };
    }

    render() {
        if (!this.enabled || !this.container || !this.renderItem) return;

        const { start, end } = this.visibleRange;
        const visibleItems = this.items.slice(start, end);

        // 创建占位符
        const topHeight = start * this.itemHeight;
        const bottomHeight = (this.items.length - end) * this.itemHeight;

        this.container.innerHTML = `
            <div style="height: ${topHeight}px;"></div>
            ${visibleItems.map((item, index) => this.renderItem(item, start + index)).join('')}
            <div style="height: ${bottomHeight}px;"></div>
        `;

        // 更新实际高度
        this.updateItemHeights(start);
    }

    updateItemHeights(startIndex) {
        const cards = this.container.querySelectorAll('.article-card');
        cards.forEach((card, index) => {
            const actualHeight = card.offsetHeight;
            const itemIndex = startIndex + index;
            this.itemHeights.set(itemIndex, actualHeight);
        });

        // 更新平均高度
        if (this.itemHeights.size > 0) {
            const sum = Array.from(this.itemHeights.values()).reduce((a, b) => a + b, 0);
            this.itemHeight = sum / this.itemHeights.size;
        }
    }

    scrollToIndex(index) {
        if (index < 0 || index >= this.items.length) return;

        const scrollTop = index * this.itemHeight;
        window.scrollTo({ top: scrollTop, behavior: 'smooth' });
    }

    disable() {
        this.enabled = false;
    }

    enable() {
        if (this.items.length > this.threshold) {
            this.enabled = true;
            this.calculateVisibleRange();
            this.render();
        }
    }
}

// ========================================
// 懒加载管理器
// ========================================

class LazyLoadManager {
    constructor() {
        this.observer = null;
        this.loadedImages = new Set();
        this.failedImages = new Set();
        this.rootMargin = '200px';
    }

    init() {
        if ('IntersectionObserver' in window) {
            this.observer = new IntersectionObserver(
                (entries) => this.handleIntersection(entries),
                {
                    rootMargin: this.rootMargin,
                    threshold: 0.01
                }
            );
        }
    }

    observe(imageElement) {
        if (!this.observer || !imageElement) return;

        // 添加占位符类
        imageElement.classList.add('lazy-loading');
        this.observer.observe(imageElement);
    }

    handleIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                this.loadImage(img);
                this.observer.unobserve(img);
            }
        });
    }

    loadImage(imageElement) {
        const src = imageElement.dataset.src;
        if (!src || this.loadedImages.has(src)) return;

        const img = new Image();

        img.onload = () => {
            imageElement.src = src;
            imageElement.classList.remove('lazy-loading');
            imageElement.classList.add('lazy-loaded');
            this.loadedImages.add(src);
        };

        img.onerror = () => {
            imageElement.classList.remove('lazy-loading');
            imageElement.classList.add('lazy-error');
            this.failedImages.add(src);

            // 显示占位符
            imageElement.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23ddd" width="100" height="100"/%3E%3Ctext x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="%23999"%3E✕%3C/text%3E%3C/svg%3E';
        };

        img.src = src;
    }

    unobserve(imageElement) {
        if (this.observer && imageElement) {
            this.observer.unobserve(imageElement);
        }
    }

    retryFailed() {
        this.failedImages.forEach(src => {
            const images = document.querySelectorAll(`img[data-src="${src}"]`);
            images.forEach(img => {
                this.failedImages.delete(src);
                this.loadImage(img);
            });
        });
    }

    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
    }
}

// ========================================
// 增量加载器
// ========================================

class IncrementalLoader {
    constructor(batchSize = 50) {
        this.batchSize = batchSize;
        this.currentBatch = 0;
        this.loading = false;
        this.allLoaded = false;
        this.dataSource = [];
        this.loadedItems = [];
        this.autoLoadEnabled = true;
        this.scrollThreshold = 300; // 距离底部多少像素时触发加载
    }

    init(dataSource) {
        this.dataSource = dataSource;
        this.currentBatch = 0;
        this.loadedItems = [];
        this.allLoaded = false;

        // 加载第一批
        this.loadNextBatch();

        // 设置自动加载
        if (this.autoLoadEnabled) {
            this.setupAutoLoad();
        }
    }

    loadNextBatch() {
        if (this.loading || this.allLoaded) return;

        this.loading = true;
        this.showLoadingIndicator();

        // 模拟异步加载
        setTimeout(() => {
            const start = this.currentBatch * this.batchSize;
            const end = start + this.batchSize;
            const batch = this.dataSource.slice(start, end);

            if (batch.length === 0) {
                this.allLoaded = true;
                this.showEndMessage();
            } else {
                this.loadedItems.push(...batch);
                this.currentBatch++;

                if (end >= this.dataSource.length) {
                    this.allLoaded = true;
                }
            }

            this.loading = false;
            this.hideLoadingIndicator();

            // 触发回调
            if (this.onBatchLoaded) {
                this.onBatchLoaded(this.loadedItems);
            }
        }, 300);
    }

    setupAutoLoad() {
        window.addEventListener('scroll', () => {
            if (this.shouldLoadMore()) {
                this.loadNextBatch();
            }
        });
    }

    shouldLoadMore() {
        if (this.loading || this.allLoaded || !this.autoLoadEnabled) {
            return false;
        }

        const scrollTop = window.pageYOffset;
        const windowHeight = window.innerHeight;
        const documentHeight = document.documentElement.scrollHeight;

        return (documentHeight - scrollTop - windowHeight) < this.scrollThreshold;
    }

    showLoadingIndicator() {
        let indicator = document.getElementById('incrementalLoadingIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'incrementalLoadingIndicator';
            indicator.className = 'incremental-loading';
            indicator.innerHTML = '<div class="loading-spinner"></div><span>加载中...</span>';
            document.getElementById('articleList')?.after(indicator);
        }
        indicator.style.display = 'flex';
    }

    hideLoadingIndicator() {
        const indicator = document.getElementById('incrementalLoadingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    showEndMessage() {
        let message = document.getElementById('incrementalEndMessage');
        if (!message) {
            message = document.createElement('div');
            message.id = 'incrementalEndMessage';
            message.className = 'incremental-end';
            message.innerHTML = '<span>✓ 已加载全部文献</span>';
            document.getElementById('articleList')?.after(message);
        }
        message.style.display = 'block';
    }

    reset() {
        this.currentBatch = 0;
        this.loadedItems = [];
        this.allLoaded = false;
        this.loading = false;
        this.hideLoadingIndicator();

        const endMessage = document.getElementById('incrementalEndMessage');
        if (endMessage) {
            endMessage.style.display = 'none';
        }
    }

    hasMore() {
        return !this.allLoaded;
    }

    getLoadedItems() {
        return this.loadedItems;
    }
}

// ========================================
// 缓存管理器
// ========================================

class CacheManager {
    constructor(maxSize = 50) {
        this.cache = new Map();
        this.maxSize = maxSize;
        this.accessOrder = [];
        this.hits = 0;
        this.misses = 0;
    }

    set(key, value) {
        // 如果已存在，先删除
        if (this.cache.has(key)) {
            this.cache.delete(key);
            this.accessOrder = this.accessOrder.filter(k => k !== key);
        }

        // 如果缓存已满，执行LRU淘汰
        if (this.cache.size >= this.maxSize) {
            this.evict();
        }

        // 添加新项
        this.cache.set(key, {
            value: value,
            timestamp: Date.now(),
            accessCount: 0
        });
        this.accessOrder.push(key);
    }

    get(key) {
        if (this.cache.has(key)) {
            this.hits++;
            const entry = this.cache.get(key);
            entry.accessCount++;

            // 更新访问顺序
            this.accessOrder = this.accessOrder.filter(k => k !== key);
            this.accessOrder.push(key);

            return entry.value;
        }

        this.misses++;
        return null;
    }

    has(key) {
        return this.cache.has(key);
    }

    clear() {
        this.cache.clear();
        this.accessOrder = [];
        this.hits = 0;
        this.misses = 0;
    }

    evict() {
        if (this.accessOrder.length === 0) return;

        // 移除最少使用的项（LRU）
        const lruKey = this.accessOrder.shift();
        this.cache.delete(lruKey);
    }

    getStats() {
        const total = this.hits + this.misses;
        const hitRate = total > 0 ? (this.hits / total * 100).toFixed(2) : 0;

        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            hits: this.hits,
            misses: this.misses,
            hitRate: hitRate + '%',
            items: Array.from(this.cache.entries()).map(([key, entry]) => ({
                key,
                timestamp: new Date(entry.timestamp).toLocaleString(),
                accessCount: entry.accessCount
            }))
        };
    }

    invalidate(pattern) {
        // 支持模式匹配失效
        const keysToDelete = [];
        for (const key of this.cache.keys()) {
            if (key.includes(pattern)) {
                keysToDelete.push(key);
            }
        }

        keysToDelete.forEach(key => {
            this.cache.delete(key);
            this.accessOrder = this.accessOrder.filter(k => k !== key);
        });
    }
}

// ========================================
// 移动端适配器
// ========================================

class MobileAdapter {
    constructor() {
        this.isMobile = false;
        this.touchStartX = 0;
        this.touchStartY = 0;
        this.touchEndX = 0;
        this.touchEndY = 0;
        this.swipeThreshold = 50;
        this.currentSwipeElement = null;
    }

    init() {
        this.detectMobile();

        if (this.isMobile) {
            this.setupTouchHandlers();
            this.setupBottomNav();
            this.optimizeTouchTargets();
            this.setupPullToRefresh();
        }

        // 监听窗口大小变化
        window.addEventListener('resize', () => {
            this.detectMobile();
        });
    }

    detectMobile() {
        const wasMobile = this.isMobile;
        this.isMobile = window.innerWidth < 768;

        if (wasMobile !== this.isMobile) {
            document.body.classList.toggle('mobile-layout', this.isMobile);
        }

        return this.isMobile;
    }

    setupTouchHandlers() {
        let touchStartTime = 0;

        document.addEventListener('touchstart', (e) => {
            this.touchStartX = e.changedTouches[0].screenX;
            this.touchStartY = e.changedTouches[0].screenY;
            touchStartTime = Date.now();

            // 找到最近的文章卡片
            this.currentSwipeElement = e.target.closest('.article-card');
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            this.touchEndX = e.changedTouches[0].screenX;
            this.touchEndY = e.changedTouches[0].screenY;

            const touchDuration = Date.now() - touchStartTime;
            const deltaX = Math.abs(this.touchEndX - this.touchStartX);
            const deltaY = Math.abs(this.touchEndY - this.touchStartY);

            // 只有当滑动距离超过阈值且不是快速点击时才处理滑动
            // 快速点击（<200ms）或小距离移动（<30px）视为点击，不处理滑动
            if (touchDuration > 200 && (deltaX > 30 || deltaY > 30)) {
                this.handleSwipe();
            }

            this.currentSwipeElement = null;
        }, { passive: true });
    }

    handleSwipe() {
        if (!this.currentSwipeElement) return;

        const deltaX = this.touchEndX - this.touchStartX;
        const deltaY = this.touchEndY - this.touchStartY;

        // 确保是水平滑动，且滑动距离足够大
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > this.swipeThreshold) {
            const articleId = this.currentSwipeElement.dataset.id;

            if (deltaX > 0) {
                // 右滑 - 标记已读
                if (typeof toggleReadStatus === 'function') {
                    toggleReadStatus(articleId);
                    this.showSwipeFeedback('已标记为已读');
                }
            } else {
                // 左滑 - 显示操作按钮
                this.showActionButtons(this.currentSwipeElement);
            }
        }
    }

    showActionButtons(card) {
        // 移除其他卡片的操作按钮
        document.querySelectorAll('.mobile-actions').forEach(el => el.remove());

        const actions = document.createElement('div');
        actions.className = 'mobile-actions';
        actions.innerHTML = `
            <button onclick="event.stopPropagation(); toggleFavorite('${card.dataset.id}')">⭐</button>
            <button onclick="event.stopPropagation(); toggleReadLater('${card.dataset.id}')">📌</button>
            <button onclick="event.stopPropagation(); this.parentElement.remove()">✕</button>
        `;

        card.appendChild(actions);

        // 5秒后自动隐藏
        setTimeout(() => {
            if (actions.parentElement) {
                actions.remove();
            }
        }, 5000);
    }

    showSwipeFeedback(message) {
        const feedback = document.createElement('div');
        feedback.className = 'swipe-feedback';
        feedback.textContent = message;
        document.body.appendChild(feedback);

        setTimeout(() => feedback.classList.add('visible'), 10);
        setTimeout(() => {
            feedback.classList.remove('visible');
            setTimeout(() => feedback.remove(), 300);
        }, 2000);
    }

    setupBottomNav() {
        if (!this.isMobile) return;

        // 检查是否已存在
        if (document.querySelector('.mobile-bottom-nav')) return;

        const nav = document.createElement('div');
        nav.className = 'mobile-bottom-nav';
        nav.innerHTML = `
            <button onclick="mobileAdapter.scrollToTopAndReset()">
                <span>🏠</span>
                <small>首页</small>
            </button>
            <button onclick="mobileAdapter.openMobileSearch()">
                <span>🔍</span>
                <small>搜索</small>
            </button>
            <button onclick="mobileAdapter.toggleUnreadFilter()">
                <span>📬</span>
                <small>未读</small>
            </button>
            <button onclick="mobileAdapter.toggleFavoritesFilter()">
                <span>⭐</span>
                <small>收藏</small>
            </button>
            <button onclick="mobileAdapter.openFilterPanel()">
                <span>☰</span>
                <small>筛选</small>
            </button>
        `;

        document.body.appendChild(nav);

        // 添加移动端布局类
        document.body.classList.add('mobile-layout');
    }

    // 滚动到顶部并重置筛选
    scrollToTopAndReset() {
        // 重置所有筛选条件
        if (typeof setReadFilter === 'function') setReadFilter('all');
        if (typeof setCategory === 'function') setCategory('all');
        const favCheckbox = document.getElementById('favoritesOnly');
        if (favCheckbox && favCheckbox.checked) {
            favCheckbox.checked = false;
            if (typeof filterArticles === 'function') filterArticles();
        }
        // 滚动到顶部
        window.scrollTo({ top: 0, behavior: 'smooth' });
        this.showSwipeFeedback('已返回首页');
    }

    // 打开移动端搜索
    openMobileSearch() {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            // 滚动到搜索框位置
            searchInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
            setTimeout(() => {
                searchInput.focus();
                searchInput.select();
            }, 300);
        }
    }

    // 切换未读筛选
    toggleUnreadFilter() {
        const currentFilter = typeof currentReadFilter !== 'undefined' ? currentReadFilter : 'all';
        if (currentFilter === 'unread') {
            if (typeof setReadFilter === 'function') setReadFilter('all');
            this.showSwipeFeedback('显示全部文献');
            this.updateNavButtonState('unread', false);
        } else {
            if (typeof setReadFilter === 'function') setReadFilter('unread');
            this.showSwipeFeedback('只显示未读');
            this.updateNavButtonState('unread', true);
        }
    }

    // 切换收藏筛选
    toggleFavoritesFilter() {
        const favCheckbox = document.getElementById('favoritesOnly');
        if (favCheckbox) {
            favCheckbox.checked = !favCheckbox.checked;
            if (typeof filterArticles === 'function') filterArticles();
            if (favCheckbox.checked) {
                this.showSwipeFeedback('只显示收藏');
                this.updateNavButtonState('favorites', true);
            } else {
                this.showSwipeFeedback('显示全部文献');
                this.updateNavButtonState('favorites', false);
            }
        }
    }

    // 打开筛选面板
    openFilterPanel() {
        // 检查是否已存在筛选面板
        let panel = document.getElementById('mobileFilterPanel');
        if (panel) {
            panel.classList.toggle('visible');
            return;
        }

        // 创建移动端筛选面板
        panel = document.createElement('div');
        panel.id = 'mobileFilterPanel';
        panel.className = 'mobile-filter-panel';
        panel.innerHTML = `
            <div class="mobile-filter-header">
                <h3>筛选选项</h3>
                <button onclick="document.getElementById('mobileFilterPanel').classList.remove('visible')">✕</button>
            </div>
            <div class="mobile-filter-content">
                <div class="mobile-filter-section">
                    <h4>阅读状态</h4>
                    <div class="mobile-filter-buttons">
                        <button onclick="setReadFilter('all'); mobileAdapter.closeFilterPanel()">全部</button>
                        <button onclick="setReadFilter('unread'); mobileAdapter.closeFilterPanel()">未读</button>
                        <button onclick="setReadFilter('read'); mobileAdapter.closeFilterPanel()">已读</button>
                        <button onclick="setReadFilter('later'); mobileAdapter.closeFilterPanel()">待读</button>
                    </div>
                </div>
                <div class="mobile-filter-section">
                    <h4>文献分类</h4>
                    <div class="mobile-filter-buttons">
                        <button onclick="setCategory('all'); mobileAdapter.closeFilterPanel()">全部</button>
                        <button onclick="setCategory('ai-related'); mobileAdapter.closeFilterPanel()">🤖 AI相关</button>
                        <button onclick="setCategory('ai-unrelated'); mobileAdapter.closeFilterPanel()">📚 非AI</button>
                    </div>
                </div>
                <div class="mobile-filter-section">
                    <h4>快捷操作</h4>
                    <div class="mobile-filter-buttons">
                        <button onclick="mobileAdapter.toggleFavoritesFilter(); mobileAdapter.closeFilterPanel()">⭐ 只看收藏</button>
                        <button onclick="clearSearch(); mobileAdapter.closeFilterPanel()">🔄 清除搜索</button>
                        <button onclick="clearDateFilter(); mobileAdapter.closeFilterPanel()">📅 清除日期</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(panel);

        // 点击背景关闭
        panel.addEventListener('click', (e) => {
            if (e.target === panel) {
                panel.classList.remove('visible');
            }
        });

        // 显示面板
        setTimeout(() => panel.classList.add('visible'), 10);
    }

    // 关闭筛选面板
    closeFilterPanel() {
        const panel = document.getElementById('mobileFilterPanel');
        if (panel) {
            panel.classList.remove('visible');
        }
    }

    // 更新导航按钮状态
    updateNavButtonState(type, active) {
        const nav = document.querySelector('.mobile-bottom-nav');
        if (!nav) return;

        const buttons = nav.querySelectorAll('button');
        buttons.forEach(btn => {
            const small = btn.querySelector('small');
            if (small) {
                if (type === 'unread' && small.textContent === '未读') {
                    btn.classList.toggle('active', active);
                } else if (type === 'favorites' && small.textContent === '收藏') {
                    btn.classList.toggle('active', active);
                }
            }
        });
    }

    setupPullToRefresh() {
        let startY = 0;
        let pulling = false;
        let triggered = false;

        document.addEventListener('touchstart', (e) => {
            // 只有在页面顶部时才启用下拉刷新
            if (window.pageYOffset <= 0) {
                startY = e.touches[0].pageY;
                pulling = true;
                triggered = false;
            }
        }, { passive: true });

        document.addEventListener('touchmove', (e) => {
            if (!pulling) return;

            const currentY = e.touches[0].pageY;
            const pullDistance = currentY - startY;

            // 只有向下拉动才显示指示器
            if (pullDistance > 60 && !triggered) {
                this.showPullToRefreshIndicator();
            }
        }, { passive: true });

        document.addEventListener('touchend', () => {
            if (pulling) {
                const indicator = document.getElementById('pullToRefreshIndicator');
                const wasVisible = indicator && indicator.classList.contains('visible');

                pulling = false;
                this.hidePullToRefreshIndicator();

                // 只有当指示器显示时才触发刷新
                if (wasVisible && !triggered) {
                    triggered = true;
                    this.showSwipeFeedback('正在刷新...');

                    // 重新加载数据
                    if (typeof loadArticles === 'function') {
                        loadArticles().then(() => {
                            this.showSwipeFeedback('刷新完成');
                        }).catch(() => {
                            this.showSwipeFeedback('刷新失败');
                        });
                    } else if (typeof filterArticles === 'function') {
                        filterArticles();
                        this.showSwipeFeedback('已刷新');
                    }
                }
            }
        }, { passive: true });
    }

    showPullToRefreshIndicator() {
        let indicator = document.getElementById('pullToRefreshIndicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'pullToRefreshIndicator';
            indicator.className = 'pull-to-refresh';
            indicator.innerHTML = '<div class="refresh-spinner"></div><span>释放刷新</span>';
            document.body.prepend(indicator);
        }
        indicator.classList.add('visible');
    }

    hidePullToRefreshIndicator() {
        const indicator = document.getElementById('pullToRefreshIndicator');
        if (indicator) {
            indicator.classList.remove('visible');
            setTimeout(() => indicator.remove(), 300);
        }
    }

    optimizeTouchTargets() {
        // 确保所有可点击元素至少44x44px
        const style = document.createElement('style');
        style.textContent = `
            @media (max-width: 767px) {
                button, a, .clickable {
                    min-width: 44px;
                    min-height: 44px;
                }
            }
        `;
        document.head.appendChild(style);
    }
}

// ========================================
// 全局实例更新
// ========================================

let virtualScrollManager = null;
let lazyLoadManager = null;
let incrementalLoader = null;
let cacheManager = null;
let mobileAdapter = null;

// 搜索结果缓存实例
let searchCache = null;

// 更新初始化函数
const originalInitAdvancedFeatures = initAdvancedFeatures;

initAdvancedFeatures = function () {
    // 调用原有初始化
    if (originalInitAdvancedFeatures) {
        originalInitAdvancedFeatures();
    }

    // 初始化性能优化功能
    virtualScrollManager = new VirtualScrollManager();

    lazyLoadManager = new LazyLoadManager();
    lazyLoadManager.init();

    incrementalLoader = new IncrementalLoader(50);

    cacheManager = new CacheManager(50);
    searchCache = new CacheManager(50);

    mobileAdapter = new MobileAdapter();
    mobileAdapter.init();

    console.log('✅ 所有高级功能已初始化');
};

// 导出到全局
if (typeof window !== 'undefined') {
    window.virtualScrollManager = virtualScrollManager;
    window.lazyLoadManager = lazyLoadManager;
    window.incrementalLoader = incrementalLoader;
    window.cacheManager = cacheManager;
    window.searchCache = searchCache;
    window.mobileAdapter = mobileAdapter;
}


// ========================================
// 研究趋势预测器
// ========================================

class TrendPredictor {
    constructor() {
        this.historicalData = [];
        this.predictions = [];
        this.confidenceThreshold = 0.7;
    }

    analyze(articles) {
        // 按月分组文章
        const monthlyData = this.groupByMonth(articles);

        // 计算增长率
        const growthRates = this.calculateGrowthRates(monthlyData);

        // 生成预测
        this.predictions = this.generatePredictions(monthlyData, growthRates);

        // 识别新兴和衰退主题
        const emergingTopics = this.identifyEmergingTopics(articles);
        const decliningTopics = this.identifyDecliningTopics(articles);

        return {
            monthlyData,
            growthRates,
            predictions: this.predictions,
            emergingTopics,
            decliningTopics,
            aiVsNonAI: this.compareAITrends(articles)
        };
    }

    groupByMonth(articles) {
        const groups = {};

        articles.forEach(article => {
            if (!article.pub_date) return;

            const month = article.pub_date.substring(0, 7); // YYYY-MM
            if (!groups[month]) {
                groups[month] = {
                    total: 0,
                    ai: 0,
                    nonAi: 0,
                    articles: []
                };
            }

            groups[month].total++;
            if (article.is_ai_related) {
                groups[month].ai++;
            } else {
                groups[month].nonAi++;
            }
            groups[month].articles.push(article);
        });

        // 转换为数组并排序
        return Object.entries(groups)
            .map(([month, data]) => ({ month, ...data }))
            .sort((a, b) => a.month.localeCompare(b.month));
    }

    calculateGrowthRates(monthlyData) {
        const rates = [];

        for (let i = 1; i < monthlyData.length; i++) {
            const prev = monthlyData[i - 1];
            const curr = monthlyData[i];

            const totalRate = prev.total > 0
                ? ((curr.total - prev.total) / prev.total) * 100
                : 0;

            const aiRate = prev.ai > 0
                ? ((curr.ai - prev.ai) / prev.ai) * 100
                : 0;

            rates.push({
                month: curr.month,
                totalRate,
                aiRate,
                confidence: this.calculateConfidence(prev, curr)
            });
        }

        return rates;
    }

    calculateConfidence(prev, curr) {
        // 基于数据量和趋势稳定性计算置信度
        const dataVolume = Math.min((prev.total + curr.total) / 100, 1);
        const stability = 1 - Math.abs(curr.total - prev.total) / Math.max(prev.total, curr.total, 1);

        return (dataVolume * 0.6 + stability * 0.4);
    }

    generatePredictions(monthlyData, growthRates) {
        if (monthlyData.length < 3) return [];

        const predictions = [];
        const recentData = monthlyData.slice(-6); // 最近6个月
        const avgGrowth = growthRates.slice(-6).reduce((sum, r) => sum + r.totalRate, 0) / 6;

        // 预测未来3个月
        let lastMonth = recentData[recentData.length - 1];

        for (let i = 1; i <= 3; i++) {
            const predictedTotal = Math.round(lastMonth.total * (1 + avgGrowth / 100));
            const predictedAI = Math.round(lastMonth.ai * (1 + avgGrowth / 100));

            const nextMonth = this.getNextMonth(lastMonth.month);

            predictions.push({
                month: nextMonth,
                predictedTotal,
                predictedAI,
                predictedNonAI: predictedTotal - predictedAI,
                confidence: Math.max(0.5, 1 - i * 0.15) // 置信度随时间递减
            });

            lastMonth = {
                month: nextMonth,
                total: predictedTotal,
                ai: predictedAI
            };
        }

        return predictions;
    }

    getNextMonth(monthStr) {
        const [year, month] = monthStr.split('-').map(Number);
        const date = new Date(year, month, 1); // month is 0-indexed in Date
        const nextDate = new Date(date.getFullYear(), date.getMonth() + 1, 1);

        const y = nextDate.getFullYear();
        const m = String(nextDate.getMonth() + 1).padStart(2, '0');
        return `${y}-${m}`;
    }

    identifyEmergingTopics(articles) {
        // 提取最近3个月的关键词
        const recentArticles = this.getRecentArticles(articles, 3);
        const olderArticles = this.getOlderArticles(articles, 3, 6);

        const recentKeywords = this.extractKeywords(recentArticles);
        const olderKeywords = this.extractKeywords(olderArticles);

        // 找出增长最快的关键词
        const emerging = [];

        for (const [keyword, recentCount] of Object.entries(recentKeywords)) {
            const olderCount = olderKeywords[keyword] || 0;
            const growthRate = olderCount > 0
                ? ((recentCount - olderCount) / olderCount) * 100
                : 100;

            if (growthRate > 50 && recentCount >= 3) {
                emerging.push({
                    keyword,
                    recentCount,
                    olderCount,
                    growthRate: growthRate.toFixed(1)
                });
            }
        }

        return emerging.sort((a, b) => b.growthRate - a.growthRate).slice(0, 10);
    }

    identifyDecliningTopics(articles) {
        const recentArticles = this.getRecentArticles(articles, 3);
        const olderArticles = this.getOlderArticles(articles, 3, 6);

        const recentKeywords = this.extractKeywords(recentArticles);
        const olderKeywords = this.extractKeywords(olderArticles);

        const declining = [];

        for (const [keyword, olderCount] of Object.entries(olderKeywords)) {
            const recentCount = recentKeywords[keyword] || 0;
            const declineRate = ((olderCount - recentCount) / olderCount) * 100;

            if (declineRate > 30 && olderCount >= 3) {
                declining.push({
                    keyword,
                    recentCount,
                    olderCount,
                    declineRate: declineRate.toFixed(1)
                });
            }
        }

        return declining.sort((a, b) => b.declineRate - a.declineRate).slice(0, 10);
    }

    getRecentArticles(articles, months) {
        const cutoffDate = new Date();
        cutoffDate.setMonth(cutoffDate.getMonth() - months);
        const cutoffStr = cutoffDate.toISOString().substring(0, 7);

        return articles.filter(a => a.pub_date && a.pub_date >= cutoffStr);
    }

    getOlderArticles(articles, startMonths, endMonths) {
        const startDate = new Date();
        startDate.setMonth(startDate.getMonth() - endMonths);
        const startStr = startDate.toISOString().substring(0, 7);

        const endDate = new Date();
        endDate.setMonth(endDate.getMonth() - startMonths);
        const endStr = endDate.toISOString().substring(0, 7);

        return articles.filter(a =>
            a.pub_date && a.pub_date >= startStr && a.pub_date < endStr
        );
    }

    extractKeywords(articles) {
        const keywords = {};
        const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those']);

        articles.forEach(article => {
            const text = [
                article.title || '',
                article.abstract || ''
            ].join(' ').toLowerCase();

            // 简单的词频统计
            const words = text.match(/\b[a-z]{4,}\b/g) || [];

            words.forEach(word => {
                if (!stopWords.has(word)) {
                    keywords[word] = (keywords[word] || 0) + 1;
                }
            });
        });

        return keywords;
    }

    compareAITrends(articles) {
        const monthlyData = this.groupByMonth(articles);

        return {
            labels: monthlyData.map(d => d.month),
            aiData: monthlyData.map(d => d.ai),
            nonAiData: monthlyData.map(d => d.nonAi),
            totalData: monthlyData.map(d => d.total)
        };
    }

    visualize(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const analysis = this.analyze(allArticles || []);

        let html = `
            <div class="trend-analysis">
                <h3>📈 研究趋势预测</h3>
                
                <div class="trend-section">
                    <h4>月度发表趋势</h4>
                    <div class="trend-chart" id="monthlyTrendChart"></div>
                </div>
                
                <div class="trend-section">
                    <h4>未来3个月预测</h4>
                    <div class="predictions">
                        ${analysis.predictions.map(p => `
                            <div class="prediction-item">
                                <strong>${p.month}</strong>
                                <span>预测: ${p.predictedTotal} 篇</span>
                                <span class="confidence">置信度: ${(p.confidence * 100).toFixed(0)}%</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="trend-section">
                    <h4>🔥 新兴研究主题</h4>
                    <div class="topic-list">
                        ${analysis.emergingTopics.map(t => `
                            <div class="topic-item emerging">
                                <span class="topic-keyword">${t.keyword}</span>
                                <span class="topic-growth">↑ ${t.growthRate}%</span>
                                <span class="topic-count">${t.recentCount} 篇</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="trend-section">
                    <h4>📉 衰退研究主题</h4>
                    <div class="topic-list">
                        ${analysis.decliningTopics.map(t => `
                            <div class="topic-item declining">
                                <span class="topic-keyword">${t.keyword}</span>
                                <span class="topic-decline">↓ ${t.declineRate}%</span>
                                <span class="topic-count">${t.recentCount} 篇</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="trend-section">
                    <h4>🤖 AI vs 非AI 趋势对比</h4>
                    <div class="trend-chart" id="aiComparisonChart"></div>
                </div>
            </div>
        `;

        container.innerHTML = html;

        // 这里可以集成图表库（如 Chart.js）来绘制图表
        // 为了简化，我们使用简单的文本显示
    }
}

// ========================================
// 主题演化分析器
// ========================================

class TopicEvolutionAnalyzer {
    constructor() {
        this.timeSlices = [];
        this.topicEvolution = [];
        this.sliceMonths = 3; // 每个时间切片的月数
    }

    analyze(articles) {
        // 创建时间切片
        this.timeSlices = this.createTimeSlices(articles);

        // 提取每个时期的主题
        const topicsByPeriod = this.timeSlices.map(slice => ({
            period: slice.period,
            topics: this.extractTopics(slice.articles)
        }));

        // 跟踪主题演化
        this.topicEvolution = this.trackEvolution(topicsByPeriod);

        // 识别主题合并和分裂
        const merges = this.identifyMerges(this.topicEvolution);
        const splits = this.identifySplits(this.topicEvolution);

        // 确定主题生命周期
        const lifecycles = this.determineLifecycles(this.topicEvolution);

        return {
            timeSlices: this.timeSlices,
            topicsByPeriod,
            evolution: this.topicEvolution,
            merges,
            splits,
            lifecycles
        };
    }

    createTimeSlices(articles) {
        if (articles.length === 0) return [];

        // 找出最早和最晚的日期
        const dates = articles
            .filter(a => a.pub_date)
            .map(a => a.pub_date)
            .sort();

        if (dates.length === 0) return [];

        const startDate = new Date(dates[0]);
        const endDate = new Date(dates[dates.length - 1]);

        const slices = [];
        let currentDate = new Date(startDate);

        while (currentDate <= endDate) {
            const sliceEnd = new Date(currentDate);
            sliceEnd.setMonth(sliceEnd.getMonth() + this.sliceMonths);

            const periodStart = currentDate.toISOString().substring(0, 7);
            const periodEnd = sliceEnd.toISOString().substring(0, 7);

            const sliceArticles = articles.filter(a =>
                a.pub_date && a.pub_date >= periodStart && a.pub_date < periodEnd
            );

            if (sliceArticles.length > 0) {
                slices.push({
                    period: `${periodStart} ~ ${periodEnd}`,
                    start: periodStart,
                    end: periodEnd,
                    articles: sliceArticles
                });
            }

            currentDate = sliceEnd;
        }

        return slices;
    }

    extractTopics(articles) {
        const keywords = {};

        articles.forEach(article => {
            const text = [
                article.title || '',
                article.abstract || ''
            ].join(' ').toLowerCase();

            const words = text.match(/\b[a-z]{4,}\b/g) || [];
            const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did']);

            words.forEach(word => {
                if (!stopWords.has(word)) {
                    keywords[word] = (keywords[word] || 0) + 1;
                }
            });
        });

        // 返回前20个主题
        return Object.entries(keywords)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 20)
            .map(([keyword, count]) => ({ keyword, count }));
    }

    trackEvolution(topicsByPeriod) {
        const evolution = [];

        for (let i = 0; i < topicsByPeriod.length; i++) {
            const current = topicsByPeriod[i];
            const previous = i > 0 ? topicsByPeriod[i - 1] : null;

            current.topics.forEach(topic => {
                const prevTopic = previous?.topics.find(t => t.keyword === topic.keyword);

                evolution.push({
                    period: current.period,
                    keyword: topic.keyword,
                    count: topic.count,
                    previousCount: prevTopic?.count || 0,
                    change: prevTopic
                        ? ((topic.count - prevTopic.count) / prevTopic.count * 100).toFixed(1)
                        : 'new'
                });
            });
        }

        return evolution;
    }

    calculateSimilarity(topic1, topic2) {
        // 简单的字符串相似度（可以使用更复杂的算法）
        const longer = topic1.length > topic2.length ? topic1 : topic2;
        const shorter = topic1.length > topic2.length ? topic2 : topic1;

        if (longer.length === 0) return 1.0;

        const editDistance = this.levenshteinDistance(longer, shorter);
        return (longer.length - editDistance) / longer.length;
    }

    levenshteinDistance(str1, str2) {
        const matrix = [];

        for (let i = 0; i <= str2.length; i++) {
            matrix[i] = [i];
        }

        for (let j = 0; j <= str1.length; j++) {
            matrix[0][j] = j;
        }

        for (let i = 1; i <= str2.length; i++) {
            for (let j = 1; j <= str1.length; j++) {
                if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
                    matrix[i][j] = matrix[i - 1][j - 1];
                } else {
                    matrix[i][j] = Math.min(
                        matrix[i - 1][j - 1] + 1,
                        matrix[i][j - 1] + 1,
                        matrix[i - 1][j] + 1
                    );
                }
            }
        }

        return matrix[str2.length][str1.length];
    }

    identifyMerges(evolution) {
        // 识别主题合并（多个主题合并为一个）
        const merges = [];
        // 简化实现：检测相似关键词的合并

        return merges;
    }

    identifySplits(evolution) {
        // 识别主题分裂（一个主题分裂为多个）
        const splits = [];
        // 简化实现

        return splits;
    }

    determineLifecycles(evolution) {
        const lifecycles = {};

        evolution.forEach(item => {
            if (!lifecycles[item.keyword]) {
                lifecycles[item.keyword] = {
                    keyword: item.keyword,
                    firstSeen: item.period,
                    lastSeen: item.period,
                    peakCount: item.count,
                    currentCount: item.count,
                    trend: []
                };
            }

            const lifecycle = lifecycles[item.keyword];
            lifecycle.lastSeen = item.period;
            lifecycle.peakCount = Math.max(lifecycle.peakCount, item.count);
            lifecycle.currentCount = item.count;
            lifecycle.trend.push(item.count);
        });

        // 分类生命周期阶段
        Object.values(lifecycles).forEach(lc => {
            const trend = lc.trend;
            const avgGrowth = trend.length > 1
                ? (trend[trend.length - 1] - trend[0]) / trend.length
                : 0;

            if (trend.length <= 2) {
                lc.stage = 'emerging'; // 新兴
            } else if (avgGrowth > 2) {
                lc.stage = 'growing'; // 增长
            } else if (avgGrowth > -2) {
                lc.stage = 'mature'; // 成熟
            } else {
                lc.stage = 'declining'; // 衰退
            }
        });

        return Object.values(lifecycles);
    }

    visualize(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const analysis = this.analyze(allArticles || []);

        let html = `
            <div class="evolution-analysis">
                <h3>🔄 研究主题演化分析</h3>
                
                <div class="evolution-section">
                    <h4>时间切片概览</h4>
                    <div class="time-slices">
                        ${analysis.timeSlices.map(slice => `
                            <div class="time-slice">
                                <strong>${slice.period}</strong>
                                <span>${slice.articles.length} 篇文献</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="evolution-section">
                    <h4>主题生命周期</h4>
                    <div class="lifecycle-grid">
                        ${['emerging', 'growing', 'mature', 'declining'].map(stage => {
            const topics = analysis.lifecycles.filter(lc => lc.stage === stage);
            const stageNames = {
                'emerging': '🌱 新兴',
                'growing': '📈 增长',
                'mature': '🎯 成熟',
                'declining': '📉 衰退'
            };

            return `
                                <div class="lifecycle-stage">
                                    <h5>${stageNames[stage]} (${topics.length})</h5>
                                    <div class="topic-tags">
                                        ${topics.slice(0, 10).map(t => `
                                            <span class="topic-tag ${stage}">${t.keyword}</span>
                                        `).join('')}
                                    </div>
                                </div>
                            `;
        }).join('')}
                    </div>
                </div>
                
                <div class="evolution-section">
                    <h4>主题演化流</h4>
                    <p class="evolution-note">
                        💡 显示主题随时间的变化趋势。可以使用 Sankey 图或流图进行可视化。
                    </p>
                </div>
                
                <div class="evolution-section">
                    <h4>导出数据</h4>
                    <button onclick="topicEvolutionAnalyzer.exportData()" class="export-btn">
                        📥 导出演化数据 (CSV)
                    </button>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    exportData() {
        const analysis = this.analyze(allArticles || []);

        let csv = 'Period,Keyword,Count,Previous Count,Change,Stage\n';

        analysis.evolution.forEach(item => {
            const lifecycle = analysis.lifecycles.find(lc => lc.keyword === item.keyword);
            csv += `"${item.period}","${item.keyword}",${item.count},${item.previousCount},"${item.change}","${lifecycle?.stage || 'unknown'}"\n`;
        });

        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `topic_evolution_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        if (typeof showToast === 'function') {
            showToast('演化数据已导出');
        }
    }
}

// ========================================
// 全局实例
// ========================================

let trendPredictor = null;
let topicEvolutionAnalyzer = null;

// 导出到全局
if (typeof window !== 'undefined') {
    window.TrendPredictor = TrendPredictor;
    window.TopicEvolutionAnalyzer = TopicEvolutionAnalyzer;
    window.trendPredictor = trendPredictor;
    window.topicEvolutionAnalyzer = topicEvolutionAnalyzer;
}
