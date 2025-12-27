/**
 * 文献追踪系统 - 前端应用
 * 支持：可折叠卡片、AI分类筛选、主题切换、键盘快捷键、关键词高亮
 *       阅读状态追踪、搜索历史
 */

// ========================================
// 全局状态
// ========================================

let allArticles = [];
let filteredArticles = [];
let favorites = new Set();
let readArticles = new Set();  // 已读文献
let readLater = new Set();  // 稍后阅读
let expandedCards = new Set();
let searchHistory = [];  // 搜索历史
let currentPage = 1;
let focusedIndex = -1;
let currentCategory = 'all'; // 'all' | 'ai-related' | 'ai-unrelated'
let currentReadFilter = 'all'; // 'all' | 'unread' | 'read' | 'later'
let currentTheme = 'light';

const PAGE_SIZE = 50;
const AI_KEYWORDS = ['machine', 'learn', 'neural', 'network'];
const THEME_STORAGE_KEY = 'literature_theme';
const FAVORITES_STORAGE_KEY = 'literature_favorites';
const READ_STORAGE_KEY = 'literature_read';
const READ_LATER_STORAGE_KEY = 'literature_read_later';
const SEARCH_HISTORY_KEY = 'literature_search_history';
const MAX_SEARCH_HISTORY = 10;

// 期刊分组定义
const JOURNAL_GROUPS = {
    'top': {
        name: '顶刊',
        patterns: ['nature', 'science', 'physical review letters', 'prl', 'Phys. Rev. lett.', 'journal of the american chemical society', 'jacs', 'angewandte', 'pnas', 'proceedings of the national academy', 'advanced materials', 'adv. mater', 'editor', 'suggestion', 'physics news', 'physics today', 'Rev. Mod. Phys.']
    },
    'nature': {
        name: 'Nature系列',
        patterns: ['nature', 'npj']
    },
    'aps': {
        name: 'APS系列',
        patterns: ['physical review', 'prl', 'prx', 'prb', 'pr materials', 'pr research', 'pr energy', 'pr applied', 'physics', 'Phys. Rev.', 'Rev. Mod. Phys.']
    },
    'acs': {
        name: 'ACS系列',
        patterns: ['acs', 'journal of the american chemical', 'jacs', 'nano letters', 'chemical reviews', 'j. phys. chem', 'j. chem. theory']
    },
    'wiley': {
        name: 'Wiley系列',
        patterns: ['wiley', 'angewandte', 'angew', 'advanced materials', 'adv. mater', 'adv. funct', 'advanced functional', 'advanced energy', 'small', 'chemphyschem']
    },
    'rsc': {
        name: 'RSC系列',
        patterns: ['rsc', 'royal society of chemistry', 'digital discovery', 'chem. sci', 'chemical science']
    },
    'elsevier': {
        name: 'Elsevier系列',
        patterns: ['computational materials science', 'computer physics communications', 'materials today', 'sciencedirect']
    },
    'preprint': {
        name: '预印本',
        patterns: ['arxiv', 'chemrxiv', 'researchsquare', 'preprint']
    }
};

// ========================================
// 初始化
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadFavorites();
    loadReadStatus();
    loadReadLater();
    loadSearchHistory();
    loadArticles();
    setupSearch();
    setupKeyboardNavigation();
    createTooltip();
});

// ========================================
// 主题管理
// ========================================

function initTheme() {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    currentTheme = saved || 'light';
    applyTheme(currentTheme);
}

function getCurrentTheme() {
    return currentTheme;
}

function setTheme(theme) {
    currentTheme = theme;
    localStorage.setItem(THEME_STORAGE_KEY, theme);
    applyTheme(theme);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButton();
}

function toggleTheme() {
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
}

function updateThemeButton() {
    const btn = document.getElementById('themeToggle');
    if (btn) {
        btn.innerHTML = currentTheme === 'light' ? '🌙' : '☀️';
        btn.title = currentTheme === 'light' ? '切换到深色模式' : '切换到浅色模式';
    }
}

// ========================================
// 收藏管理
// ========================================

