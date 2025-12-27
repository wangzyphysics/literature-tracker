/**
 * 性能优化模块 - 处理10,000+篇文献的深度优化
 * 包含: 分块加载、IndexedDB缓存、倒排索引搜索、Worker池、对象池、性能监控
 */

// ========================================
// 数据分块加载器
// ========================================

class ChunkLoader {
    constructor(chunkSize = 1000) {
        this.chunkSize = chunkSize;
        this.chunks = [];
        this.loadedChunks = new Set();
        this.loading = false;
        this.retryCount = 3;
        this.retryDelay = 1000;
    }

    async loadChunk(chunkIndex) {
        if (this.loadedChunks.has(chunkIndex)) {
            return this.chunks[chunkIndex];
        }

        let retries = 0;
        while (retries < this.retryCount) {
            try {
                const response = await fetch(`data/chunk_${chunkIndex}.json`);
                if (!response.ok) throw new Error(`HTTP ${response.status}`);

                const data = await response.json();
                this.chunks[chunkIndex] = data.articles || [];
                this.loadedChunks.add(chunkIndex);

                return this.chunks[chunkIndex];
            } catch (error) {
                retries++;
                console.warn(`加载块 ${chunkIndex} 失败 (尝试 ${retries}/${this.retryCount}):`, error);

                if (retries < this.retryCount) {
                    await this.delay(this.retryDelay * retries);
                } else {
                    throw error;
                }
            }
        }
    }

    async loadAll(progressCallback) {
        this.loading = true;

        try {
            // 首先加载主索引文件获取总块数
            const response = await fetch('data/index.json');
            const index = await response.json();

            const articles = index.articles || [];
            const totalChunks = Math.ceil(articles.length / this.chunkSize);

            // 如果数据量小,直接返回
            if (articles.length <= this.chunkSize) {
                if (progressCallback) progressCallback(100, 1, 1);
                return articles;
            }

            // 分块加载
            const allArticles = [];
            for (let i = 0; i < totalChunks; i++) {
                const start = i * this.chunkSize;
                const end = Math.min(start + this.chunkSize, articles.length);
                const chunk = articles.slice(start, end);

                allArticles.push(...chunk);

                if (progressCallback) {
                    const progress = Math.round(((i + 1) / totalChunks) * 100);
                    progressCallback(progress, i + 1, totalChunks);
                }

                // 预加载下一块
                if (i < totalChunks - 1) {
                    this.preloadNextChunk(i + 1);
                }
            }

            return allArticles;
        } finally {
            this.loading = false;
        }
    }

    preloadNextChunk(chunkIndex) {
        // 在后台预加载,不阻塞主流程
        setTimeout(() => {
            this.loadChunk(chunkIndex).catch(err => {
                console.warn(`预加载块 ${chunkIndex} 失败:`, err);
            });
        }, 100);
    }

