#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Enhance generated weekly HTML pages with prev/next navigation, richer hyperlinks, and a scrollable single-page TOC."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from text_normalizer import normalize_text

STYLE_ID = "weekly-enhancement-style"
TOP_NAV_ID = "weekly-enhancement-top-nav"
BOTTOM_NAV_ID = "weekly-enhancement-bottom-nav"
SIDEBAR_NAV_ID = "weekly-enhancement-sidebar-nav"
OUTLINE_ID = "weekly-enhancement-outline"

ENHANCEMENT_CSS = """
#weekly-enhancement-top-nav, #weekly-enhancement-bottom-nav {
    margin-top: 18px;
}

.weekly-page-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
}

.weekly-page-nav-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 9px 14px;
    border-radius: 999px;
    border: 1px solid var(--border-color);
    background: rgba(255,255,255,0.92);
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 0.92rem;
    transition: all var(--transition-fast);
}

[data-theme="dark"] .weekly-page-nav-link {
    background: rgba(30,41,59,0.92);
}

.weekly-page-nav-link:hover {
    color: var(--accent-primary);
    border-color: rgba(99,102,241,0.35);
    background: rgba(99,102,241,0.08);
}

.weekly-page-nav-disabled {
    opacity: 0.45;
    pointer-events: none;
}

.weekly-permalink-link {
    margin-left: 8px;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
}

.weekly-permalink-link:hover {
    color: var(--accent-primary);
}

.weekly-inline-links {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 10px;
}

.weekly-inline-link {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: var(--accent-primary);
    text-decoration: none;
    font-size: 0.9rem;
    font-weight: 600;
}

.weekly-inline-link:hover {
    color: var(--accent-hover);
}

.weekly-report-sidebar {
    max-height: min(74vh, calc(100vh - 40px));
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable both-edges;
    padding-right: 12px;
}

.weekly-report-sidebar::-webkit-scrollbar {
    width: 10px;
}

.weekly-report-sidebar::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.28);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}

.weekly-report-sidebar::-webkit-scrollbar-track {
    background: rgba(148, 163, 184, 0.10);
    border-radius: 999px;
}

.weekly-outline-scroll {
    max-height: min(40vh, calc(100vh - 320px));
    overflow-y: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable both-edges;
    padding-right: 6px;
}

.weekly-outline-scroll::-webkit-scrollbar {
    width: 10px;
}

.weekly-outline-scroll::-webkit-scrollbar-thumb {
    background: rgba(99, 102, 241, 0.28);
    border-radius: 999px;
    border: 2px solid transparent;
    background-clip: padding-box;
}

.weekly-outline-scroll::-webkit-scrollbar-track {
    background: rgba(148, 163, 184, 0.10);
    border-radius: 999px;
}

.weekly-outline-group + .weekly-outline-group {
    margin-top: 14px;
}

.weekly-outline-group-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
    padding: 10px 12px;
    border-radius: 14px;
    color: var(--text-primary);
    text-decoration: none;
    background: rgba(255,255,255,0.65);
    border: 1px solid rgba(148,163,184,0.18);
    font-weight: 700;
}

[data-theme="dark"] .weekly-outline-group-title {
    background: rgba(30,41,59,0.78);
}

.weekly-outline-group-title:hover {
    color: var(--accent-primary);
    border-color: rgba(99,102,241,0.28);
}

.weekly-outline-list {
    display: grid;
    gap: 6px;
}

.weekly-outline-link {
    display: block;
    padding: 8px 10px;
    border-radius: 12px;
    color: var(--text-secondary);
    text-decoration: none;
    font-size: 0.9rem;
    line-height: 1.45;
    background: rgba(255,255,255,0.55);
    border: 1px solid rgba(148,163,184,0.14);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

[data-theme="dark"] .weekly-outline-link {
    background: rgba(30,41,59,0.70);
}

.weekly-outline-link:hover {
    color: var(--accent-primary);
    background: rgba(99,102,241,0.08);
}

.weekly-outline-link-highlight {
    border-color: rgba(99,102,241,0.24);
}

.weekly-outline-meta {
    display: block;
    margin-top: 2px;
    color: var(--text-muted);
    font-size: 0.8rem;
}

@media (max-width: 980px) {
    .weekly-report-sidebar {
        max-height: none;
    }
    .weekly-outline-scroll {
        max-height: none;
    }
}
"""


