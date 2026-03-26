#!/usr/bin/env python3
"""Static sanity checks for archive/home entry navigation markup."""

from pathlib import Path


def main() -> int:
    daily = Path('docs/daily/index.html').read_text(encoding='utf-8')
    weekly = Path('docs/weekly/index.html').read_text(encoding='utf-8')
    home = Path('docs/index.html').read_text(encoding='utf-8')

    assert 'id="dailyArchiveTopNav"' in daily
    assert 'id="dailyArchiveOutline"' in daily
    assert 'insight-entry-scroll' in daily
    assert '前一天' in daily
    assert '页内定位' in daily

    assert 'id="weeklyArchiveTopNav"' in weekly
    assert 'id="weeklyArchiveOutline"' in weekly
    assert 'insight-entry-scroll' in weekly
    assert '前一周' in weekly
    assert '页内定位' in weekly

    assert 'id="homeInsightTopNav"' in home
    assert 'id="homeInsightOutline"' in home
    assert 'id="homeDailyCard"' in home
    assert 'id="homeWeeklyCard"' in home
    assert 'id="homeQuickArchiveSection"' in home
    assert 'renderHomeNav' in home
    assert '#summary' in home
    assert '#cross' in home

    print('[OK] archive/home navigation markup sanity checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