    getChunkCount() {
        return this.chunks.length;
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    clear() {
        this.chunks = [];
        this.loadedChunks.clear();
    }
}

// ========================================
// IndexedDB 缓存管理器
// ========================================

class IndexedDBManager {
    constructor(dbName = 'LiteratureDB', version = 1) {
        this.dbName = dbName;
        this.version = version;
        this.db = null;
        this.storeName = 'articles';
        this.metaStoreName = 'metadata';
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // 创建文章存储
                if (!db.objectStoreNames.contains(this.storeName)) {
                    const store = db.createObjectStore(this.storeName, { keyPath: 'id' });
                    store.createIndex('pub_date', 'pub_date', { unique: false });
                    store.createIndex('journal', 'journal', { unique: false });
                    store.createIndex('is_ai_related', 'is_ai_related', { unique: false });
                }

                // 创建元数据存储
                if (!db.objectStoreNames.contains(this.metaStoreName)) {
                    db.createObjectStore(this.metaStoreName, { keyPath: 'key' });
                }
            };
        });
    }

    async saveArticles(articles) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);

            let completed = 0;
            const total = articles.length;

            articles.forEach(article => {
                const request = store.put(article);
                request.onsuccess = () => {
                    completed++;
                    if (completed === total) {
                        this.setLastUpdate(new Date());
                        resolve();
                    }
                };
                request.onerror = () => reject(request.error);
            });
        });
    }

    async getArticles(ids) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const results = [];

            ids.forEach(id => {
                const request = store.get(id);
                request.onsuccess = () => {
                    if (request.result) {
                        results.push(request.result);
                    }
                };
            });

            transaction.oncomplete = () => resolve(results);
            transaction.onerror = () => reject(transaction.error);
        });
    }

    async getAllArticles() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.getAll();

            request.onsuccess = () => resolve(request.result || []);
            request.onerror = () => reject(request.error);
        });
    }

    async updateArticle(id, data) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.get(id);

            request.onsuccess = () => {
                const article = request.result;
                if (article) {
                    Object.assign(article, data);
                    const updateRequest = store.put(article);
                    updateRequest.onsuccess = () => resolve();
                    updateRequest.onerror = () => reject(updateRequest.error);
                } else {
                    reject(new Error(`Article ${id} not found`));
                }
            };

            request.onerror = () => reject(request.error);
        });
    }

    async deleteArticle(id) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.delete(id);

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async clear() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.clear();

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async getLastUpdate() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.metaStoreName], 'readonly');
            const store = transaction.objectStore(this.metaStoreName);
            const request = store.get('lastUpdate');

            request.onsuccess = () => {
                const result = request.result;
                resolve(result ? new Date(result.value) : null);
            };
            request.onerror = () => reject(request.error);
        });
    }

    async setLastUpdate(date) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction([this.metaStoreName], 'readwrite');
            const store = transaction.objectStore(this.metaStoreName);
            const request = store.put({ key: 'lastUpdate', value: date.toISOString() });

            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async getStorageSize() {
        if (!navigator.storage || !navigator.storage.estimate) {
            return { usage: 0, quota: 0 };
        }

        const estimate = await navigator.storage.estimate();
        return {
            usage: estimate.usage || 0,
            quota: estimate.quota || 0,
            usagePercent: estimate.quota ? (estimate.usage / estimate.quota * 100).toFixed(2) : 0
        };
    }
}


// ========================================
// 倒排索引搜索引擎
// ========================================

class InvertedIndexSearchEngine {
    constructor() {
        this.index = new Map(); // 词 -> 文章ID列表
        this.documents = new Map(); // 文章ID -> 文章
        this.stopWords = new Set([
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        ]);
        this.buildTime = 0;
    }

    buildIndex(articles) {
        const startTime = performance.now();

        this.index.clear();
        this.documents.clear();

        articles.forEach(article => {
            this.addArticle(article);
        });

        this.buildTime = performance.now() - startTime;
        console.log(`✅ 索引构建完成: ${articles.length} 篇文献, 耗时 ${this.buildTime.toFixed(2)}ms`);
    }

    addArticle(article) {
        this.documents.set(article.id, article);

        const text = [
            article.title || '',
            article.title_zh || '',
            article.abstract || '',
            article.abstract_zh || '',
            (article.authors || []).join(' '),
            article.journal || ''
        ].join(' ').toLowerCase();

        const words = this.tokenize(text);

        words.forEach(word => {
            if (!this.index.has(word)) {
                this.index.set(word, new Set());
            }
            this.index.get(word).add(article.id);
        });
    }

    removeArticle(id) {
        this.documents.delete(id);

        // 从索引中移除
        for (const [word, ids] of this.index.entries()) {
            ids.delete(id);
            if (ids.size === 0) {
                this.index.delete(word);
            }
        }
    }

    tokenize(text) {
        // 分词: 提取4个字符以上的单词
        const words = text.match(/\b[a-z]{4,}\b/g) || [];

        // 过滤停用词
        return words.filter(word => !this.stopWords.has(word));
    }

