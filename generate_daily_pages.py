#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate daily summary pages for GitHub Pages.

- Input (preferred): data/index.json (keyword-filtered global index)
  - Fallback: data/ai_relevant.json (created by run_optimized_sync)
- Output:
  - docs/daily/YYYY-MM-DD.html
  - docs/daily/summaries.json
"""
import os
import json
import html
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import hashlib

from ai_summarizer import AISummarizer


def beijing_today() -> str:
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).strftime('%Y-%m-%d')

def beijing_yesterday() -> str:
    tz = timezone(timedelta(hours=8))
    return (datetime.now(tz) - timedelta(days=1)).strftime('%Y-%m-%d')


def safe_text(value: str) -> str:
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def safe_url(value: str) -> str:
    url = (value or "").strip()
    if not url:
        return "#"
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return "#"
    except Exception:
        return "#"
    return html.escape(url, quote=True)

def format_authors(authors) -> str:
    if not authors:
        return ""
    if isinstance(authors, list):
        names = [str(a).replace("\n", " ").strip() for a in authors if str(a).strip()]
        if len(names) <= 6:
            return ", ".join(names)
        return ", ".join(names[:6]) + f" 等{len(names)}位作者"
    return str(authors).replace("\n", " ").strip()

def arxiv_badge(item: Dict) -> str:
    """Return a readable arXiv category badge from item fields."""
    journal = (item.get("journal") or "").strip()
    if journal.lower() != "arxiv":
        return ""
    cat = (item.get("arxiv_category") or "").strip()
    if not cat:
        # fallback: infer from source_url
        src = (item.get("source_url") or "").strip()
        marker = "/rss/"
        if marker in src:
            cat = src.split(marker, 1)[1].strip()
    if not cat:
        return ""
    return cat

def load_relevant(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def load_index_articles(path: str = "data/index.json") -> List[Dict]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        return data.get("articles", []) or []
    except Exception:
        return []


def ensure_dirs():
    os.makedirs('docs/daily', exist_ok=True)

def digest_links(articles: List[Dict]) -> str:
    links = sorted({(a.get("link") or "").strip() for a in articles if (a.get("link") or "").strip()})
    raw = "\n".join(links).encode("utf-8")
    return hashlib.md5(raw).hexdigest()

def format_date_display(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y/%m/%d")
    except Exception:
        return date_str

def count_unique_journals(items: List[Dict]) -> int:
    journals = {
        (item.get("journal") or "").strip().lower()
        for item in items
        if (item.get("journal") or "").strip()
    }
    return len(journals)

def count_arxiv_items(items: List[Dict]) -> int:
    return sum(1 for item in items if (item.get("journal") or "").strip().lower() == "arxiv")

def build_daily_tags(items: List[Dict]) -> List[str]:
    tags = ["AI", "物理", "化学", "材料", "交叉学科"]
    if any((item.get("journal") or "").strip().lower() == "arxiv" for item in items):
        tags.append("arXiv")
    if any(arxiv_badge(item) for item in items):
        tags.append("预印本追踪")
    return tags[:7]

def build_highlight_reason(item: Dict) -> str:
    reason = str(item.get("reason") or "").strip()
    if reason:
        return reason

    ai_score = item.get("ai_score")
    if ai_score is not None and str(ai_score).strip() != "":
        return f"AI相关度 {ai_score}"

    arxiv_cat = arxiv_badge(item)
    if arxiv_cat:
        return f"arXiv / {arxiv_cat}"

    journal = str(item.get("journal") or "").strip()
    if journal:
        return journal

    return "交叉重点"

def collect_focus_highlights(summary: Dict, items: List[Dict], limit: int = 8) -> List[Dict]:
    selected: List[Dict] = []
    seen = set()

    def add(item: Dict):
        if not isinstance(item, dict):
            return
        key = (item.get("link") or item.get("title_en") or item.get("title_zh") or "").strip()
        if not key or key in seen:
            return
        selected.append(item)
        seen.add(key)

    for group_name in ("ml_highlights", "ferro_highlights"):
        for item in summary.get(group_name, []) or []:
            add(item)
            if len(selected) >= limit:
                return selected[:limit]

    def score_key(item: Dict):
        try:
            return float(item.get("ai_score"))
        except Exception:
            return -1.0

    ranked = sorted(items, key=score_key, reverse=True)
    for item in ranked:
        add(item)
        if len(selected) >= limit:
            return selected[:limit]

    for item in items:
        add(item)
        if len(selected) >= limit:
            return selected[:limit]

    return selected[:limit]

def render_daily_html(date_str: str, summary: Dict) -> str:
    items = summary.get("full_list") or summary.get("summaries") or []
    highlight_items = collect_focus_highlights(summary, items)
    tag_list = build_daily_tags(items)
    display_date = format_date_display(date_str)
    journal_count = count_unique_journals(items)
    arxiv_count = count_arxiv_items(items)

    def render_meta_chips(item: Dict) -> str:
        journal = safe_text(item.get("journal", ""))
        arxiv_cat = safe_text(arxiv_badge(item))
        authors = safe_text(format_authors(item.get("authors")))
        ai_score = item.get("ai_score")
        meta_parts = []
        if journal:
            if arxiv_cat:
                meta_parts.append(f"<span class='daily-chip daily-chip-journal'>📖 {journal} / {arxiv_cat}</span>")
            else:
                meta_parts.append(f"<span class='daily-chip daily-chip-journal'>📖 {journal}</span>")
        if authors:
            meta_parts.append(f"<span class='daily-chip daily-chip-authors'>👤 {authors}</span>")
        if ai_score is not None and str(ai_score).strip() != "":
            meta_parts.append(f"<span class='daily-chip daily-chip-score'>🔥 AI {safe_text(ai_score)}</span>")
        return "".join(meta_parts)

    def render_focus_item(item: Dict, index: int) -> str:
        meta_html = render_meta_chips(item)
        reason = safe_text(build_highlight_reason(item))
        return f"""
        <li class=\"daily-news-item\">
            <div class=\"daily-news-index\">{index:02d}</div>
            <div class=\"daily-news-body\">
                <div class=\"daily-news-title-zh\">{safe_text(item.get('title_zh',''))}</div>
                <div class=\"daily-news-title-en\">{safe_text(item.get('title_en',''))}</div>
                <div class=\"daily-news-meta\">{meta_html}</div>
                <p class=\"daily-news-summary\">{safe_text(item.get('summary',''))}</p>
                <p class=\"daily-news-reason\"><strong>关注理由：</strong>{reason}</p>
                <a class=\"daily-news-link\" href=\"{safe_url(item.get('link',''))}\" target=\"_blank\" rel=\"noopener noreferrer\">查看原文 ↗</a>
            </div>
        </li>
        """

    def render_item(item: Dict, index: int) -> str:
        meta_html = render_meta_chips(item)
        return f"""
        <li class=\"daily-paper-card\" id=\"paper-{index}\">
            <div class=\"daily-paper-head\">
                <span class=\"daily-paper-number\">{index:02d}</span>
                <div class=\"daily-paper-titles\">
                    <div class=\"daily-paper-title-zh\">{safe_text(item.get('title_zh',''))}</div>
                    <div class=\"daily-paper-title-en\">{safe_text(item.get('title_en',''))}</div>
                </div>
            </div>
            <div class=\"daily-paper-meta\">{meta_html}</div>
            <div class=\"daily-paper-summary\">{safe_text(item.get('summary',''))}</div>
            <div class=\"daily-paper-actions\">
                <a class=\"daily-news-link\" href=\"{safe_url(item.get('link',''))}\" target=\"_blank\" rel=\"noopener noreferrer\">阅读原文 ↗</a>
            </div>
        </li>
        """

    focus_html = "".join(render_focus_item(item, idx) for idx, item in enumerate(highlight_items, 1))
    items_html = "".join(render_item(item, idx) for idx, item in enumerate(items, 1))

    overview = safe_text(summary.get('overview', ''))
    trends = safe_text(summary.get('trends', ''))
    tags_html = "".join(f"<span class=\"daily-tag\">{safe_text(tag)}</span>" for tag in tag_list)

    return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{date_str} 文献日报 - 文献追踪系统</title>
  <link rel=\"stylesheet\" href=\"../style.css\" />
	  <style>
	    body {{ background: linear-gradient(180deg, rgba(99, 102, 241, 0.08) 0%, rgba(248, 250, 252, 0.85) 220px), var(--bg-primary); }}
	    .daily-shell {{ max-width: 1260px; margin: 0 auto; padding: 28px 20px 48px; }}
	    .daily-topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }}
	    .daily-topbar-left, .daily-topbar-right {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
	    .back-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--accent-primary); text-decoration: none; font-weight: 600; }}
	    .back-link:hover {{ color: var(--accent-hover); }}
	    .daily-mini-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; background: rgba(255,255,255,0.75); border: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.92rem; backdrop-filter: blur(8px); }}
	    .daily-layout {{ display: grid; grid-template-columns: minmax(0, 1fr) 260px; gap: 24px; align-items: start; }}
	    .daily-article {{ background: rgba(255,255,255,0.76); border: 1px solid rgba(148,163,184,0.28); border-radius: 28px; box-shadow: var(--shadow-lg); backdrop-filter: blur(14px); padding: 32px; }}
	    .daily-hero {{ padding-bottom: 18px; border-bottom: 1px solid var(--border-color); }}
	    .daily-kicker {{ display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; background: rgba(99,102,241,0.12); color: var(--accent-primary); font-weight: 700; letter-spacing: 0.04em; }}
	    .daily-title {{ margin: 18px 0 10px; font-size: clamp(2rem, 4vw, 3rem); line-height: 1.15; letter-spacing: -0.03em; }}
	    .daily-subtitle {{ font-size: 1.02rem; color: var(--text-secondary); margin-bottom: 18px; }}
	    .daily-quote {{ margin: 0; padding: 16px 18px; border-left: 4px solid var(--accent-primary); border-radius: 16px; background: rgba(99,102,241,0.08); color: var(--text-secondary); font-size: 1rem; }}
	    .daily-tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 18px 0 22px; }}
	    .daily-tag {{ display: inline-flex; align-items: center; padding: 7px 13px; border-radius: 999px; background: rgba(255,255,255,0.92); border: 1px solid var(--border-color); color: var(--text-secondary); font-size: 0.92rem; }}
	    .daily-stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
	    .daily-stat {{ padding: 18px; border-radius: 18px; background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,250,252,0.92)); border: 1px solid var(--border-color); }}
	    .daily-stat-label {{ color: var(--text-muted); font-size: 0.92rem; margin-bottom: 6px; }}
	    .daily-stat-value {{ font-size: 1.8rem; font-weight: 800; letter-spacing: -0.03em; }}
	    .daily-section {{ margin-top: 28px; }}
	    .daily-section-head {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
	    .daily-section-index {{ font-size: 0.92rem; font-weight: 800; color: var(--accent-primary); padding: 5px 10px; border-radius: 999px; background: rgba(99,102,241,0.1); }}
	    .daily-section-title {{ font-size: 1.45rem; letter-spacing: -0.02em; }}
	    .daily-summary-card {{ padding: 18px 20px; border-radius: 20px; background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(244,247,255,0.96)); border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); }}
	    .daily-summary-card p + p {{ margin-top: 12px; }}
	    .daily-news-list, .daily-paper-list {{ list-style: none; margin: 0; padding: 0; }}
	    .daily-news-item, .daily-paper-card {{ display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 16px; padding: 20px; border-radius: 22px; background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(249,250,251,0.92)); border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); }}
	    .daily-news-item + .daily-news-item, .daily-paper-card + .daily-paper-card {{ margin-top: 16px; }}
	    .daily-news-index, .daily-paper-number {{ width: 42px; height: 42px; display: inline-flex; align-items: center; justify-content: center; border-radius: 14px; font-weight: 800; color: white; background: var(--gradient-accent); box-shadow: var(--shadow-sm); flex-shrink: 0; }}
	    .daily-news-title-zh, .daily-paper-title-zh {{ font-size: 1.12rem; font-weight: 700; line-height: 1.5; margin-bottom: 6px; }}
	    .daily-news-title-en, .daily-paper-title-en {{ color: var(--text-secondary); font-size: 0.96rem; line-height: 1.6; }}
	    .daily-news-meta, .daily-paper-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }}
	    .daily-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 999px; font-size: 0.88rem; color: var(--text-secondary); background: rgba(99,102,241,0.08); }}
	    .daily-chip-authors {{ background: rgba(16,185,129,0.08); }}
	    .daily-chip-score {{ background: rgba(245,158,11,0.12); }}
	    .daily-news-summary, .daily-paper-summary {{ color: var(--text-primary); line-height: 1.8; }}
	    .daily-news-reason {{ margin-top: 10px; color: var(--text-secondary); }}
	    .daily-paper-actions, .daily-news-link {{ margin-top: 14px; }}
	    .daily-news-link {{ display: inline-flex; align-items: center; gap: 6px; color: var(--accent-primary); text-decoration: none; font-weight: 600; }}
	    .daily-news-link:hover {{ color: var(--accent-hover); }}
	    .daily-paper-head {{ display: flex; gap: 16px; align-items: flex-start; }}
	    .daily-paper-titles {{ min-width: 0; }}
	    .daily-toc {{ position: sticky; top: 24px; }}
	    .daily-toc-card {{ padding: 18px; border-radius: 20px; background: rgba(255,255,255,0.78); border: 1px solid var(--border-color); box-shadow: var(--shadow-md); backdrop-filter: blur(12px); }}
	    .daily-toc-title {{ font-size: 0.95rem; font-weight: 800; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px; }}
	    .daily-toc a {{ display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 14px; color: var(--text-secondary); text-decoration: none; }}
	    .daily-toc a:hover {{ background: rgba(99,102,241,0.08); color: var(--accent-primary); }}
	    .daily-footer {{ margin-top: 28px; padding-top: 18px; border-top: 1px solid var(--border-color); color: var(--text-muted); font-size: 0.94rem; }}
	    @media (max-width: 980px) {{
	      .daily-layout {{ grid-template-columns: 1fr; }}
	      .daily-toc {{ position: static; order: -1; }}
	    }}
	    @media (max-width: 720px) {{
	      .daily-shell {{ padding: 16px 12px 36px; }}
	      .daily-article {{ padding: 22px 16px; border-radius: 22px; }}
	      .daily-stats {{ grid-template-columns: 1fr; }}
	      .daily-news-item, .daily-paper-card {{ grid-template-columns: 1fr; }}
	      .daily-news-index, .daily-paper-number {{ width: 38px; height: 38px; }}
	      .daily-paper-head {{ flex-direction: column; gap: 12px; }}
	    }}
	  </style>
</head>
<body>
  <div class=\"daily-shell\">
    <div class=\"daily-topbar\">
      <div class=\"daily-topbar-left\">
        <a href=\"../index.html\" class=\"back-link\">← 返回主页</a>
        <span class=\"daily-mini-chip\">AI × Science Daily</span>
      </div>
      <div class=\"daily-topbar-right\">
        <span class=\"daily-mini-chip\">{safe_text(date_str)}</span>
      </div>
    </div>
    <div class=\"daily-layout\">
      <article class=\"daily-article\">
        <header class=\"daily-hero\">
          <div class=\"daily-kicker\">AI 文献日报</div>
          <h1 class=\"daily-title\">AI × Science 文献日报 {display_date}</h1>
          <p class=\"daily-subtitle\">参考 CloudFlare-AI-Insight-Daily 的资讯版式，重构为更适合 AI × 物理 / 化学 / 材料交叉文献阅读的日报页面。</p>
          <blockquote class=\"daily-quote\">{' | '.join(safe_text(tag) for tag in tag_list)}</blockquote>
          <div class=\"daily-tags\">{tags_html}</div>
          <div class=\"daily-stats\">
            <div class=\"daily-stat\">
              <div class=\"daily-stat-label\">收录文献</div>
              <div class=\"daily-stat-value\">{len(items)}</div>
            </div>
            <div class=\"daily-stat\">
              <div class=\"daily-stat-label\">期刊 / 来源</div>
              <div class=\"daily-stat-value\">{journal_count}</div>
            </div>
            <div class=\"daily-stat\">
              <div class=\"daily-stat-label\">arXiv 相关</div>
              <div class=\"daily-stat-value\">{arxiv_count}</div>
            </div>
          </div>
        </header>

        <section id=\"summary\" class=\"daily-section\">
          <div class=\"daily-section-head\">
            <span class=\"daily-section-index\">01</span>
            <h2 class=\"daily-section-title\">今日摘要</h2>
          </div>
          <div class=\"daily-summary-card\">
            <p><strong>总览：</strong>{overview}</p>
            <p><strong>热点：</strong>{trends}</p>
          </div>
        </section>

        <section id=\"highlights\" class=\"daily-section\">
          <div class=\"daily-section-head\">
            <span class=\"daily-section-index\">02</span>
            <h2 class=\"daily-section-title\">交叉重点</h2>
          </div>
          {f'<ol class=\"daily-news-list\">{focus_html}</ol>' if focus_html else '<div class=\"daily-summary-card\"><p>暂无重点论文。</p></div>'}
        </section>

        <section id=\"papers\" class=\"daily-section\">
          <div class=\"daily-section-head\">
            <span class=\"daily-section-index\">03</span>
            <h2 class=\"daily-section-title\">完整速览</h2>
          </div>
          {f'<ol class=\"daily-paper-list\">{items_html}</ol>' if items_html else '<div class=\"daily-summary-card\"><p>今日无文献。</p></div>'}
        </section>

        <div class=\"daily-footer\">
          本页由文献追踪系统自动生成，保留中英标题、期刊、作者与摘要信息，便于快速筛选与深度阅读。
        </div>
      </article>

      <aside class=\"daily-toc\">
        <div class=\"daily-toc-card\">
          <div class=\"daily-toc-title\">目录</div>
          <a href=\"#summary\"><span>今日摘要</span><span>01</span></a>
          <a href=\"#highlights\"><span>交叉重点</span><span>02</span></a>
          <a href=\"#papers\"><span>完整速览</span><span>03</span></a>
        </div>
      </aside>
    </div>
  </div>
</body>
</html>
"""