function loadFavorites() {
    try {
        const saved = localStorage.getItem(FAVORITES_STORAGE_KEY);
        if (saved) {
            favorites = new Set(JSON.parse(saved));
        }
    } catch (e) {
        console.warn('无法加载收藏数据:', e);
    }
}

function saveFavorites() {
    try {
        localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify([...favorites]));
    } catch (e) {
        console.warn('无法保存收藏数据:', e);
    }
}

function toggleFavorite(id) {
    if (favorites.has(id)) {
        favorites.delete(id);
    } else {
        favorites.add(id);
    }

    saveFavorites();

    const article = allArticles.find(a => a.id === id);
    if (article) {
        article.is_favorite = favorites.has(id);
    }

    updateFavCount();

    if (document.getElementById('favoritesOnly')?.checked) {
        filterArticles();
    } else {
        updateCardFavoriteUI(id);
    }
}

function updateCardFavoriteUI(id) {
    const card = document.getElementById(`article-${id}`);
    if (card) {
        card.classList.toggle('favorite', favorites.has(id));
        const btn = card.querySelector('.favorite-btn');
        if (btn) {
            btn.innerHTML = favorites.has(id) ? '⭐' : '☆';
            btn.title = favorites.has(id) ? '取消收藏' : '添加收藏';
        }
    }
}

function updateFavCount() {
    const el = document.getElementById('favCount');
    if (el) el.textContent = favorites.size;
}

// ========================================
// 阅读状态管理
// ========================================

function loadReadStatus() {
    try {
        const saved = localStorage.getItem(READ_STORAGE_KEY);
        if (saved) {
            readArticles = new Set(JSON.parse(saved));
        }
    } catch (e) {
        console.warn('无法加载阅读状态:', e);
    }
}

function saveReadStatus() {
    try {
        localStorage.setItem(READ_STORAGE_KEY, JSON.stringify([...readArticles]));
    } catch (e) {
        console.warn('无法保存阅读状态:', e);
    }
}

function toggleReadStatus(id) {
    if (readArticles.has(id)) {
        readArticles.delete(id);
    } else {
        readArticles.add(id);
    }

    saveReadStatus();

    const article = allArticles.find(a => a.id === id);
    if (article) {
        article.is_read = readArticles.has(id);
    }

    updateUnreadCount();

    if (currentReadFilter !== 'all') {
        filterArticles();
    } else {
        updateCardReadUI(id);
    }
}

function updateCardReadUI(id) {
    const card = document.getElementById(`article-${id}`);
    if (card) {
        const isRead = readArticles.has(id);
        card.classList.toggle('read', isRead);
        const btn = card.querySelector('.read-btn');
        if (btn) {
            btn.innerHTML = isRead ? '✓ 已读' : '○ 未读';
            btn.title = isRead ? '标记为未读' : '标记为已读';
            btn.classList.toggle('is-read', isRead);
        }
    }
}

function updateUnreadCount() {
    const unreadCount = allArticles.length - readArticles.size;
    const el = document.getElementById('unreadCount');
    if (el) el.textContent = unreadCount;
}

function setReadFilter(filter) {
    currentReadFilter = filter;

    document.querySelectorAll('.read-filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });

    filterArticles();
}

// ========================================
// 稍后阅读管理
// ========================================

function loadReadLater() {
    try {
        const saved = localStorage.getItem(READ_LATER_STORAGE_KEY);
        if (saved) {
            readLater = new Set(JSON.parse(saved));
        }
    } catch (e) {
        console.warn('无法加载稍后阅读:', e);
    }
}

function saveReadLater() {
    try {
        localStorage.setItem(READ_LATER_STORAGE_KEY, JSON.stringify([...readLater]));
    } catch (e) {
        console.warn('无法保存稍后阅读:', e);
    }
}

function toggleReadLater(id) {
    if (readLater.has(id)) {
        readLater.delete(id);
    } else {
        readLater.add(id);
    }

    saveReadLater();

    const article = allArticles.find(a => a.id === id);
    if (article) {
        article.is_read_later = readLater.has(id);
    }

    updateReadLaterCount();

    if (currentReadFilter === 'later') {
        filterArticles();
    } else {
        updateCardReadLaterUI(id);
    }
}

function updateCardReadLaterUI(id) {
    const card = document.getElementById(`article-${id}`);
    if (card) {
        const isLater = readLater.has(id);
        card.classList.toggle('read-later', isLater);
        const btn = card.querySelector('.read-later-btn');
        if (btn) {
            btn.innerHTML = isLater ? '📌' : '📍';
            btn.title = isLater ? '从待读列表移除' : '添加到待读列表';
            btn.classList.toggle('is-later', isLater);
        }
    }
}

function updateReadLaterCount() {
    const el = document.getElementById('readLaterCount');
    if (el) el.textContent = readLater.size;
}

// ========================================
// 搜索历史管理
// ========================================

function loadSearchHistory() {
    try {
        const saved = localStorage.getItem(SEARCH_HISTORY_KEY);
        if (saved) {
            searchHistory = JSON.parse(saved);
        }
    } catch (e) {
        console.warn('无法加载搜索历史:', e);
    }
}

function saveSearchHistory() {
    try {
        localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(searchHistory));
    } catch (e) {
        console.warn('无法保存搜索历史:', e);
    }
}