    search(query, options = {}) {
        const startTime = performance.now();

        if (!query || query.trim().length === 0) {
            return [];
        }

        const words = this.tokenize(query.toLowerCase());
        if (words.length === 0) {
            return [];
        }

        // 获取包含任意关键词的文章ID
        const matchedIds = new Set();
        const wordScores = new Map(); // 文章ID -> 分数

        words.forEach(word => {
            const ids = this.index.get(word);
            if (ids) {
                ids.forEach(id => {
                    matchedIds.add(id);
                    wordScores.set(id, (wordScores.get(id) || 0) + 1);
                });
            }
        });

        // 转换为文章对象并计算TF-IDF分数
        const results = Array.from(matchedIds).map(id => {
            const article = this.documents.get(id);
            const score = this.calculateScore(article, words, wordScores.get(id));

            return {
                article,
                score,
                matchedWords: wordScores.get(id)
            };
        });

        // 按分数排序
        results.sort((a, b) => b.score - a.score);

        const searchTime = performance.now() - startTime;
        console.log(`🔍 搜索完成: 找到 ${results.length} 个结果, 耗时 ${searchTime.toFixed(2)}ms`);

        return results.map(r => r.article);
    }

    calculateScore(article, queryWords, matchCount) {
        if (!article) return 0;

        // 简化的TF-IDF评分
        let score = matchCount * 10; // 基础分数

        // 标题匹配加权
        const titleText = (article.title + ' ' + (article.title_zh || '')).toLowerCase();
        queryWords.forEach(word => {
            if (titleText.includes(word)) {
                score += 20;
            }
        });

        // 摘要匹配加权
        const abstractText = (article.abstract + ' ' + (article.abstract_zh || '')).toLowerCase();
        queryWords.forEach(word => {
            if (abstractText.includes(word)) {
                score += 5;
            }
        });

        // 日期新鲜度加权
        if (article.pub_date) {
            const date = new Date(article.pub_date);
            const now = new Date();
            const daysDiff = (now - date) / (1000 * 60 * 60 * 24);
            score += Math.max(0, 10 - daysDiff / 30); // 越新分数越高
        }

        return score;
    }

    getIndexStats() {
        return {
            totalWords: this.index.size,
            totalDocuments: this.documents.size,
            buildTime: this.buildTime,
            avgWordsPerDoc: this.documents.size > 0 ? this.index.size / this.documents.size : 0,
            memoryUsage: this.estimateMemoryUsage()
        };
    }

    estimateMemoryUsage() {
        // 粗略估计内存使用(字节)
        let size = 0;

        // 索引大小
        for (const [word, ids] of this.index.entries()) {
            size += word.length * 2; // 字符串
            size += ids.size * 8; // Set中的ID
        }

        // 文档大小
        for (const [id, doc] of this.documents.entries()) {
            size += JSON.stringify(doc).length * 2;
        }

        return {
            bytes: size,
            kb: (size / 1024).toFixed(2),
            mb: (size / 1024 / 1024).toFixed(2)
        };
    }
}

// ========================================
// Web Worker 池
// ========================================

class WorkerPool {
    constructor(workerScript, poolSize = navigator.hardwareConcurrency || 4) {
        this.workerScript = workerScript;
        this.poolSize = poolSize;
        this.workers = [];
        this.taskQueue = [];
        this.activeTasks = new Map();
        this.nextTaskId = 0;
        this.stats = {
            totalTasks: 0,
            completedTasks: 0,
            failedTasks: 0,
            avgExecutionTime: 0
        };

        this.init();
    }

    init() {
        for (let i = 0; i < this.poolSize; i++) {
            try {
                const worker = new Worker(this.workerScript);
                worker.id = i;
                worker.busy = false;

                worker.onmessage = (e) => this.handleWorkerMessage(worker, e);
                worker.onerror = (e) => this.handleWorkerError(worker, e);

                this.workers.push(worker);
            } catch (error) {
                console.error(`创建 Worker ${i} 失败:`, error);
            }
        }

        console.log(`✅ Worker 池初始化完成: ${this.workers.length} 个 Worker`);
    }

