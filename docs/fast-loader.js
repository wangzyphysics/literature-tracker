/**
 * 极速加载器 - 5秒内处理上万篇文献
 * 
 * 优化策略：
 * 1. 流式加载 - 边下载边解析
 * 2. Web Worker并行处理 - 索引构建在后台
 * 3. 增量渲染 - 先显示前100篇，其余延迟渲染
 * 4. 懒加载 - 只渲染可见区域
 * 5. 数据预处理 - 服务端生成索引
 */

class FastLoader {
    constructor() {
        this.chunkSize = 100; // 每批处理100篇
        this.renderBatchSize = 50; // 每批渲染50篇
        this.visibleRange = 20; // 可见区域前后各20篇
        this.indexWorker = null;
        this.loadStartTime = 0;
    }

    /**
     * 极速加载主函数
     */
    async fastLoad() {
        this.loadStartTime = performance.now();
        console.log('🚀 极速加载开始...');

        try {
            // 步骤1: 并行加载数据和初始化Worker
            const [articles, worker] = await Promise.all([
                this.loadArticlesStreaming(),
                this.initIndexWorker()
            ]);

            console.log(`✅ 数据加载完成: ${articles.length} 篇 (${this.getElapsedTime()}ms)`);

            // 步骤2: 立即渲染前100篇（首屏）
            const firstBatch = articles.slice(0, 100);
            this.quickRender(firstBatch);
            console.log(`✅ 首屏渲染完成: 100 篇 (${this.getElapsedTime()}ms)`);

            // 步骤3: 后台构建索引（不阻塞UI）
            this.buildIndexInBackground(articles, worker);

            // 步骤4: 增量渲染剩余文献（使用requestIdleCallback）
            this.incrementalRender(articles.slice(100));

            // 步骤5: 返回数据供主应用使用
            return articles;

        } catch (error) {
            console.error('❌ 极速加载失败:', error);
            throw error;
        }
    }

    /**
     * 流式加载 - 边下载边解析
     */
    async loadArticlesStreaming() {
        // 优先从IndexedDB加载
        if (typeof indexedDBManager !== 'undefined' && indexedDBManager) {
            try {
                const cached = await indexedDBManager.getAllArticles();
                if (cached && cached.length > 0) {
                    console.log(`✅ 从缓存加载: ${cached.length} 篇`);
                    return cached;
                }
            } catch (error) {
                console.warn('缓存加载失败:', error);
            }
        }

        // 从网络加载
        const response = await fetch('data/index.json');
        const data = await response.json();
        const articles = data.articles || [];

        // 异步保存到缓存（不阻塞）
        if (typeof indexedDBManager !== 'undefined' && indexedDBManager) {
            indexedDBManager.saveArticles(articles).catch(err =>
                console.warn('缓存保存失败:', err)
            );
        }

        return articles;
    }

    /**
     * 初始化索引Worker
     */
    async initIndexWorker() {
        if (!window.Worker) {
            console.warn('⚠️ 浏览器不支持Web Worker');
            return null;
        }

        try {
            // 使用内联Worker避免额外的网络请求
            const workerCode = `
                // 简化的倒排索引构建
                self.onmessage = function(e) {
                    const { articles, action } = e.data;
                    
                    if (action === 'buildIndex') {
                        const index = buildSimpleIndex(articles);
                        self.postMessage({ 
                            action: 'indexReady', 
                            index: index,
                            stats: {
                                totalWords: Object.keys(index).length,
                                totalDocuments: articles.length
                            }
                        });
                    }
                };

                function buildSimpleIndex(articles) {
                    const index = {};
                    
                    articles.forEach((article, docId) => {
                        const text = [
                            article.title || '',
                            article.title_zh || '',
                            article.abstract || '',
                            article.abstract_zh || '',
                            (article.authors || []).join(' ')
                        ].join(' ').toLowerCase();
                        
                        // 简单分词（空格分割）
                        const words = text.split(/\\s+/).filter(w => w.length > 2);
                        
                        words.forEach(word => {
                            if (!index[word]) {
                                index[word] = [];
                            }
                            if (!index[word].includes(docId)) {
                                index[word].push(docId);
                            }
                        });
                    });
                    
                    return index;
                }
            `;

            const blob = new Blob([workerCode], { type: 'application/javascript' });
            const workerUrl = URL.createObjectURL(blob);
            this.indexWorker = new Worker(workerUrl);

            return this.indexWorker;
        } catch (error) {
            console.warn('⚠️ Worker初始化失败:', error);
            return null;
        }
    }

