# 每日摘要筛选流程说明

日报只统计**单日**文献，按「北京时间的日历日」统一口径，避免 Actions（UTC）与统计日期时差导致漏筛或多筛。每一篇文献都会参与筛选，逐篇按 `pub_date` 判断是否属于当日。

**Actions 与报告日**：定时抓取在 **UTC 0:00、12:00**（北京时间 08:00、20:00）运行。main.py 调用日报时**固定传入「北京时间昨天」**作为报告日，这样得到的是**前一天完整一天**的文献总结，而不是「今天」（当天数据不全）。

---

## 一、时区与日期约定

| 环节 | 约定 |
|------|------|
| **RSS 解析**（`rss_fetcher._parse_date`） | 将 feed 的发布时间（多为 UTC）转为**北京时间**，再取日历日 `YYYY-MM-DD` 写入 `pub_date`。无时区信息时按 UTC 再转北京。 |
| **报告日**（`generate_daily_summary` 的 `date`） | 未传 `date` 时取「**北京时间今天**」作为 `report_date`，与 `pub_date` 口径一致。 |
| **Actions 运行** | 跑在 UTC；通过上述统一为「北京时间的日历日」，不依赖运行时刻的 UTC 日期。 |

---

## 二、每日筛选流程（逐篇筛选）

1. **确定报告日 `report_date`**
   - 若调用时传入 `date`（`YYYY-MM-DD`），则 `report_date = date`。
   - 若未传，则 `report_date = 北京时间今天的 YYYY-MM-DD`。
   - **main.py 定时跑时**：始终传入 `date = 北京时间昨天`，故报告日为前一天，保证总结完整一天。

2. **数据来源**
   - 文献列表来自**刚更新后的** `data/index.json`（main.py 中在 `generate_index_json()` 之后读取，保证含本次新抓取的文章）。

3. **逐篇筛选**
   - 对 `articles` 中**每一篇**：
     - 取 `pub_date` 的日期部分：`_date_part(pub_date)` → `YYYY-MM-DD`（前 10 位，支持带空格或 ISO 格式）。
     - 若 `_date_part(pub_date) == report_date` → **保留**，加入当日列表。
     - 否则 → **丢弃**。
   - 可选：`verbose_filter=True` 时逐篇打印「保留」或「跳过」及原因。

4. **后续**
   - 得到当日文献列表后，交给 AI 生成摘要（最多取前 80 篇送审），再保存为 `docs/daily/{report_date}.html`。

---

## 三、相关代码位置

- **RSS 日期解析**：`rss_fetcher.py` → `_parse_date()`（统一为北京时间日历日）。
- **报告日与逐篇筛选**：`ai_summarizer.py` → `_daily_report_date()`、`_date_part()`、`generate_daily_summary()` 中的 for 循环。
- **数据源**：`main.py` 中 RSS 与日报均从 `data/index.json` 读取（非 `docs/data/index.json`）。

---

## 四、排查建议

- 若某天篇数异常少：先看 `pub_date` 是否均为北京时间日历日（rss_fetcher 是否已统一）；再确认 Actions 运行时「北京时间今天」与预期是否一致（可打 `report_date` 日志）。
- 本地调试：`python ai_summarizer.py 2026-01-30 --verbose` 使用指定日期并逐篇打印筛选结果。