function addToSearchHistory(term) {
    if (!term || term.trim().length === 0) return;

    term = term.trim();

    // 移除重复项
    searchHistory = searchHistory.filter(h => h.toLowerCase() !== term.toLowerCase());

    // 添加到开头
    searchHistory.unshift(term);

    // 限制数量
    if (searchHistory.length > MAX_SEARCH_HISTORY) {
        searchHistory = searchHistory.slice(0, MAX_SEARCH_HISTORY);
    }

    saveSearchHistory();
    renderSearchHistory();
}

function clearSearchHistory() {
    searchHistory = [];
    saveSearchHistory();
    renderSearchHistory();
    hideSearchHistory();
}

function renderSearchHistory() {
    const container = document.getElementById('searchHistoryList');
    if (!container) return;

    if (searchHistory.length === 0) {
        container.innerHTML = '<div class="search-history-empty">暂无搜索历史</div>';
        return;
    }

    container.innerHTML = searchHistory.map(term => `
        <div class="search-history-item" onclick="useSearchHistory('${escapeHtml(term)}')">
            <span class="history-icon">🕐</span>
            <span class="history-text">${escapeHtml(term)}</span>
        </div>
    `).join('');
}

function useSearchHistory(term) {
    const input = document.getElementById('searchInput');
    if (input) {
        input.value = term;
        hideSearchHistory();
        filterArticles();
    }
}

function showSearchHistory() {
    const dropdown = document.getElementById('searchHistoryDropdown');
    if (dropdown && searchHistory.length > 0) {
        renderSearchHistory();
        dropdown.classList.add('visible');
    }
}

function hideSearchHistory() {
    const dropdown = document.getElementById('searchHistoryDropdown');
    if (dropdown) {
        dropdown.classList.remove('visible');
    }
}

// ========================================
// 数据加载
// ========================================

async function loadArticles() {
    try {
        const response = await fetch('data/index.json');
        const data = await response.json();

        allArticles = data.articles || [];

        // 合并本地状态
        allArticles.forEach(article => {
            article.is_favorite = favorites.has(article.id);
            article.is_read = readArticles.has(article.id);
            article.is_read_later = readLater.has(article.id);
            article.is_ai_related = isAIRelated(article);
        });

        // 填充期刊下拉列表
        populateJournalList();

        updateStats(data);
        updateReadLaterCount();
        filterArticles();
    } catch (error) {
        console.error('加载数据失败:', error);
        document.getElementById('articleList').innerHTML = `
            <div class="no-results">
                <h3>暂无数据</h3>
                <p>请先运行抓取脚本获取文献</p>
            </div>
        `;
    }
}

// ========================================
// AI分类
// ========================================

function isAIRelated(article) {
    const text = [
        article.title || '',
        article.title_zh || '',
        article.abstract || '',
        article.abstract_zh || ''
    ].join(' ').toLowerCase();

    return AI_KEYWORDS.some(keyword => text.includes(keyword));
}

function filterByCategory(articles, category) {
    if (category === 'all') return articles;
    if (category === 'ai-related') return articles.filter(a => a.is_ai_related);
    if (category === 'ai-unrelated') return articles.filter(a => !a.is_ai_related);
    return articles;
}