    async execute(taskType, data) {
        return new Promise((resolve, reject) => {
            const taskId = this.nextTaskId++;
            const task = {
                id: taskId,
                type: taskType,
                data,
                resolve,
                reject,
                startTime: performance.now()
            };

            this.stats.totalTasks++;
            this.taskQueue.push(task);
            this.processQueue();
        });
    }

    processQueue() {
        if (this.taskQueue.length === 0) return;

        // 找到空闲的 Worker
        const freeWorker = this.workers.find(w => !w.busy);
        if (!freeWorker) return;

        const task = this.taskQueue.shift();
        freeWorker.busy = true;
        this.activeTasks.set(freeWorker.id, task);

        freeWorker.postMessage({
            taskId: task.id,
            type: task.type,
            data: task.data
        });
    }

    handleWorkerMessage(worker, event) {
        const { taskId, result, error } = event.data;
        const task = this.activeTasks.get(worker.id);

        if (!task) {
            console.warn(`收到未知任务 ${taskId} 的响应`);
            return;
        }

        worker.busy = false;
        this.activeTasks.delete(worker.id);

        const executionTime = performance.now() - task.startTime;
        this.updateStats(executionTime, !error);

        if (error) {
            task.reject(new Error(error));
        } else {
            task.resolve(result);
        }

        // 处理队列中的下一个任务
        this.processQueue();
    }

    handleWorkerError(worker, error) {
        console.error(`Worker ${worker.id} 错误:`, error);

        const task = this.activeTasks.get(worker.id);
        if (task) {
            worker.busy = false;
            this.activeTasks.delete(worker.id);
            this.stats.failedTasks++;
            task.reject(error);
        }

        // 尝试重启 Worker
        this.restartWorker(worker);

        // 处理队列中的下一个任务
        this.processQueue();
    }

    restartWorker(worker) {
        try {
            worker.terminate();
            const newWorker = new Worker(this.workerScript);
            newWorker.id = worker.id;
            newWorker.busy = false;

            newWorker.onmessage = (e) => this.handleWorkerMessage(newWorker, e);
            newWorker.onerror = (e) => this.handleWorkerError(newWorker, e);

            const index = this.workers.findIndex(w => w.id === worker.id);
            if (index !== -1) {
                this.workers[index] = newWorker;
            }

            console.log(`✅ Worker ${worker.id} 已重启`);
        } catch (error) {
            console.error(`重启 Worker ${worker.id} 失败:`, error);
        }
    }

    updateStats(executionTime, success) {
        if (success) {
            this.stats.completedTasks++;
            const totalTime = this.stats.avgExecutionTime * (this.stats.completedTasks - 1) + executionTime;
            this.stats.avgExecutionTime = totalTime / this.stats.completedTasks;
        } else {
            this.stats.failedTasks++;
        }
    }

    getStats() {
        return {
            ...this.stats,
            poolSize: this.poolSize,
            activeWorkers: this.workers.filter(w => w.busy).length,
            queueLength: this.taskQueue.length,
            successRate: this.stats.totalTasks > 0
                ? ((this.stats.completedTasks / this.stats.totalTasks) * 100).toFixed(2) + '%'
                : '0%'
        };
    }

    terminate() {
        this.workers.forEach(worker => worker.terminate());
        this.workers = [];
        this.taskQueue = [];
        this.activeTasks.clear();
    }
}


// ========================================
// 对象池
// ========================================

class ObjectPool {
    constructor(factory, resetFn, initialSize = 10, maxSize = 100) {
        this.factory = factory;
        this.resetFn = resetFn;
        this.maxSize = maxSize;
        this.pool = [];
        this.stats = {
            created: 0,
            acquired: 0,
            released: 0,
            reused: 0
        };

        // 预创建对象
        for (let i = 0; i < initialSize; i++) {
            this.pool.push(this.factory());
            this.stats.created++;
        }
    }

