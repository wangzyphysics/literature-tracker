/**
 * 文献追踪系统 - Service Worker(离线缓存 / PWA)
 *
 * 约束:站点部署在 GitHub Pages 项目子路径(/<repo>/)下,
 * 预缓存与注册必须用 ./ 相对路径——绝对路径(/index.html)会指向
 * user.github.io 根而 404,导致 install 整体失败。
 *
 * 策略:
 * - 数据(*.json、*.xml、/data/)与生成页(/daily/、/weekly/ 的 html)
 *   network-first:日更内容,缓存仅作离线兜底,避免用户被锁在旧数据上
 * - 其余同源静态资源 cache-first(带 ?v= 版本号的请求天然绕过旧缓存)
 * - 跨域(CDN)请求不拦截
 */

const CACHE_NAME = 'literature-tracker-v6';
const DATA_CACHE_NAME = 'literature-data-v6';

const STATIC_ASSETS = [
    './',
    './index.html',
    './analytics.html',
    './style.css',
    './daily-common.css',
    './app.js',
    './analytics.js',
    './manifest.json',
    './bookmarks.js',
    './bookmarks.css',
    './exports.js',
    './performance-optimization.js',
    './advanced-features.js'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(names => Promise.all(
            names
                .filter(name => name !== CACHE_NAME && name !== DATA_CACHE_NAME)
                .map(name => caches.delete(name))
        )).then(() => self.clients.claim())
    );
});

function isNetworkFirst(url) {
    const p = url.pathname;
    if (p.endsWith('.json') || p.endsWith('.xml') || p.includes('/data/')) return true;
    return (p.includes('/daily/') || p.includes('/weekly/')) && p.endsWith('.html');
}

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    const url = new URL(event.request.url);
    if (url.origin !== self.location.origin) return;

    if (isNetworkFirst(url)) {
        event.respondWith(
            fetch(event.request).then(resp => {
                if (resp && resp.ok) {
                    const copy = resp.clone();
                    caches.open(DATA_CACHE_NAME).then(c => c.put(event.request, copy));
                }
                return resp;
            }).catch(() =>
                caches.match(event.request).then(r => r || Response.error())
            )
        );
        return;
    }

    event.respondWith(
        caches.match(event.request).then(cached =>
            cached || fetch(event.request).then(resp => {
                if (resp && resp.ok) {
                    const copy = resp.clone();
                    caches.open(CACHE_NAME).then(c => c.put(event.request, copy));
                }
                return resp;
            })
        )
    );
});