function filterByReadStatus(articles, filter) {
    if (filter === 'all') return articles;
    if (filter === 'unread') return articles.filter(a => !a.is_read);
    if (filter === 'read') return articles.filter(a => a.is_read);
    if (filter === 'later') return articles.filter(a => a.is_read_later);
    return articles;
}

function setCategory(category) {
    currentCategory = category;

    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });

    filterArticles();
}

// ========================================
// 期刊筛选
// ========================================

function matchesJournalGroup(journal, groupKey) {
    if (!journal || !JOURNAL_GROUPS[groupKey]) return false;

    const journalLower = journal.toLowerCase();
    const patterns = JOURNAL_GROUPS[groupKey].patterns;

    return patterns.some(pattern => journalLower.includes(pattern));
}

function isInAnyGroup(journal) {
    if (!journal) return false;

    for (const groupKey of Object.keys(JOURNAL_GROUPS)) {
        if (matchesJournalGroup(journal, groupKey)) {
            return true;
        }
    }
    return false;
}

function filterByJournal(articles, filterValue) {
    if (filterValue === 'all') return articles;

    if (filterValue.startsWith('group:')) {
        const groupKey = filterValue.replace('group:', '');

        if (groupKey === 'other') {
            // "其他"分组：不属于任何已定义分组的期刊
            return articles.filter(a => !isInAnyGroup(a.journal));
        }

        return articles.filter(a => matchesJournalGroup(a.journal, groupKey));
    }

    // 单独期刊筛选
    return articles.filter(a => a.journal === filterValue);
}

function populateJournalList() {
    const journalSet = new Set();
    allArticles.forEach(article => {
        if (article.journal) {
            journalSet.add(article.journal);
        }
    });

    const journals = Array.from(journalSet).sort();
    const optgroup = document.getElementById('journalList');

    if (optgroup) {
        optgroup.innerHTML = journals.map(journal =>
            `<option value="${escapeHtml(journal)}">${escapeHtml(journal)}</option>`
        ).join('');
    }
}

// ========================================
// 关键词高亮
// ========================================

function highlightKeywords(text) {
    if (!text) return '';

    const escaped = escapeHtml(text);
    const pattern = new RegExp(`(${AI_KEYWORDS.join('|')})`, 'gi');
    return escaped.replace(pattern, '<span class="keyword-highlight">$1</span>');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========================================
// 统计信息
// ========================================

function updateStats(data) {
    document.getElementById('totalCount').textContent = data.total || 0;
    updateFavCount();
    updateUnreadCount();

    const aiCount = allArticles.filter(a => a.is_ai_related).length;
    const nonAiCount = allArticles.length - aiCount;

    const aiCountEl = document.getElementById('aiCount');
    const nonAiCountEl = document.getElementById('nonAiCount');
    if (aiCountEl) aiCountEl.textContent = aiCount;
    if (nonAiCountEl) nonAiCountEl.textContent = nonAiCount;

    if (data.last_update) {
        const date = new Date(data.last_update);
        document.getElementById('lastUpdate').textContent = date.toLocaleString('zh-CN');
    }
}

// ========================================
// 搜索和筛选
// ========================================

function setupSearch() {
    const input = document.getElementById('searchInput');
    if (!input) return;

    let timeout;
    input.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(filterArticles, 300);
    });

    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const term = input.value.trim();
            if (term) {
                addToSearchHistory(term);
            }
            hideSearchHistory();
            filterArticles();
        }
    });

    input.addEventListener('focus', () => {
        showSearchHistory();
    });

    // 点击外部关闭下拉
    document.addEventListener('click', (e) => {
        const searchBox = document.querySelector('.search-box');
        if (searchBox && !searchBox.contains(e.target)) {
            hideSearchHistory();
        }
    });
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    hideSearchHistory();
    filterArticles();
}

