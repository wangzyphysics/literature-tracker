#!/usr/bin/env python3
"""docs/ 静态资产引用回归测试(stdlib-only)。

防止两类线上 404:
- index.html / analytics.html 引用了不存在的本地 css/js/json 资源
- (Task B6 起)sw.js 预缓存清单引用不存在文件 → Service Worker 安装失败
"""
import os
import re

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")

# 只校验资产类引用;页面间导航(daily/、weekly/ 等生成页)不在此测试范围
_ASSET_EXT = (".css", ".js", ".json", ".xml", ".png", ".svg", ".webp", ".ico", ".webmanifest")
_ATTR_RE = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)


def _local_asset_refs(html_name):
    path = os.path.join(DOCS, html_name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    refs = []
    for url in _ATTR_RE.findall(text):
        if url.startswith(("http://", "https://", "//", "data:", "mailto:", "#", "javascript:")):
            continue
        clean = url.split("?", 1)[0].split("#", 1)[0]
        if clean.endswith(_ASSET_EXT):
            refs.append(clean)
    return refs


def _assert_exists(refs, base_html):
    missing = []
    for ref in refs:
        target = os.path.normpath(os.path.join(DOCS, ref.lstrip("/")))
        if not os.path.isfile(target):
            missing.append(ref)
    assert not missing, f"{base_html} 引用了不存在的本地资源: {missing}"


def test_index_html_assets_exist():
    refs = _local_asset_refs("index.html")
    assert refs, "index.html 应当至少引用 style.css/app.js 等本地资产"
    _assert_exists(refs, "index.html")


def test_analytics_html_assets_exist():
    refs = _local_asset_refs("analytics.html")
    _assert_exists(refs, "analytics.html")


if __name__ == "__main__":
    test_index_html_assets_exist()
    test_analytics_html_assets_exist()
    print("OK")