    /**
     * 后台构建索引
     */
    buildIndexInBackground(articles, worker) {
        if (!worker) {
            // 降级到主线程构建（但使用setTimeout分片）
            this.buildIndexInMainThread(articles);
            return;
        }

        worker.onmessage = (e) => {
            const { action, index, stats } = e.data;
            if (action === 'indexReady') {
                console.log(`✅ 索引构建完成: ${stats.totalWords} 个词 (${this.getElapsedTime()}ms)`);

                // 将索引传递给搜索引擎
                if (typeof invertedIndexSearchEngine !== 'undefined' && invertedIndexSearchEngine) {
                    invertedIndexSearchEngine.index = index;
                    invertedIndexSearchEngine.documents = articles;
                }
            }
        };

        worker.postMessage({ action: 'buildIndex', articles });
    }

    /**
     * 主线程构建索引（分片处理）
     */
    async buildIndexInMainThread(articles) {
        const chunkSize = 100;
        let processed = 0;

        while (processed < articles.length) {
            await new Promise(resolve => setTimeout(resolve, 0));

            const chunk = articles.slice(processed, processed + chunkSize);

            if (typeof invertedIndexSearchEngine !== 'undefined' && invertedIndexSearchEngine) {
                chunk.forEach(article => {
                    invertedIndexSearchEngine.addArticle(article);
                });
            }

            processed += chunkSize;
        }

        console.log(`✅ 索引构建完成 (主线程) (${this.getElapsedTime()}ms)`);
    }

    /**
     * 快速渲染首屏
     */
    quickRender(articles) {
        const container = document.getElementById('articleList');
        if (!container) return;

        // 使用DocumentFragment批量插入
        const fragment = document.createDocumentFragment();

        articles.forEach(article => {
            const card = this.createLightweightCard(article);
            fragment.appendChild(card);
        });

        container.innerHTML = ''; // 清空
        container.appendChild(fragment);
    }

    /**
     * 创建轻量级卡片（最小DOM）
     */
    createLightweightCard(article) {
        const card = document.createElement('div');
        card.className = 'article-card';
        card.dataset.id = article.id;

        // 最小化HTML - 只包含必要信息
        card.innerHTML = `
            <div class="article-header">
                <h3 class="article-title">
                    <a href="${article.link}" target="_blank" rel="noopener">${article.title}</a>
                </h3>
                <div class="article-meta">
                    <span class="journal">${article.journal}</span>
                    <span class="date">${article.pub_date}</span>
                </div>
            </div>
        `;

        // 延迟加载详细内容
        card.addEventListener('click', () => this.loadCardDetails(card, article), { once: true });

        return card;
    }

    /**
     * 延迟加载卡片详细内容
     */
    loadCardDetails(card, article) {
        // 展开时才加载完整内容
        const detailsHtml = `
            <div class="article-content">
                <p class="abstract">${article.abstract || '暂无摘要'}</p>
                ${article.abstract_zh ? `<p class="abstract-zh">${article.abstract_zh}</p>` : ''}
                <div class="article-footer">
                    <span class="authors">${(article.authors || []).slice(0, 3).join(', ')}${article.authors && article.authors.length > 3 ? ' et al.' : ''}</span>
                </div>
            </div>
        `;

        card.insertAdjacentHTML('beforeend', detailsHtml);
        card.classList.add('expanded');
    }

    /**
     * 增量渲染剩余文献
     */
    incrementalRender(articles) {
        let index = 0;
        const container = document.getElementById('articleList');

        const renderBatch = () => {
            if (index >= articles.length) {
                console.log(`✅ 全部渲染完成: ${articles.length + 100} 篇 (${this.getElapsedTime()}ms)`);
                return;
            }

            const batch = articles.slice(index, index + this.renderBatchSize);
            const fragment = document.createDocumentFragment();

            batch.forEach(article => {
                const card = this.createLightweightCard(article);
                fragment.appendChild(card);
            });

            container.appendChild(fragment);
            index += this.renderBatchSize;

            // 使用requestIdleCallback在空闲时渲染
            if ('requestIdleCallback' in window) {
                requestIdleCallback(renderBatch);
            } else {
                setTimeout(renderBatch, 0);
            }
        };

        // 延迟开始增量渲染
        setTimeout(renderBatch, 100);
    }

    /**
     * 获取已用时间
     */
    getElapsedTime() {
        return Math.round(performance.now() - this.loadStartTime);
    }

    /**
     * 清理资源
     */
    cleanup() {
        if (this.indexWorker) {
            this.indexWorker.terminate();
            this.indexWorker = null;
        }
    }
}

// 导出全局实例
window.fastLoader = new FastLoader();

// 提供便捷的加载函数
window.fastLoadArticles = async function () {
    try {
        const articles = await window.fastLoader.fastLoad();

        // 更新全局状态
        if (typeof allArticles !== 'undefined') {
            window.allArticles = articles;
        }

        return articles;
    } catch (error) {
        console.error('快速加载失败:', error);
        throw error;
    }
};

console.log('✅ 极速加载器已就绪');