function filterArticles() {
    const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
    const favoritesOnly = document.getElementById('favoritesOnly')?.checked || false;
    const dateFrom = document.getElementById('dateFrom')?.value || '';
    const dateTo = document.getElementById('dateTo')?.value || '';
    const journalFilter = document.getElementById('journalFilter')?.value || 'all';

    filteredArticles = allArticles.filter(article => {
        if (favoritesOnly && !article.is_favorite) {
            return false;
        }

        // 日期范围筛选
        if (dateFrom || dateTo) {
            const articleDate = article.pub_date || '';
            if (articleDate) {
                if (dateFrom && articleDate < dateFrom) {
                    return false;
                }
                if (dateTo && articleDate > dateTo) {
                    return false;
                }
            } else {
                // 没有日期的文献，如果设置了日期筛选则排除
                if (dateFrom || dateTo) {
                    return false;
                }
            }
        }

        if (searchTerm) {
            const searchText = [
                article.title,
                article.title_zh,
                article.abstract,
                article.abstract_zh,
                article.journal,
                ...(article.authors || [])
            ].join(' ').toLowerCase();

            if (!searchText.includes(searchTerm)) {
                return false;
            }
        }

        return true;
    });

    // 应用分类筛选
    filteredArticles = filterByCategory(filteredArticles, currentCategory);

    // 应用阅读状态筛选
    filteredArticles = filterByReadStatus(filteredArticles, currentReadFilter);

    // 应用期刊筛选
    filteredArticles = filterByJournal(filteredArticles, journalFilter);

    currentPage = 1;
    focusedIndex = -1;
    sortArticles();
}

function clearDateFilter() {
    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');
    if (dateFrom) dateFrom.value = '';
    if (dateTo) dateTo.value = '';
    filterArticles();
}

function sortArticles() {
    const sortBy = document.getElementById('sortSelect')?.value || 'date-desc';

    filteredArticles.sort((a, b) => {
        switch (sortBy) {
            case 'date-desc':
                return (b.pub_date || '').localeCompare(a.pub_date || '');
            case 'date-asc':
                return (a.pub_date || '').localeCompare(b.pub_date || '');
            default:
                return 0;
        }
    });

    updateFilteredCount();
    renderArticles();
}

function updateFilteredCount() {
    const el = document.getElementById('filteredCount');
    if (el) {
        el.textContent = filteredArticles.length;
    }
}

// ========================================
// 分页
// ========================================

function getCurrentPageArticles() {
    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    return filteredArticles.slice(start, end);
}

function getTotalPages() {
    return Math.ceil(filteredArticles.length / PAGE_SIZE);
}