    acquire() {
        this.stats.acquired++;

        if (this.pool.length > 0) {
            this.stats.reused++;
            return this.pool.pop();
        }

        // 池为空,创建新对象
        this.stats.created++;
        return this.factory();
    }

    release(obj) {
        if (!obj) return;

        this.stats.released++;

        // 重置对象状态
        if (this.resetFn) {
            this.resetFn(obj);
        }

        // 如果池未满,放回池中
        if (this.pool.length < this.maxSize) {
            this.pool.push(obj);
        }
    }

    clear() {
        this.pool = [];
    }

    getStats() {
        return {
            ...this.stats,
            poolSize: this.pool.length,
            maxSize: this.maxSize,
            reuseRate: this.stats.acquired > 0
                ? ((this.stats.reused / this.stats.acquired) * 100).toFixed(2) + '%'
                : '0%'
        };
    }
}

// DOM 节点池
class DOMNodePool extends ObjectPool {
    constructor(tagName, className, initialSize = 20) {
        super(
            () => {
                const node = document.createElement(tagName);
                if (className) node.className = className;
                return node;
            },
            (node) => {
                node.innerHTML = '';
                node.className = className || '';
                node.style.cssText = '';
                // 移除所有事件监听器
                const clone = node.cloneNode(false);
                node.parentNode?.replaceChild(clone, node);
                return clone;
            },
            initialSize
        );
    }
}

// ========================================
// 性能监控器
// ========================================

class PerformanceMonitor {
    constructor() {
        this.metrics = new Map();
        this.marks = new Map();
        this.observers = [];
        this.thresholds = {
            fcp: 1800,  // First Contentful Paint
            lcp: 2500,  // Largest Contentful Paint
            fid: 100,   // First Input Delay
            cls: 0.1,   // Cumulative Layout Shift
            longTask: 50 // Long Task
        };

        this.init();
    }

    init() {
        // 监控 Web Vitals
        this.observeWebVitals();

        // 监控长任务
        this.observeLongTasks();

        // 监控内存
        this.observeMemory();
    }

