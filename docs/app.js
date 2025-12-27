/**
 * 文献追踪系统 - 前端应用
 * 支持：可折叠卡片、AI分类筛选、主题切换、键盘快捷键、关键词高亮
 */

// ========================================
// 全局状态
// ========================================

let allArticles = [];
let filteredArticles = [];
let favorites = new Set();
let expandedCards = new Set();
let currentPage = 1;
let focusedIndex = -1;
let currentCategory = 'all'; // 'all' | 'ai-related' | 'ai-unrelated'
let currentTheme = 'light';

const PAGE_SIZE = 50;
const AI_KEYWORDS = ['machine', 'learn', 'neural', 'network'];
const THEME_STORAGE_KEY = 'literature_theme';
const FAVORITES_STORAGE_KEY = 'literature_favorites';

// ========================================
// 初始化
// ========================================

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadFavorites();
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

    if (document.getElementById('favoritesOnly').checked) {
        filterArticles();
    } else {
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
}

function updateFavCount() {
    const el = document.getElementById('favCount');
    if (el) el.textContent = favorites.size;
}

// ========================================
// 数据加载
// ========================================

async function loadArticles() {
    try {
        const response = await fetch('data/index.json');
        const data = await response.json();

        allArticles = data.articles || [];

        // 合并本地收藏状态并计算AI分类
        allArticles.forEach(article => {
            article.is_favorite = favorites.has(article.id);
            article.is_ai_related = isAIRelated(article);
        });

        updateStats(data);
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

function setCategory(category) {
    currentCategory = category;

    // 更新按钮状态
    document.querySelectorAll('.category-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.category === category);
    });

    filterArticles();
}

// ========================================
// 关键词高亮
// ========================================

function highlightKeywords(text) {
    if (!text) return '';

    // 先转义HTML
    const escaped = escapeHtml(text);

    // 创建正则表达式匹配所有关键词（大小写不敏感）
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

    // 计算AI相关/无关数量
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
            filterArticles();
        }
    });
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    filterArticles();
}

function filterArticles() {
    const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
    const favoritesOnly = document.getElementById('favoritesOnly')?.checked || false;

    filteredArticles = allArticles.filter(article => {
        // 收藏筛选
        if (favoritesOnly && !article.is_favorite) {
            return false;
        }

        // 搜索筛选
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

    currentPage = 1;
    focusedIndex = -1;
    sortArticles();
}

function sortArticles() {
    const sortBy = document.getElementById('sortSelect')?.value || 'date-desc';

    filteredArticles.sort((a, b) => {
        switch (sortBy) {
            case 'date-desc':
                return (b.pub_date || '').localeCompare(a.pub_date || '');
            case 'date-asc':
                return (a.pub_date || '').localeCompare(b.pub_date || '');
            case 'journal':
                return (a.journal || '').localeCompare(b.journal || '');
            default:
                return 0;
        }
    });

    renderArticles();
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
    updateFilteredStats();
}

function updateFilteredStats() {
    // 更新当前筛选结果的统计
    const filteredCount = document.getElementById('filteredCount');
    if (filteredCount) {
        filteredCount.textContent = filteredArticles.length;
    }
}

function createArticleCard(article, index) {
    const isExpanded = expandedCards.has(article.id);
    const isFav = article.is_favorite;
    const isFocused = index === focusedIndex;
    const isAI = article.is_ai_related;

    const authors = (article.authors || []).slice(0, 3).join(', ');
    const authorsMore = article.authors && article.authors.length > 3 ? ' et al.' : '';

    // 高亮标题和摘要中的关键词
    const titleZhHighlighted = highlightKeywords(article.title_zh || article.title);
    const titleEnHighlighted = highlightKeywords(article.title);
    const abstractZhHighlighted = highlightKeywords(article.abstract_zh);

    return `
        <div class="article-card ${isExpanded ? 'expanded' : ''} ${isFav ? 'favorite' : ''} ${isFocused ? 'focused' : ''}" 
             id="article-${article.id}"
             data-index="${index}"
             data-id="${article.id}">
            
            <div class="card-header" 
                 onclick="toggleCardExpansion('${article.id}')"
                 onmouseenter="showPreview(event, '${article.id}')"
                 onmouseleave="hidePreview()">
                <div class="card-main">
                    <div class="card-title-zh">${titleZhHighlighted}</div>
                    <div class="card-meta">
                        <span>📖 ${escapeHtml(article.journal || '未知期刊')}</span>
                        <span>📅 ${article.pub_date || '未知日期'}</span>
                        <span class="ai-tag ${isAI ? 'ai-related' : 'ai-unrelated'}">
                            ${isAI ? '🤖 AI' : '📚 非AI'}
                        </span>
                    </div>
                </div>
                <div class="card-actions">
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

    // 上一页
    html += `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>上一页</button>`;

    // 页码
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

    // 下一页
    html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>下一页</button>`;

    // 页码信息
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
    // 如果在输入框中，不处理快捷键
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
    }
}

function focusNext() {
    const pageArticles = getCurrentPageArticles();
    if (pageArticles.length === 0) return;

    // 移除当前焦点
    updateFocusedCard(false);

    // 移动到下一个
    focusedIndex = Math.min(focusedIndex + 1, pageArticles.length - 1);

    // 添加新焦点
    updateFocusedCard(true);
    scrollToFocused();
}

function focusPrev() {
    const pageArticles = getCurrentPageArticles();
    if (pageArticles.length === 0) return;

    // 移除当前焦点
    updateFocusedCard(false);

    // 移动到上一个
    if (focusedIndex < 0) {
        focusedIndex = 0;
    } else {
        focusedIndex = Math.max(focusedIndex - 1, 0);
    }

    // 添加新焦点
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
    // 移动端不显示tooltip
    if (window.innerWidth < 768) return;

    // 如果卡片已展开，不显示tooltip
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

        // 定位tooltip
        const rect = event.target.getBoundingClientRect();
        const tooltipRect = tooltipElement.getBoundingClientRect();

        let left = rect.left;
        let top = rect.bottom + 10;

        // 确保不超出屏幕
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
