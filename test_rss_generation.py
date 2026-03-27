#!/usr/bin/env python3
"""Deterministic sanity tests for global and daily RSS generation."""

from pathlib import Path
from tempfile import TemporaryDirectory

from rss_generator import SITE_URL, generate_daily_rss_feed, generate_rss_feed


SAMPLE_ARTICLES = [
    {
        'title_zh': '测试中文标题',
        'title': 'Test English Title',
        'link': 'https://example.com/paper',
        'journal': 'arXiv',
        'authors': ['Alice', 'Bob'],
        'summary': '一段用于 RSS 的中文摘要。',
        'pub_date': '2026-03-27',
    },
    {
        'title': 'Second Paper',
        'link': 'https://example.com/paper2',
        'journal': 'Nature Materials',
        'authors': list('Carol Smith, David Lee'),
        'abstract': 'English abstract for RSS testing.',
        'pub_date': '2026-03-26',
    },
]


def main() -> int:
    with TemporaryDirectory() as tmpdir:
        root_feed = Path(tmpdir) / 'docs' / 'feed.xml'
        daily_feed = Path(tmpdir) / 'docs' / 'daily' / '2026-03-27.xml'

        assert generate_rss_feed(SAMPLE_ARTICLES, output_path=str(root_feed))
        assert generate_daily_rss_feed('2026-03-27', SAMPLE_ARTICLES[:1], output_path=str(daily_feed))

        root_xml = root_feed.read_text(encoding='utf-8')
        daily_xml = daily_feed.read_text(encoding='utf-8')

        assert SITE_URL in root_xml
        assert '<title>文献追踪系统</title>' in root_xml
        assert 'Alice, Bob' in root_xml
        assert 'Carol Smith, David Lee' in root_xml
        assert '一段用于 RSS 的中文摘要。' in root_xml
        assert f'{SITE_URL}/daily/2026-03-27.xml' in daily_xml
        assert f'{SITE_URL}/daily/2026-03-27.html' in daily_xml
        assert '2026-03-27 AI × Science 文献日报 RSS' in daily_xml
        assert '📚 arXiv' in daily_xml

    print('[OK] rss generation sanity checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