    observeWebVitals() {
        // FCP
        if ('PerformanceObserver' in window) {
            try {
                const fcpObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.name === 'first-contentful-paint') {
                            this.recordMetric('FCP', entry.startTime);
                        }
                    }
                });
                fcpObserver.observe({ entryTypes: ['paint'] });
                this.observers.push(fcpObserver);
            } catch (e) {
                console.warn('FCP 监控不可用:', e);
            }

            // LCP
            try {
                const lcpObserver = new PerformanceObserver((list) => {
                    const entries = list.getEntries();
                    const lastEntry = entries[entries.length - 1];
                    this.recordMetric('LCP', lastEntry.renderTime || lastEntry.loadTime);
                });
                lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] });
                this.observers.push(lcpObserver);
            } catch (e) {
                console.warn('LCP 监控不可用:', e);
            }

            // FID
            try {
                const fidObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        this.recordMetric('FID', entry.processingStart - entry.startTime);
                    }
                });
                fidObserver.observe({ entryTypes: ['first-input'] });
                this.observers.push(fidObserver);
            } catch (e) {
                console.warn('FID 监控不可用:', e);
            }

            // CLS
            try {
                let clsValue = 0;
                const clsObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            clsValue += entry.value;
                            this.recordMetric('CLS', clsValue);
                        }
                    }
                });
                clsObserver.observe({ entryTypes: ['layout-shift'] });
                this.observers.push(clsObserver);
            } catch (e) {
                console.warn('CLS 监控不可用:', e);
            }
        }
    }

    observeLongTasks() {
        if ('PerformanceObserver' in window) {
            try {
                const longTaskObserver = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.duration > this.thresholds.longTask) {
                            this.recordMetric('LongTask', entry.duration, {
                                name: entry.name,
                                startTime: entry.startTime
                            });
                        }
                    }
                });
                longTaskObserver.observe({ entryTypes: ['longtask'] });
                this.observers.push(longTaskObserver);
            } catch (e) {
                console.warn('Long Task 监控不可用:', e);
            }
        }
    }

    observeMemory() {
        if (performance.memory) {
            setInterval(() => {
                const memory = performance.memory;
                this.recordMetric('Memory', {
                    used: memory.usedJSHeapSize,
                    total: memory.totalJSHeapSize,
                    limit: memory.jsHeapSizeLimit,
                    usagePercent: (memory.usedJSHeapSize / memory.jsHeapSizeLimit * 100).toFixed(2)
                });
            }, 5000);
        }
    }

    start(label) {
        this.marks.set(label, performance.now());
    }

    end(label) {
        const startTime = this.marks.get(label);
        if (startTime !== undefined) {
            const duration = performance.now() - startTime;
            this.recordMetric(label, duration);
            this.marks.delete(label);
            return duration;
        }
        return null;
    }

    mark(name) {
        if (performance.mark) {
            performance.mark(name);
        }
    }

    measure(name, startMark, endMark) {
        if (performance.measure) {
            try {
                performance.measure(name, startMark, endMark);
                const measures = performance.getEntriesByName(name, 'measure');
                if (measures.length > 0) {
                    const duration = measures[measures.length - 1].duration;
                    this.recordMetric(name, duration);
                    return duration;
                }
            } catch (e) {
                console.warn(`测量 ${name} 失败:`, e);
            }
        }
        return null;
    }

    recordMetric(name, value, metadata = {}) {
        if (!this.metrics.has(name)) {
            this.metrics.set(name, []);
        }

        this.metrics.get(name).push({
            value,
            timestamp: Date.now(),
            ...metadata
        });

        // 检查是否超过阈值
        this.checkThreshold(name, value);
    }

    checkThreshold(name, value) {
        const threshold = this.thresholds[name.toLowerCase()];
        if (threshold !== undefined) {
            if (typeof value === 'number' && value > threshold) {
                console.warn(`⚠️ 性能警告: ${name} = ${value.toFixed(2)} (阈值: ${threshold})`);
            }
        }
    }

    getMetrics() {
        const result = {};

        for (const [name, values] of this.metrics.entries()) {
            if (values.length === 0) continue;

            const numericValues = values
                .map(v => typeof v.value === 'number' ? v.value : null)
                .filter(v => v !== null);

            if (numericValues.length > 0) {
                result[name] = {
                    current: values[values.length - 1].value,
                    avg: numericValues.reduce((a, b) => a + b, 0) / numericValues.length,
                    min: Math.min(...numericValues),
                    max: Math.max(...numericValues),
                    count: values.length
                };
            } else {
                result[name] = {
                    current: values[values.length - 1].value,
                    count: values.length
                };
            }
        }

        return result;
    }

    exportReport() {
        const metrics = this.getMetrics();
        const report = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            metrics,
            recommendations: this.generateRecommendations(metrics)
        };

        return JSON.stringify(report, null, 2);
    }

    generateRecommendations(metrics) {
        const recommendations = [];

        if (metrics.FCP && metrics.FCP.current > this.thresholds.fcp) {
            recommendations.push('FCP 过高,建议优化首屏渲染');
        }

        if (metrics.LCP && metrics.LCP.current > this.thresholds.lcp) {
            recommendations.push('LCP 过高,建议优化最大内容渲染');
        }

        if (metrics.FID && metrics.FID.current > this.thresholds.fid) {
            recommendations.push('FID 过高,建议减少主线程阻塞');
        }

        if (metrics.CLS && metrics.CLS.current > this.thresholds.cls) {
            recommendations.push('CLS 过高,建议优化布局稳定性');
        }

        if (metrics.Memory && typeof metrics.Memory.current === 'object') {
            const usagePercent = parseFloat(metrics.Memory.current.usagePercent);
            if (usagePercent > 80) {
                recommendations.push('内存使用过高,建议优化内存管理');
            }
        }

        if (metrics.LongTask && metrics.LongTask.count > 10) {
            recommendations.push('长任务过多,建议拆分任务或使用 Web Worker');
        }

        return recommendations;
    }

    showPanel() {
        const metrics = this.getMetrics();
        const panel = document.createElement('div');
        panel.id = 'performancePanel';
        panel.className = 'performance-panel';

        let html = '<div class="performance-panel-header">';
        html += '<h3>⚡ 性能监控</h3>';
        html += '<button onclick="advancedPerformanceMonitor.hidePanel()">✕</button>';
        html += '</div>';

        html += '<div class="performance-panel-body">';

        for (const [name, data] of Object.entries(metrics)) {
            html += `<div class="metric-item">`;
            html += `<strong>${name}</strong>`;

            if (typeof data.current === 'number') {
                html += `<span>${data.current.toFixed(2)}ms</span>`;
                if (data.avg !== undefined) {
                    html += `<small>平均: ${data.avg.toFixed(2)}ms</small>`;
                }
            } else if (typeof data.current === 'object') {
                html += `<pre>${JSON.stringify(data.current, null, 2)}</pre>`;
            } else {
                html += `<span>${data.current}</span>`;
            }

            html += `</div>`;
        }

        const recommendations = this.generateRecommendations(metrics);
        if (recommendations.length > 0) {
            html += '<div class="metric-recommendations">';
            html += '<h4>💡 优化建议</h4>';
            html += '<ul>';
            recommendations.forEach(rec => {
                html += `<li>${rec}</li>`;
            });
            html += '</ul>';
            html += '</div>';
        }

        html += '</div>';

        html += '<div class="performance-panel-footer">';
        html += '<button onclick="advancedPerformanceMonitor.exportReport()">导出报告</button>';
        html += '<button onclick="advancedPerformanceMonitor.clear()">清除数据</button>';
        html += '</div>';

        panel.innerHTML = html;

        // 移除旧面板
        const oldPanel = document.getElementById('performancePanel');
        if (oldPanel) oldPanel.remove();

        document.body.appendChild(panel);
    }

    hidePanel() {
        const panel = document.getElementById('performancePanel');
        if (panel) panel.remove();
    }

    clear() {
        this.metrics.clear();
        this.marks.clear();
        console.log('✅ 性能数据已清除');
    }

    destroy() {
        this.observers.forEach(observer => observer.disconnect());
        this.observers = [];
        this.clear();
    }
}