function goToPage(page) {
    const totalPages = getTotalPages();
    if (page < 1 || page > totalPages) return;

    currentPage = page;
    focusedIndex = -1;
    renderArticles();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ========================================
// 卡片展开/折叠
// ========================================

function toggleCardExpansion(id) {
    if (expandedCards.has(id)) {
        expandedCards.delete(id);
    } else {
        expandedCards.add(id);
        // 展开时自动标记为已读
        if (!readArticles.has(id)) {
            readArticles.add(id);
            saveReadStatus();

            const article = allArticles.find(a => a.id === id);
            if (article) {
                article.is_read = true;
            }

            updateUnreadCount();
            updateCardReadUI(id);
        }
    }

    const card = document.getElementById(`article-${id}`);
    if (card) {
        card.classList.toggle('expanded', expandedCards.has(id));
    }
}

// ========================================
// 渲染文献列表
// ========================================

function renderArticles() {
    const container = document.getElementById('articleList');
    if (!container) return;

    if (filteredArticles.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <h3>没有找到文献</h3>
                <p>尝试调整搜索条件或分类筛选</p>
            </div>
        `;
        renderPagination();
        return;
    }

    const pageArticles = getCurrentPageArticles();
    container.innerHTML = pageArticles.map((article, index) =>
        createArticleCard(article, index)
    ).join('');

    renderPagination();
}

function createArticleCard(article, index) {
    const isExpanded = expandedCards.has(article.id);
    const isFav = article.is_favorite;
    const isRead = article.is_read;
    const isLater = article.is_read_later;
    const isFocused = index === focusedIndex;
    const isAI = article.is_ai_related;

    const authors = (article.authors || []).slice(0, 3).join(', ');
    const authorsMore = article.authors && article.authors.length > 3 ? ' et al.' : '';

    const titleZhHighlighted = highlightKeywords(article.title_zh || article.title);
    const titleEnHighlighted = highlightKeywords(article.title);
    const abstractZhHighlighted = highlightKeywords(article.abstract_zh);

    return `
        <div class="article-card ${isExpanded ? 'expanded' : ''} ${isFav ? 'favorite' : ''} ${isRead ? 'read' : ''} ${isLater ? 'read-later' : ''} ${isFocused ? 'focused' : ''}" 
             id="article-${article.id}"
             data-index="${index}"
             data-id="${article.id}">
            
            <div class="card-header" 
                 onclick="toggleCardExpansion('${article.id}')"
                 onmouseenter="showPreview(event, '${article.id}')"
                 onmouseleave="hidePreview()">
                <div class="card-main">
                    <div class="card-title-zh">
                        <a href="${article.link}" target="_blank" rel="noopener" onclick="event.stopPropagation();">${titleZhHighlighted}</a>
                    </div>
                    <div class="card-meta">
                        <span>� $${escapeHtml(article.journal || '未知期刊')}</span>
                        <span>📅 ${article.pub_date || '未知日期'}</span>
                        <span class="ai-tag ${isAI ? 'ai-related' : 'ai-unrelated'}">
                            ${isAI ? '🤖 AI' : '📚 非AI'}
                        </span>
                    </div>
                </div>
                <div class="card-actions">
                    <button class="read-btn ${isRead ? 'is-read' : ''}" 
                            onclick="event.stopPropagation(); toggleReadStatus('${article.id}')" 
                            title="${isRead ? '标记为未读' : '标记为已读'}">
                        ${isRead ? '✓ 已读' : '○ 未读'}
                    </button>
                    <button class="read-later-btn ${isLater ? 'is-later' : ''}" 
                            onclick="event.stopPropagation(); toggleReadLater('${article.id}')" 
                            title="${isLater ? '从待读列表移除' : '添加到待读列表'}">
                        ${isLater ? '📌' : '📍'}
                    </button>
                    <button class="favorite-btn" 
                            onclick="event.stopPropagation(); toggleFavorite('${article.id}')" 
                            title="${isFav ? '取消收藏' : '添加收藏'}">
                        ${isFav ? '⭐' : '☆'}
                    </button>
                    <span class="expand-icon">▼</span>
                </div>
            </div>
            
            <div class="card-details">
                <div class="card-details-inner">
                    <div class="card-title-en">
                        <a href="${article.link}" target="_blank" rel="noopener">
                            ${titleEnHighlighted}
                        </a>
                    </div>
                    <div class="card-authors">
                        👤 ${escapeHtml(authors + authorsMore) || '未知作者'}
                    </div>
                    ${article.abstract_zh ? `
                        <div class="card-abstract">
                            ${abstractZhHighlighted}
                        </div>
                    ` : ''}
                    <div class="card-export">
                        <button class="export-btn" onclick="event.stopPropagation(); exportBibTeX('${article.id}')" title="导出BibTeX">
                            📄 BibTeX
                        </button>
                        <button class="export-btn" onclick="event.stopPropagation(); exportRIS('${article.id}')" title="导出RIS">
                            📋 RIS
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ========================================
// 分页渲染
// ========================================

function renderPagination() {
    const totalPages = getTotalPages();
    const paginationContainer = document.getElementById('pagination');

    if (!paginationContainer) return;

    if (totalPages <= 1) {
        paginationContainer.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';
    html += `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>`;

    const maxVisible = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }

    if (startPage > 1) {
        html += `<button class="page-btn" onclick="goToPage(1)">1</button>`;
        if (startPage > 2) html += '<span class="page-ellipsis">...</span>';
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    if (endPage < totalPages) {
        if (endPage < totalPages - 1) html += '<span class="page-ellipsis">...</span>';
        html += `<button class="page-btn" onclick="goToPage(${totalPages})">${totalPages}</button>`;
    }

    html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>`;
    html += `<span class="page-info">第 ${currentPage}/${totalPages} 页，共 ${filteredArticles.length} 篇</span>`;
    html += '</div>';
    paginationContainer.innerHTML = html;
}

// ========================================
// 键盘导航
// ========================================

function setupKeyboardNavigation() {
    document.addEventListener('keydown', handleKeyPress);
}

function handleKeyPress(event) {
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    switch (event.key.toLowerCase()) {
        case 'j':
            event.preventDefault();
            focusNext();
            break;
        case 'k':
            event.preventDefault();
            focusPrev();
            break;
        case 'enter':
            if (focusedIndex >= 0) {
                event.preventDefault();
                toggleFocused();
            }
            break;
        case 'o':
            if (focusedIndex >= 0) {
                event.preventDefault();
                openFocused();
            }
            break;
        case 's':
            if (focusedIndex >= 0) {
                event.preventDefault();
                starFocused();
            }
            break;
        case 'r':
            if (focusedIndex >= 0) {
                event.preventDefault();
                markFocusedRead();
            }
            break;
        case 'l':
            if (focusedIndex >= 0) {
                event.preventDefault();
                markFocusedReadLater();
            }
            break;
    }
}

function focusNext() {
    const pageArticles = getCurrentPageArticles();
    if (pageArticles.length === 0) return;
    updateFocusedCard(false);
    focusedIndex = Math.min(focusedIndex + 1, pageArticles.length - 1);
    updateFocusedCard(true);
    scrollToFocused();
}

function focusPrev() {
    const pageArticles = getCurrentPageArticles();
    if (pageArticles.length === 0) return;
    updateFocusedCard(false);
    if (focusedIndex < 0) {
        focusedIndex = 0;
    } else {
        focusedIndex = Math.max(focusedIndex - 1, 0);
    }
    updateFocusedCard(true);
    scrollToFocused();
}

function updateFocusedCard(isFocused) {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    const card = document.getElementById(`article-${article.id}`);
    if (card) {
        card.classList.toggle('focused', isFocused);
    }
}

function scrollToFocused() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    const card = document.getElementById(`article-${article.id}`);
    if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function toggleFocused() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    toggleCardExpansion(article.id);
}

function openFocused() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    if (article.link) {
        window.open(article.link, '_blank');
    }
}

function starFocused() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    toggleFavorite(article.id);
}

function markFocusedRead() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    toggleReadStatus(article.id);
}

function markFocusedReadLater() {
    const pageArticles = getCurrentPageArticles();
    if (focusedIndex < 0 || focusedIndex >= pageArticles.length) return;
    const article = pageArticles[focusedIndex];
    toggleReadLater(article.id);
}

// ========================================
// 悬停预览
// ========================================

let tooltipElement = null;
let tooltipTimeout = null;

function createTooltip() {
    tooltipElement = document.createElement('div');
    tooltipElement.className = 'preview-tooltip';
    document.body.appendChild(tooltipElement);
}

function showPreview(event, articleId) {
    if (window.innerWidth < 768) return;
    if (expandedCards.has(articleId)) return;

    const article = allArticles.find(a => a.id === articleId);
    if (!article || !article.abstract_zh) return;

    clearTimeout(tooltipTimeout);

    tooltipTimeout = setTimeout(() => {
        const preview = article.abstract_zh.length > 200
            ? article.abstract_zh.substring(0, 200) + '...'
            : article.abstract_zh;

        tooltipElement.innerHTML = highlightKeywords(preview);
        tooltipElement.classList.add('visible');

        const rect = event.target.getBoundingClientRect();
        let left = rect.left;
        let top = rect.bottom + 10;

        const tooltipRect = tooltipElement.getBoundingClientRect();
        if (left + tooltipRect.width > window.innerWidth - 20) {
            left = window.innerWidth - tooltipRect.width - 20;
        }
        if (top + tooltipRect.height > window.innerHeight - 20) {
            top = rect.top - tooltipRect.height - 10;
        }

        tooltipElement.style.left = `${left}px`;
        tooltipElement.style.top = `${top}px`;
    }, 500);
}

function hidePreview() {
    clearTimeout(tooltipTimeout);
    if (tooltipElement) {
        tooltipElement.classList.remove('visible');
    }
}

// ========================================
// 导出功能 (BibTeX / RIS)
// ========================================

function exportBibTeX(articleId) {
    const article = allArticles.find(a => a.id === articleId);
    if (!article) return;

    const authors = (article.authors || []).join(' and ');
    const year = article.pub_date ? article.pub_date.substring(0, 4) : 'unknown';
    const key = `${(article.authors?.[0]?.split(' ').pop() || 'unknown').toLowerCase()}${year}`;

    const bibtex = `@article{${key},
  title = {${article.title}},
  author = {${authors || 'Unknown'}},
  journal = {${article.journal || 'Unknown'}},
  year = {${year}},
  url = {${article.link || ''}},
  abstract = {${(article.abstract || '').replace(/\n/g, ' ')}}
}`;

    downloadFile(bibtex, `${key}.bib`, 'text/plain');
    showToast('BibTeX 已导出');
}

function exportRIS(articleId) {
    const article = allArticles.find(a => a.id === articleId);
    if (!article) return;

    const year = article.pub_date ? article.pub_date.substring(0, 4) : '';
    const month = article.pub_date ? article.pub_date.substring(5, 7) : '';
    const day = article.pub_date ? article.pub_date.substring(8, 10) : '';

    let ris = `TY  - JOUR\n`;
    ris += `TI  - ${article.title}\n`;

    (article.authors || []).forEach(author => {
        ris += `AU  - ${author}\n`;
    });

    ris += `JO  - ${article.journal || ''}\n`;
    ris += `PY  - ${year}\n`;
    if (month) ris += `DA  - ${year}/${month}/${day || '01'}\n`;
    ris += `UR  - ${article.link || ''}\n`;
    ris += `AB  - ${(article.abstract || '').replace(/\n/g, ' ')}\n`;
    ris += `ER  - \n`;

    const filename = `${(article.authors?.[0]?.split(' ').pop() || 'article').toLowerCase()}_${year}.ris`;
    downloadFile(ris, filename, 'text/plain');
    showToast('RIS 已导出');
}

function exportAllBibTeX() {
    const articles = filteredArticles.length > 0 ? filteredArticles : allArticles;
    let bibtex = '';

    articles.forEach((article, index) => {
        const authors = (article.authors || []).join(' and ');
        const year = article.pub_date ? article.pub_date.substring(0, 4) : 'unknown';
        const key = `${(article.authors?.[0]?.split(' ').pop() || 'unknown').toLowerCase()}${year}_${index}`;

        bibtex += `@article{${key},
  title = {${article.title}},
  author = {${authors || 'Unknown'}},
  journal = {${article.journal || 'Unknown'}},
  year = {${year}},
  url = {${article.link || ''}},
  abstract = {${(article.abstract || '').replace(/\n/g, ' ')}}
}\n\n`;
    });

    downloadFile(bibtex, `literature_export_${new Date().toISOString().slice(0, 10)}.bib`, 'text/plain');
    showToast(`已导出 ${articles.length} 篇文献的 BibTeX`);
}

function exportAllRIS() {
    const articles = filteredArticles.length > 0 ? filteredArticles : allArticles;
    let ris = '';

    articles.forEach(article => {
        const year = article.pub_date ? article.pub_date.substring(0, 4) : '';
        const month = article.pub_date ? article.pub_date.substring(5, 7) : '';
        const day = article.pub_date ? article.pub_date.substring(8, 10) : '';

        ris += `TY  - JOUR\n`;
        ris += `TI  - ${article.title}\n`;

        (article.authors || []).forEach(author => {
            ris += `AU  - ${author}\n`;
        });

        ris += `JO  - ${article.journal || ''}\n`;
        ris += `PY  - ${year}\n`;
        if (month) ris += `DA  - ${year}/${month}/${day || '01'}\n`;
        ris += `UR  - ${article.link || ''}\n`;
        ris += `AB  - ${(article.abstract || '').replace(/\n/g, ' ')}\n`;
        ris += `ER  - \n\n`;
    });

    downloadFile(ris, `literature_export_${new Date().toISOString().slice(0, 10)}.ris`, 'text/plain');
    showToast(`已导出 ${articles.length} 篇文献的 RIS`);
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('visible'), 10);
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => document.body.removeChild(toast), 300);
    }, 2000);
}
