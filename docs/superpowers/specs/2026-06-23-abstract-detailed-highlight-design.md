# 日报/周报每篇增加「摘要中文 + 详细亮点」设计

- 日期:2026-06-23
- 状态:已批准,待写实现计划

## 背景与问题

当前日报每篇文章只显示一条"💡 亮点"。亮点取值优先级是
`summary`(AI 生成的 `one_sentence_summary`,**≤40 字**)→ `abstract_zh` → ...。
也就是说 `abstract_zh`(中文摘要)字段其实已在生成,但在日报里只是"亮点为空时的兜底",
平时根本不出现。用户只能看到标题 + 一句话,信息量太少,无法判断文章在讲什么。

周报:**核心关注**文章已显示"📄 摘要"+ 方法要点/相关工作/启示;
但**普通文章卡**把中文摘要折叠在"📖 查看完整摘要"按钮后,默认只露一句 `ai_analysis`。

## 目标

每篇文章(日报、周报)都显式展示两段:
1. **摘要中文**:加长版中文概括(≤200 字),让用户知道文章讲什么。
2. **详细亮点**:一小段 2~3 句(≤100 字),核心创新点 + 最强结论 + 对方向的意义。

## 用户已确认的决策

- 摘要形态:**加长版中文概括(≤200 字)**,非忠实全文翻译(多数 Nature RSS 只有 DOI 行,无真实摘要可逐句翻译)。
- 亮点详略:**一段 2~3 句(≤100 字)**。
- 生效范围:**以后生效 + 回填最近一段(约 14 天日报、最近 2 周周报)**。

## 方案

### A. AI 生成层(`ai_summarizer.py`)

`_build_prompt()`:
- `abstract_zh`:`≤120 字` → **`≤200 字`**,继续要求写出"体系/方法/关键数值或结论"至少一项,
  保留"禁止套话"硬规则('本研究/取得进展/具有重要意义/为…提供新思路/点击查看' 等)。
- `one_sentence_summary`:由"一句话 ≤40 字" → **"一小段 2~3 句、≤100 字"**:核心创新点 +
  最强结论 + 对凝聚态 / AI for science 方向的意义。**字段名保持不变**,只改写作要求,不牵动下游。
- 喂给 AI 的原文摘要由 `abstract[:300]` 放宽到 **`abstract[:600]`**(否则没素材写不出 200 字)。
  `_build_missing_summaries_prompt()` 的 `[:300]` 同步放宽到 `[:600]`。
- 更新 `example_block`,示范更长的 `abstract_zh` 与 2-3 句 `one_sentence_summary`。
- 更新 `【输出格式】` 内联注释里的字数提示,保持与硬性要求一致。

`_parse_response()`:
- `one_sentence` 截断 `_clamp_text(..., 80)` → **`120`**(放行 ≤100 字,留余量)。
- `abstract_zh` 截断维持 `240`(200 字够用)。
- highlights 段(line ~953-957)的同名 clamp 同步:`one_sentence` 80→120,`abstract_zh` 维持 240。

### B. 渲染层

**日报** `generate_daily_pages.py: render_unified_item()`:
- 新增"📄 摘要"块,显示 `abstract_zh`(有才显示)。
- "💡 亮点"块改为只取 `summary`(去掉对 `abstract_zh` / `one_sentence_summary` 的兜底,
  避免与摘要块重复内容)。
- 顺序:摘要在上,亮点在下(对应用户"亮点里首先要有摘要翻译内容"的诉求)。

`docs/daily-common.css`:
- 新增 `.daily-paper-abstract` 样式,与现有 `.daily-paper-highlight` 协调。
- **必须** bump `docs/sw.js` 的 `CACHE_NAME`(`v5`→`v6`)及引用 `daily-common.css` 处的缓存键,
  并按既有约定更新相关 `?v=`(见仓库不变量:SW 相对路径 + 改前端 bump 版本)。

**周报** `weekly_summary.py`:
- 核心区 `render_core_weekly_section`:已显示"📄 摘要",自动受益于更长 `abstract_zh`,不改逻辑。
- 普通文章卡 `render_article_cards()`(line ~1461):把中文摘要从折叠块改为**默认可见**
  (展示 `abstract_zh`);`ai_analysis`(已 50-80 字)作为详细解读保留在摘要上方。
  "查看完整摘要"toggle 可保留用于展示英文原文/超长摘要,但中文摘要不再默认隐藏。

### C. 回填层(无需新代码,操作步骤)

合并后手动触发现成 workflow(本环境无 gh CLI,经 git-credential token + REST API):
- `backfill-daily.yml`:`days=14`、`force=true`(→ `generate_daily_pages.py --days 14 --force`,重跑 AI)。
- `backfill-weekly.yml`:最近 2 周。

## 测试

- `test_ai_summarizer*`(若本地缺依赖则 CI 跑):断言 prompt 含新字数要求(≤200 字 / 2~3 句),
  且 `_clamp_text` 阈值 ≥ 新上限(one_sentence ≥120)。可用纯字符串断言,不需真实 API。
- `test_daily_pages_render.py`:构造含 `abstract_zh` + `summary` 的 item,断言渲染出
  `📄 摘要` 块与 `💡 亮点` 块,且两者文本不相互兜底重复;`abstract_zh` 为空时不出现摘要块。
- 周报渲染测试(本地缺 bs4 跳过,CI 跑):断言普通卡的中文摘要默认可见(不在仅 toggle 后)。
- `test_docs_assets.py`:`daily-common.css` 新增类不破坏现有断言;若 bump 了 sw 版本,确认预缓存仍相对路径且文件存在。
- 全量 `python run_tests.py` + 9 个脚本式 main() 测试(见本仓库测试约定)。

## 成本与边界(诚实说明)

- 每篇输出 token 约翻倍(摘要 120→200、亮点 40→100、输入 300→600)。用户已确认接受。
  日报每天上百篇,单次回填 14 天 = 十几次 AI 批量调用。
- 无真实摘要的来源(多数 Nature RSS 仅 DOI 行):AI 据标题概括,可能偏薄;
  摘要块"空则不显示",不出现占位垃圾。
- **不动**:数据写回 `data/index.json` 的链路、`focus_core` 判定与计分、深析正文与信息图、
  `docs/data` 不入库等既有不变量。