// ========================================
// Service Worker 管理器
// ========================================

class ServiceWorkerManager {
    constructor() {
        this.registration = null;
        this.updateAvailable = false;
    }

    async register() {
        if (!('serviceWorker' in navigator)) {
            console.warn('⚠️ 浏览器不支持 Service Worker');
            return false;
        }

        try {
            this.registration = await navigator.serviceWorker.register('sw.js', {
                scope: '/'
            });

            console.log('✅ Service Worker 注册成功:', this.registration.scope);

            // 监听更新
            this.registration.addEventListener('updatefound', () => {
                const newWorker = this.registration.installing;
                console.log('🔄 发现 Service Worker 更新');

                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                        this.updateAvailable = true;
                        this.showUpdateNotification();
                    }
                });
            });

            // 检查更新
            this.checkForUpdates();

            return true;
        } catch (error) {
            console.error('❌ Service Worker 注册失败:', error);
            return false;
        }
    }

    async update() {
        if (!this.registration) {
            console.warn('⚠️ Service Worker 未注册');
            return;
        }

        try {
            await this.registration.update();
            console.log('✅ Service Worker 更新检查完成');
        } catch (error) {
            console.error('❌ Service Worker 更新失败:', error);
        }
    }

    async clearCache() {
        if (!this.registration || !this.registration.active) {
            console.warn('⚠️ Service Worker 未激活');
            return;
        }

        try {
            // 发送清除缓存消息
            this.registration.active.postMessage({
                type: 'CLEAR_CACHE'
            });

            console.log('✅ 缓存清除请求已发送');
        } catch (error) {
            console.error('❌ 清除缓存失败:', error);
        }
    }

    checkForUpdates() {
        // 每小时检查一次更新
        setInterval(() => {
            if (this.registration) {
                this.registration.update();
            }
        }, 60 * 60 * 1000);
    }

    showUpdateNotification() {
        const notification = document.createElement('div');
        notification.className = 'sw-update-notification';
        notification.innerHTML = `
            <div class="sw-update-content">
                <span>🔄 发现新版本</span>
                <button onclick="serviceWorkerManager.applyUpdate()">立即更新</button>
                <button onclick="this.parentElement.parentElement.remove()">稍后</button>
            </div>
        `;

        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('visible'), 100);
    }

    applyUpdate() {
        if (!this.registration || !this.registration.waiting) {
            console.warn('⚠️ 没有等待的 Service Worker');
            return;
        }

        // 告诉等待的 Service Worker 跳过等待
        this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });

        // 监听控制器变化
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            window.location.reload();
        });
    }

    async unregister() {
        if (!this.registration) {
            console.warn('⚠️ Service Worker 未注册');
            return;
        }

        try {
            await this.registration.unregister();
            console.log('✅ Service Worker 已注销');
            this.registration = null;
        } catch (error) {
            console.error('❌ Service Worker 注销失败:', error);
        }
    }
}

