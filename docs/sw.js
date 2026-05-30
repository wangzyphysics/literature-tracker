/**
 * 文献追踪系统 - Service Worker
 * 实现离线缓存和PWA支持
 */

const CACHE_NAME = 'literature-tracker-v3';
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
    '/exports.js',
    '/feed.html',
    '/feed.css',
    '/feed.js',
    '/likes.js',
    '/data/feed.json'
];

const DATA_CACHE_NAME = 'literature-data-v3';

// 安装事件 - 缓存静态资源
self.addEventListener('install', event => {
    console.log('[SW] 安装中...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[SW] 缓存静态资源');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// 激活事件 - 清理旧缓存
self.addEventListener('activate', event => {
    console.log('[SW] 激活中...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME && name !== DATA_CACHE_NAME)
                    .map(name => {
                        console.log('[SW] 删除旧缓存:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    const isDailyOrWeekly =
        (url.pathname.startsWith('/daily/') || url.pathname.startsWith('/weekly/')) &&
        url.pathname.endsWith('.html');

    if (isDailyOrWeekly) {
        // network-first with cache fallback for daily/weekly HTML
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

    // default: cache-first for static assets, fall back to network
    event.respondWith(
        caches.match(event.request).then(cached => {
            return cached || fetch(event.request).then(resp => {
                if (resp && resp.ok && event.request.method === 'GET') {
                    const copy = resp.clone();
                    caches.open(DATA_CACHE_NAME).then(c => c.put(event.request, copy));
                }
                return resp;
            }).catch(() => caches.match(event.request));
        })
    );
});

// Cache First 策略
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) {
        return cached;
    }

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.log('[SW] 网络请求失败:', error);
        // 返回离线页面或默认响应
        return new Response('离线模式 - 无法加载资源', {
            status: 503,
            statusText: 'Service Unavailable'
        });
    }
}

// Network First 策略
async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (error) {
        console.log('[SW] 网络请求失败，使用缓存:', error);
        const cached = await caches.match(request);
        if (cached) {
            return cached;
        }
        return new Response(JSON.stringify({ error: '离线模式' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
        });
    }
}

// 后台同步
self.addEventListener('sync', event => {
    if (event.tag === 'sync-data') {
        event.waitUntil(syncData());
    }
});

async function syncData() {
    try {
        const response = await fetch('/data/index.json');
        if (response.ok) {
            const cache = await caches.open(DATA_CACHE_NAME);
            await cache.put('/data/index.json', response);
            console.log('[SW] 数据同步完成');
        }
    } catch (error) {
        console.log('[SW] 数据同步失败:', error);
    }
}

// 推送通知（可选）
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/icon-192.png'
        });
    }
});