def update_index(date_str: str, total: int):
    index_path = os.path.join('docs/daily', 'summaries.json')
    data = {"summaries": []}
    if os.path.exists(index_path):
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {"summaries": []}
    summaries = [s for s in data.get('summaries', []) if s.get('date') != date_str]
    summaries.insert(0, {"date": date_str, "file": f"{date_str}.html", "total": total})
    data["summaries"] = summaries[:120]
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_summary_index() -> Dict:
    index_path = os.path.join("docs/daily", "summaries.json")
    if not os.path.exists(index_path):
        return {"summaries": []}
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f) or {"summaries": []}
    except Exception:
        return {"summaries": []}

def save_summary_index(summaries: List[Dict]):
    index_path = os.path.join("docs/daily", "summaries.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"summaries": summaries}, f, ensure_ascii=False, indent=2)

def preserve_existing_entry(prev: Dict, date_str: str) -> Dict:
    preserved = dict(prev or {})
    preserved["date"] = date_str
    preserved["file"] = preserved.get("file") or f"{date_str}.html"
    if "total" not in preserved:
        preserved["total"] = 0
    return preserved

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=None, help='YYYY-MM-DD (Beijing). 默认使用北京时间昨天以保证日报完整。')
    parser.add_argument('--days', default="1", help='生成最近 N 天（包含 --date 指定的日期）。用于补回漏抓/晚到数据。')
    parser.add_argument('--force', action='store_true', help='强制重新生成（忽略 summaries.json 中的 digest/total 缓存）。')
    args = parser.parse_args()

    # 默认生成“北京时间昨天”的日报：与 Actions 的抓取频率 (08:00/20:00) 匹配，避免当天数据不全导致“摘要缺失/为0”。
    date_str = args.date or beijing_yesterday()
    try:
        days = max(1, int(str(args.days).strip()))
    except Exception:
        days = 1

    ensure_dirs()

    # Prefer full daily list from index.json, but always union with ai_relevant.json
    # to avoid omitting focus-relevant papers.
    index_articles = load_index_articles("data/index.json")
    relevant_articles = load_relevant("data/ai_relevant.json")

    existing_index = load_summary_index()
    existing_items = existing_index.get("summaries", []) or []
    existing_by_date = {s.get("date"): s for s in existing_items if isinstance(s, dict) and s.get("date")}

    new_entries: List[Dict] = []
    api_key = os.environ.get('AI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    provider = os.environ.get('AI_PROVIDER') or 'openrouter'
    summarizer = AISummarizer(provider, api_key) if api_key else None

    base_dt = datetime.strptime(date_str, "%Y-%m-%d")
    # Generate newest -> oldest to keep logs intuitive.
    for i in range(days):
        day_dt = base_dt - timedelta(days=i)
        day_str = day_dt.strftime("%Y-%m-%d")

        relevant_day = [a for a in relevant_articles if (a.get("pub_date") or "").startswith(day_str)]
        relevant_links = {a.get("link") for a in relevant_day if a.get("link")}

        index_day = [
            a for a in index_articles
            if (a.get("pub_date") or "").startswith(day_str) and (a.get("link") not in relevant_links)
        ]

        # Relevant first
        day_articles = relevant_day + index_day

        total = len(day_articles)
        digest = digest_links(day_articles) if day_articles else ""

        out_path = os.path.join("docs/daily", f"{day_str}.html")
        prev = existing_by_date.get(day_str) or {}
        prev_digest = str(prev.get("digest") or "")
        prev_total = prev.get("total")

        should_skip = (
            (not args.force)
            and os.path.exists(out_path)
            and prev_digest
            and prev_digest == digest
            and isinstance(prev_total, int)
            and prev_total == total
        )

        if should_skip:
            print(f"⏭️  Skip daily page (unchanged): {out_path}")
            new_entries.append({"date": day_str, "file": f"{day_str}.html", "total": total, "digest": digest})
        else:
            try:
                if not day_articles:
                    # still generate empty page so index shows date
                    summary = {"date": day_str, "total": 0, "overview": "今日无文献", "trends": "", "summaries": []}
                else:
                    if summarizer is None:
                        raise ValueError("AI_API_KEY is empty; cannot generate daily summary")
                    summary = summarizer.generate_daily_summary(day_articles, day_str)

                page_html = render_daily_html(day_str, summary)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(page_html)
                print(f"✅ Daily page generated: {out_path}")
                new_entries.append({"date": day_str, "file": f"{day_str}.html", "total": total, "digest": digest})
            except Exception as exc:
                has_existing_page = os.path.exists(out_path)
                if has_existing_page:
                    print(f"⚠️ Daily page generation failed for {day_str}, preserving existing page: {exc}")
                    new_entries.append(preserve_existing_entry(prev, day_str))
                else:
                    print(f"⚠️ Daily page generation failed for {day_str}, skipping this date for now: {exc}")

    # Merge index entries: update our generated dates, keep others, then sort by date desc.
    updated_dates = {e.get("date") for e in new_entries if e.get("date")}
    merged = [e for e in existing_items if e.get("date") not in updated_dates]
    merged.extend(new_entries)
    merged = [e for e in merged if isinstance(e, dict) and e.get("date")]
    merged.sort(key=lambda x: x.get("date") or "", reverse=True)
    save_summary_index(merged[:120])


if __name__ == '__main__':
    main()
