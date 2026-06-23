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


def _read(name):
    with open(os.path.join(DOCS, name), encoding="utf-8") as f:
        return f.read()


def test_sw_precache_relative_and_existing():
    """站点挂在 GitHub Pages 项目子路径下:预缓存绝对路径(/x)必 404 → install 失败。"""
    sw = _read("sw.js")
    m = re.search(r"STATIC_ASSETS\s*=\s*\[(.*?)\]", sw, re.DOTALL)
    assert m, "sw.js 应定义 STATIC_ASSETS"
    entries = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
    assert entries, "STATIC_ASSETS 不应为空"
    bad_abs = [e for e in entries if not e.startswith("./")]
    assert not bad_abs, f"预缓存必须用 ./ 相对路径: {bad_abs}"
    missing = [e for e in entries if e != "./" and not os.path.isfile(os.path.join(DOCS, e[2:]))]
    assert not missing, f"预缓存引用了不存在的文件(install 必失败): {missing}"


def test_sw_registration_paths_relative():
    """register('/sw.js') 与 scope:'/' 在项目子路径下分别 404/抛异常。"""
    for name in ("app.js", "performance-optimization.js"):
        src = _read(name)
        assert "register('/sw.js'" not in src and 'register("/sw.js"' not in src, \
            f"{name} 不得用绝对路径注册 sw"
        for call in re.findall(r"serviceWorker\.register\([^)]*\)", src):
            assert "scope" not in call, f"{name} 注册不应显式指定 scope(子路径下 '/' 非法): {call}"


def test_index_main_scripts_deferred_and_preconnect():
    html = _read("index.html")
    assert re.search(r'rel="preconnect"\s+href="https://cdn\.jsdelivr\.net"', html), \
        "index.html 应预连接 cdn.jsdelivr.net(KaTeX css 为渲染阻塞资源)"
    for script in ("performance-optimization.js", "advanced-features.js", "app.js"):
        tag = re.search(r"<script[^>]*src=\"%s[^\"]*\"[^>]*>" % re.escape(script), html)
        assert tag, f"index.html 应引用 {script}"
        assert "defer" in tag.group(0), f"{script} 应当 defer(内联脚本已验证无同步依赖)"


def test_daily_common_css_has_abstract_and_highlight():
    css = _read("daily-common.css")
    assert ".daily-paper-abstract" in css, "应为摘要块加样式"
    assert ".daily-paper-highlight" in css, "应为亮点块加样式"


if __name__ == "__main__":
    for _fn in sorted(k for k in dir() if k.startswith("test_")):
        globals()[_fn]()
        print(f"✓ {_fn}")
    print("OK")