// ========================================
// 全局实例
// ========================================

let chunkLoader = null;
let indexedDBManager = null;
let invertedIndexSearchEngine = null;
let workerPool = null;
let domNodePool = null;
let advancedPerformanceMonitor = null;  // 重命名避免与app.js中的performanceMonitor冲突
let serviceWorkerManager = null;

// 初始化性能优化功能
async function initPerformanceOptimization() {
    console.log('🚀 初始化性能优化模块...');

    // 初始化高级性能监控
    advancedPerformanceMonitor = new PerformanceMonitor();
    advancedPerformanceMonitor.start('初始化');

    // 初始化 Service Worker
    try {
        serviceWorkerManager = new ServiceWorkerManager();
        await serviceWorkerManager.register();
        console.log('✅ Service Worker 初始化完成');
    } catch (error) {
        console.warn('⚠️ Service Worker 初始化失败:', error);
    }

    // 初始化 IndexedDB
    try {
        indexedDBManager = new IndexedDBManager();
        await indexedDBManager.init();
        console.log('✅ IndexedDB 初始化完成');
    } catch (error) {
        console.warn('⚠️ IndexedDB 初始化失败:', error);
    }

    // 初始化分块加载器
    chunkLoader = new ChunkLoader(1000);

    // 初始化倒排索引搜索引擎
    invertedIndexSearchEngine = new InvertedIndexSearchEngine();

    // 初始化 DOM 节点池
    domNodePool = new DOMNodePool('div', 'article-card', 20);

    // 初始化 Worker 池 (如果支持)
    if (typeof Worker !== 'undefined') {
        try {
            // workerPool = new WorkerPool('search-worker.js');
            // console.log('✅ Worker 池初始化完成');
        } catch (error) {
            console.warn('⚠️ Worker 池初始化失败:', error);
        }
    }

    advancedPerformanceMonitor.end('初始化');

    console.log('✅ 性能优化模块初始化完成');
}

// 导出到全局
if (typeof window !== 'undefined') {
    window.chunkLoader = chunkLoader;
    window.indexedDBManager = indexedDBManager;
    window.invertedIndexSearchEngine = invertedIndexSearchEngine;
    window.workerPool = workerPool;
    window.domNodePool = domNodePool;
    window.advancedPerformanceMonitor = advancedPerformanceMonitor;
    window.serviceWorkerManager = serviceWorkerManager;
    window.initPerformanceOptimization = initPerformanceOptimization;
}