def _safe_text(text: str) -> str:
    return " ".join(normalize_text(text or "").split())


def _slugify(text: str, fallback: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", _safe_text(text)).strip("-").lower()
    return base or fallback


def _relative_weekly_href(entry: Dict[str, str]) -> str:
    return entry.get("file") or f"{entry.get('week_start')}.html"


def load_weekly_entries(index_path: str | Path = "docs/weekly/index.json") -> List[Dict]:
    path = Path(index_path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [item for item in (data.get("weeklies") or []) if isinstance(item, dict) and item.get("week_start")]


def build_nav_context(entries: List[Dict]) -> Dict[str, Dict[str, Optional[Dict]]]:
    by_start: Dict[str, Dict[str, Optional[Dict]]] = {}
    for idx, entry in enumerate(entries):
        by_start[entry["week_start"]] = {
            "newer": entries[idx - 1] if idx > 0 else None,
            "older": entries[idx + 1] if idx + 1 < len(entries) else None,
            "latest": entries[0] if entries else None,
        }
    return by_start


def _range_label(current_start: str, target_start: Optional[str], *, older: bool) -> str:
    if not target_start:
        return ""
    try:
        current_dt = datetime.strptime(current_start, "%Y-%m-%d")
        target_dt = datetime.strptime(target_start, "%Y-%m-%d")
        days = abs((current_dt - target_dt).days)
    except Exception:
        days = None
    if days == 7:
        return "前一周" if older else "后一周"
    return "上一期" if older else "下一期"


def _ensure_style(soup: BeautifulSoup) -> None:
    old = soup.find(id=STYLE_ID)
    if old is not None:
        old.decompose()
    style = soup.new_tag("style", id=STYLE_ID)
    style.string = ENHANCEMENT_CSS
    if soup.head is not None:
        soup.head.append(style)


def _remove_existing_injected_blocks(soup: BeautifulSoup) -> None:
    for block_id in (TOP_NAV_ID, BOTTOM_NAV_ID, SIDEBAR_NAV_ID, OUTLINE_ID):
        node = soup.find(id=block_id)
        if node is not None:
            node.decompose()

    for node in soup.select(".weekly-inline-links"):
        node.decompose()
    for node in soup.select("a.weekly-permalink-link"):
        node.decompose()


def _sanitize_soup_text(soup: BeautifulSoup) -> None:
    for node in list(soup.find_all(string=True)):
        if isinstance(node, Comment):
            continue
        if node.parent is not None and node.parent.name in {"script", "style"}:
            continue
        old = str(node)
        new = normalize_text(old)
        if new != old:
            node.replace_with(NavigableString(new))

    for tag in soup.find_all(True):
        for attr in ("title", "aria-label", "alt", "content"):
            if tag.has_attr(attr):
                tag[attr] = normalize_text(tag.get(attr))


def _title_plain_text(node: Optional[Tag]) -> str:
    if node is None:
        return ""
    texts = []
    for child in node.children:
        if hasattr(child, "get") and "weekly-permalink-link" in (child.get("class") or []):
            continue
        if hasattr(child, "get_text"):
            texts.append(child.get_text(" ", strip=True))
        else:
            texts.append(str(child))
    return _safe_text(" ".join(texts))


def _ensure_permalink(soup: BeautifulSoup, node: Optional[Tag], anchor_id: str) -> None:
    if node is None:
        return
    if node.select_one("a.weekly-permalink-link") is not None:
        return
    permalink = soup.new_tag("a", href=f"#{anchor_id}", **{"class": "weekly-permalink-link", "title": "复制本页定位"})
    permalink.string = "#"
    node.append(permalink)


def _ensure_inline_links(soup: BeautifulSoup, card: Tag, anchor_id: str, section_id: str) -> None:
    actions = card.select_one(".weekly-paper-actions")
    if actions is None:
        return
    inline = soup.new_tag("div", **{"class": "weekly-inline-links"})
    anchor = soup.new_tag("a", href=f"#{anchor_id}", **{"class": "weekly-inline-link"})
    anchor.string = "页内定位"
    inline.append(anchor)
    section_link = soup.new_tag("a", href=f"#{section_id}", **{"class": "weekly-inline-link"})
    section_link.string = "所在专题"
    inline.append(section_link)
    actions.append(inline)


def _build_nav_block(
    soup: BeautifulSoup,
    nav: Dict[str, Optional[Dict]],
    *,
    current_start: str,
    block_id: str,
    overview_href: str = "#overview",
    focus_href: Optional[str] = None,
    papers_href: Optional[str] = None,
    journals_href: Optional[str] = None,
    compact: bool = False,
) -> Tag:
    wrapper = soup.new_tag("div", id=block_id, **{"class": "weekly-page-nav"})

    def append_link(label: str, href: Optional[str], extra_text: str = "", disabled: bool = False):
        cls = "weekly-page-nav-link"
        if disabled:
            cls += " weekly-page-nav-disabled"
            tag = soup.new_tag("span", **{"class": cls})
        else:
            tag = soup.new_tag("a", href=href or "#", **{"class": cls})
        tag.string = label + (f" · {extra_text}" if extra_text else "")
        wrapper.append(tag)

    older = nav.get("older")
    newer = nav.get("newer")
    latest = nav.get("latest")

    append_link(
        _range_label(current_start, older.get("week_start") if older else None, older=True) or "前一周",
        _relative_weekly_href(older) if older else None,
        f"{older.get('week_start')} → {older.get('week_end')}" if older else "暂无",
        disabled=older is None,
    )
    append_link(
        _range_label(current_start, newer.get("week_start") if newer else None, older=False) or "后一周",
        _relative_weekly_href(newer) if newer else None,
        f"{newer.get('week_start')} → {newer.get('week_end')}" if newer else "暂无",
        disabled=newer is None,
    )
    if latest is not None:
        append_link("最新一期", _relative_weekly_href(latest), f"{latest.get('week_start')} → {latest.get('week_end')}")
    append_link("周报归档", "index.html")
    append_link("日报归档", "../daily/index.html")
    append_link("站点RSS", "../feed.xml")
    append_link("主页", "../index.html")
    if not compact:
        append_link("本周总览", overview_href)
        if focus_href:
            append_link("交叉研究", focus_href)
        if papers_href:
            append_link("全文速览", papers_href)
        if journals_href:
            append_link("期刊分布", journals_href)
    return wrapper


def enhance_weekly_html_file(file_path: str | Path, entries: List[Dict], *, week_start: Optional[str] = None) -> bool:
    path = Path(file_path)
    if not path.exists() or path.name == "index.html":
        return False

    if week_start is None:
        week_start = path.stem

    nav_map = build_nav_context(entries)
    nav = nav_map.get(week_start, {"newer": None, "older": None, "latest": entries[0] if entries else None})

    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    _sanitize_soup_text(soup)
    hero = soup.select_one(".weekly-report-hero")
    sidebar = soup.select_one(".weekly-report-sidebar")
    footer = soup.select_one(".weekly-report-footer")
    if hero is None or sidebar is None or footer is None:
        return False

    _ensure_style(soup)
    _remove_existing_injected_blocks(soup)

    outline_groups = []
    focus_href: Optional[str] = None
    papers_href: Optional[str] = None
    journals_href: Optional[str] = None

    for sec_idx, section in enumerate(soup.select(".weekly-report-section"), 1):
        title_node = section.select_one(".insight-panel-title")
        title_text = _title_plain_text(title_node)
        section_id = section.get("id") or _slugify(title_text, f"section-{sec_idx}")
        section["id"] = section_id
        _ensure_permalink(soup, title_node, section_id)

        if title_text == "交叉研究" and focus_href is None:
            focus_href = f"#{section_id}"
        if title_text == "期刊分布" and journals_href is None:
            journals_href = f"#{section_id}"

        article_links = []
        for art_idx, card in enumerate(section.select(".weekly-paper-card"), 1):
            card_id = card.get("id") or f"{section_id}-paper-{art_idx}"
            card["id"] = card_id
            if papers_href is None:
                papers_href = f"#{card_id}"
            title_h3 = card.select_one(".weekly-paper-title-zh")
            _ensure_permalink(soup, title_h3, card_id)
            _ensure_inline_links(soup, card, card_id, section_id)
            card_title = _title_plain_text(title_h3) or _safe_text(card.get_text(" ", strip=True))
            journal_chip = card.select_one(".weekly-chip-journal")
            journal = _safe_text(journal_chip.get_text(" ", strip=True).replace("📚", "").strip()) if journal_chip else ""
            article_links.append({
                "href": f"#{card_id}",
                "title": card_title,
                "meta": journal,
            })

        outline_groups.append({
            "href": f"#{section_id}",
            "title": title_text or f"章节 {sec_idx}",
            "meta": f"{len(article_links)} 篇" if article_links else "分区",
            "links": article_links,
        })

    top_nav = _build_nav_block(
        soup,
        nav,
        current_start=week_start,
        block_id=TOP_NAV_ID,
        overview_href="#overview",
        focus_href=focus_href,
        papers_href=papers_href,
        journals_href=journals_href,
    )
    hero_actions = hero.select_one(".weekly-hero-actions")
    if hero_actions is not None:
        hero_actions.insert_after(top_nav)
    else:
        hero.append(top_nav)

    sidebar_title = sidebar.select_one(".insight-sidebar-title")
    old_toc = sidebar.select_one(".weekly-toc-list")
    if old_toc is not None:
        old_toc.decompose()

    first_block = None
    for child in list(sidebar.children):
        if isinstance(child, Tag) and child is not sidebar_title:
            first_block = child
            break

    sidebar_nav_block = soup.new_tag("div", id=SIDEBAR_NAV_ID, **{"class": "weekly-sidebar-block"})
    heading = soup.new_tag("div", **{"class": "weekly-sidebar-heading"})
    heading.string = "日期跳转"
    sidebar_nav_block.append(heading)
    sidebar_nav_block.append(
        _build_nav_block(
            soup,
            nav,
            current_start=week_start,
            block_id=f"{SIDEBAR_NAV_ID}-links",
            compact=True,
        )
    )

    outline_block = soup.new_tag("div", id=OUTLINE_ID, **{"class": "weekly-sidebar-block"})
    outline_heading = soup.new_tag("div", **{"class": "weekly-sidebar-heading"})
    outline_heading.string = "单页目录"
    outline_block.append(outline_heading)
    outline_scroll = soup.new_tag("div", **{"class": "weekly-outline-scroll"})

    for group in outline_groups:
        group_wrap = soup.new_tag("div", **{"class": "weekly-outline-group"})
        group_title = soup.new_tag("a", href=group["href"], **{"class": "weekly-outline-group-title"})
        group_title.string = group["title"]
        meta = soup.new_tag("span", **{"class": "weekly-outline-meta"})
        meta.string = group["meta"]
        group_title.append(meta)
        group_wrap.append(group_title)

        if group["links"]:
            link_list = soup.new_tag("div", **{"class": "weekly-outline-list"})
            for link in group["links"]:
                item = soup.new_tag("a", href=link["href"], **{"class": "weekly-outline-link weekly-outline-link-highlight"})
                item.string = link["title"]
                if link["meta"]:
                    meta_node = soup.new_tag("span", **{"class": "weekly-outline-meta"})
                    meta_node.string = link["meta"]
                    item.append(meta_node)
                link_list.append(item)
            group_wrap.append(link_list)
        outline_scroll.append(group_wrap)

    outline_block.append(outline_scroll)

    if first_block is not None:
        first_block.insert_before(sidebar_nav_block)
        first_block.insert_before(outline_block)
    else:
        sidebar.append(sidebar_nav_block)
        sidebar.append(outline_block)

    bottom_nav = _build_nav_block(
        soup,
        nav,
        current_start=week_start,
        block_id=BOTTOM_NAV_ID,
        overview_href="#overview",
        focus_href=focus_href,
        papers_href=papers_href,
        journals_href=journals_href,
    )
    footer.insert_before(bottom_nav)

    path.write_text(str(soup), encoding="utf-8")
    return True



def enhance_weekly_archive(index_path: str | Path = "docs/weekly/index.json") -> int:
    entries = load_weekly_entries(index_path)
    weekly_dir = Path(index_path).parent
    changed = 0
    for entry in entries:
        file_path = weekly_dir / (entry.get("file") or f"{entry.get('week_start')}.html")
        if enhance_weekly_html_file(file_path, entries, week_start=entry.get("week_start")):
            changed += 1
    return changed


if __name__ == "__main__":
    count = enhance_weekly_archive("docs/weekly/index.json")
    print(f"enhanced {count} weekly page(s)")
