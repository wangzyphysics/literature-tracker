# Design: 日报/周报以"ML × ferro/凝聚态"为核心的深度优化

> 作者：Claude (Opus 4.6) + 于宏宇
> 日期：2026-04-15
> 状态：待实现

## Context

当前 `literature-tracker` 的日报/周报对"所有 AI × 物理/化学/材料"相关论文一视同仁地展示。用户（于宏宇）真正关心的是更窄的交叉：**机器学习 × 凝聚态/铁电/磁性方向**（关键词：ferro, machine, learn, magne, neural, network, potential, hamiltonian）。现状下这类论文被埋在通用"交叉重点"和主题分组中，用户需要自行筛选，时间成本高。

本次优化目标：让"你的方向"在日报/周报里**一眼可见、信息密度最高**，同时保留现有的通用面向作为外围参考。

非目标：不改 RSS 抓取、去重、翻译、email/wechat 通知；不引入新依赖。

---

## 架构总览

```
┌─ focus_core.py (新) ─────────────────────────────┐
│  - is_core_focus(item) -> bool                   │
│  - core_score(item) -> float ∈ [0,1]             │
│  - core_priority(item) -> tuple                  │
└───────────────────┬──────────────────────────────┘
                    │ 纯函数，无依赖 AI
          ┌─────────┴─────────┐
          ▼                   ▼
 ai_summarizer.py     weekly_summary.py
  + _generate_core_    + _generate_core_weekly(
    deep_fields(          core_items)
    core_items)
  (Kimi 一次批量)       (Kimi 一次批量)
          │                   │
          ▼                   ▼
 generate_daily_pages  render_weekly_html
  + render_core_        + render_core_weekly_
    section()             section()
```

所有 LLM 调用复用现有 `KimiClaudeCodeProvider` + `_load_json_lenient`；所有排序复用 `focus_priority` 的 tuple-key 模式。

---

## § 1. 核心关注判定（`focus_core.py`）

### 接口

```python
def is_core_focus(item: Mapping) -> bool
def core_score(item: Mapping) -> float   # 0.0 ~ 1.0，用于排序/tier 划分
def core_priority(item: Mapping) -> tuple  # 返回 sort key
```

**纯函数**，只读 `item['title']`、`item['abstract']`、`item['title_zh']`、`item['abstract_zh']`、`item['journal']`、`item['source_url']`。

### 判定规则

必须同时命中**两侧**才返回 `True`：

**AI / 方法侧**（`METHOD_SET`）：
```
AI_TERMS 现有项（machine learning / neural network / gnn / transformer / diffusion /
 graph neural / equivariant / message passing / ml potential / mlip / foundation model / llm...）
+ {hamiltonian, interatomic potential, neural network potential, nnp,
   ml hamiltonian, learnable hamiltonian, symmetry-adapted, equivariant force field}
+ 中文 {机器学习, 深度学习, 神经网络, 哈密顿量}
```

**ferro/凝聚态侧**（`FERRO_CORE_SET`）：
```
{ferroelectric, ferromagnet, antiferromagnet, altermagnet, multiferroic,
 piezoelectric, magnetoelectric, skyrmion, magnon, spin hall, moire magnet,
 spintronic, spintronics, spin current, topological magnon}
+ 中文 {铁电, 铁磁, 反铁磁, 交错磁, 多铁, 压电, 磁电, 斯格明子, 磁振子,
       自旋霍尔, 自旋流, 磁性, 拓扑磁}
```

匹配基于 `text = title + title_zh + abstract + abstract_zh` 的小写全文子串（与现有 `focus_filter._has_any` 一致）。

### `core_score`（用于排序/分层）

基础分 = 0.5；加成：
- 标题命中 METHOD_SET：+0.15
- 标题命中 FERRO_CORE_SET：+0.15
- 同时命中 `hamiltonian` 或 `potential` 且 + 磁/铁：+0.10
- arXiv `cond-mat` 类别：+0.05
- 命中 curated 高分期刊（复用 `CURATED_JOURNAL_HINTS`）：+0.05

上限 1.0。不命中核心关注判定 → `core_score = 0.0`。

### `core_priority`

新增一条排序 key，作为 `focus_priority` 的**第 0 位**（最高优先级），由 `focus_priority` 组合使用：

```python
return (0 if is_core_focus(item) else 1, -core_score(item), *existing_focus_priority_tail)
```

---

## § 2. 日报新增 "🎯 核心关注" section

### 位置与触发

- 在 hero（统计卡 + 标签）之后、"今日摘要" 之前。
- 当日核心关注论文数 **== 0** 时整个 section 不渲染（**不显示空卡**）。

### 结构

```
┌─ 🎯 核心关注（ML × ferro / 凝聚态）  [N 篇] ─────────┐
│                                                      │
│  ▸ 方向点评（AI 生成，3-4 句）                        │
│                                                      │
│  ┌─ paper 1 ──────────────────────────────────┐     │
│  │ 中文标题                                     │     │
│  │ 英文标题                                     │     │
│  │ [🧭 topic] [📖 journal] [👤 authors] [🎯 核心]│     │
│  │ 📄 摘要：...                                 │     │
│  │ 💡 亮点：...                                 │     │
│  │ 📐 方法要点：...（新字段）                    │     │
│  │ 🔗 相关工作关联：...（新字段）                │     │
│  │ 💡 对你方向的启示：...（新字段）              │     │
│  │ 阅读原文 ↗                                   │     │
│  └────────────────────────────────────────────┘     │
│  ... (按 core_score 降序，最多 8 篇)                 │
└──────────────────────────────────────────────────────┘
```

### 样式（加到 `render_daily_html` 的 `<style>` 块）

- `.daily-core-section`：金色渐变边框（#f59e0b → #fbbf24），背景 `rgba(253,244,215,0.4)`
- `.daily-core-card`：每篇 card 的圆角 20px + 细金色左边框 3px
- `.daily-chip-core`：小徽章，🎯 + "核心关注"，金色背景
- 移动端：布局同 `.daily-paper-card`

---

## § 3. AI 调用：方向点评 + 每篇 3 深字段

### 数据流

`generate_daily_pages.main` 中，在 `AISummarizer.generate_daily_summary` 返回后：

```python
if ai_provider_available:
    core_items = [it for it in summary['full_list'] if is_core_focus(it)]
    core_items.sort(key=lambda x: -core_score(x))
    core_items = core_items[:8]
    if core_items:
        deep_fields, direction_note = summarizer.generate_core_deep_fields(core_items, date)
        # 把 deep_fields 按 link 合并回 core_items
        for it in core_items:
            info = deep_fields.get(it['link'], {})
            it['method_point'] = info.get('method_point', '')
            it['related_work'] = info.get('related_work', '')
            it['implication'] = info.get('implication', '')
        summary['core_items'] = core_items
        summary['core_direction_note'] = direction_note
```

### 新方法：`AISummarizer.generate_core_deep_fields`

```python
def generate_core_deep_fields(
    self,
    core_items: List[Dict],
    date: str,
) -> Tuple[Dict[str, Dict[str, str]], str]:
    """对核心关注论文批量生成 3 个深度字段 + 整段方向点评。
    Returns: ({link -> {method_point, related_work, implication}}, direction_note_str)
    """
```

**Prompt 骨架**：

```
你是一位深耕 ML × 铁电/磁性/凝聚态方向的资深研究员。下面是 {date}
当日的 {N} 篇核心关注论文（均属于 ML × ferro/凝聚态方向）。

对每篇文章输出三条线索（中文、信息密度高，禁止套话）：
1) method_point（≤60字）：这篇论文的核心技术/方法是什么，一针见血。
2) related_work（≤70字）：与哪些已知方法/体系/团队方向呼应（可从你的训练知识推理，不要编造具体文献名）。
3) implication（≤70字）：对 ML × ferro/凝聚态研究者的具体启发（能不能复用方法？
   能不能迁移到类似体系？有没有待验证的假设？）。

另外再给一段 direction_note：
- 3-4 句，中文，高信息密度
- 概括本日 ML×ferro/凝聚态方向出现的**实质进展**
- 必须点名具体材料（如 NbOI2、CrI3、CrSBr）与具体方法（如 equivariant GNN、DFT+U、NEP、MACE）
- 禁止"整体来看/值得关注/有望为..."等套话

文献列表:
[1] ...
[2] ...
...

输出 JSON（只输出 JSON，无 markdown）：
{
  "direction_note": "...",
  "items": [
    {"index": 1, "method_point": "...", "related_work": "...", "implication": "..."},
    ...
  ]
}
```

**错误处理**：
- 超时/401/解析失败 → 三字段留空 + direction_note 留空；section 仍然渲染但不显示三字段（保持原样 card 渲染），错误不阻塞主流程。
- 使用 `_load_json_lenient` 做 JSON 解析。
- 失败时打印 warn，不 raise。

### 排序/高亮联动

- `_parse_response` 末尾，对 `full_list` 每篇 `item`：注入 `item['is_core_focus'] = is_core_focus(item)`、`item['core_score'] = core_score(item)`。
- `ml_highlights` / `ferro_highlights` 构造时**先按 `core_score` 降序**挑选，再按原逻辑 fallback；仍限制 top 5。
- `focus_priority` 在 `focus_filter.py` 内改为：若 `is_core_focus(item)` 则 tuple 第 0 位返回 0，否则 1；其余 key 保持不变。

---

## § 4. 周报结构重构

### 新的渲染顺序

```
1. [Hero]                              # 保留
2. 🎯 本周核心方向（ML × ferro/凝聚态）  # 新，最吸睛
   - 方向周回顾（AI 生成，6-8 句）
   - 本周核心论文列表（按 core_score，全列，≤20 篇）
   - 每篇带 § 3 的三深字段
3. 相关外围（by_topic: 铁电/磁性/多铁/方法）  # 从前排降级
   - 每类 top 3-5 篇
4. 本周趋势 / 展望                      # 简化为单段
5. 全文速览 / 期刊分布                  # 最后
```

如当周核心关注数 == 0：第 2 节不渲染，周报退化为旧版结构。

### 新方法：`WeeklySummarizer._generate_core_weekly`

```python
def _generate_core_weekly(
    self,
    core_items: List[Dict],
    week_start: str,
    week_end: str,
) -> Tuple[str, Dict[str, Dict]]:
    """Returns: (direction_weekly_note_str, {link -> 3 deep fields})"""
```

Prompt 结构：与 § 3 相同但 note 要求 6-8 句、面向"本周"。

### 模板层修改

- `weekly_page_enhancer.py` 或 `weekly_summary.py` 中渲染 HTML 的函数（依据现有代码位置）插入新 `render_core_weekly_section(core_items, direction_weekly_note)`。
- 复用日报的 `.daily-core-*` CSS，样式名改 `.weekly-core-*`。

---

## § 5. 配置 / 环境变量

- 新增 `CORE_FOCUS_CONFIG` 于 `config.py`：
  ```python
  CORE_FOCUS_CONFIG = {
      "enabled": True,   # 可关闭以 fallback 到旧行为
      "daily_max_items": 8,
      "weekly_max_items": 20,
      "min_score": 0.60,  # 低于此分数不展示 (例如只命中一侧 0.50 的边缘样本)
  }
  ```
- 由 `CORE_FOCUS_ENABLED` 环境变量可临时关闭（测试 fallback）。

---

## § 6. 需要修改/新增的文件

| 文件 | 变更 |
|---|---|
| `focus_core.py` | **新建**：`is_core_focus`, `core_score`, `core_priority`, 两个关键词集常量 |
| `focus_filter.py` | `focus_priority` 增加 `is_core_focus` 作为第 0 排序键 |
| `ai_summarizer.py` | 新增 `AISummarizer.generate_core_deep_fields`；`_parse_response` 注入 `is_core_focus`/`core_score`；`ml_highlights`/`ferro_highlights` 排序联动 |
| `weekly_summary.py` | 新增 `_generate_core_weekly`；调整渲染顺序 |
| `generate_daily_pages.py` | 主流程调用 deep-field；`render_daily_html` 新增 `render_core_section`；CSS 补金色核心区域样式 |
| `config.py` | 新增 `CORE_FOCUS_CONFIG` |
| `docs/superpowers/specs/2026-04-15-core-focus-deep-report-design.md` | 本文档 |

---

## § 7. 成本估算

- 日报：现 ~2 Kimi calls；新增 1 batch call（核心关注 deep fields + direction_note） → **~3 calls/day**，单日净增 ~8K tokens
- 周报：现 ~1-2 calls；新增 1 batch call → **~3 calls/week**
- 整体月度成本 +25~30%，换取用户方向的高密度信息

---

## § 8. 验证方式

1. **单元级**（`focus_core.py`）：
   - 构造 10 条典型 item（明确 core / 明确非 core / 边缘），逐一断言 `is_core_focus` 与 `core_score` 预期。
2. **集成级**（日报）：
   ```bash
   KIMI_API_KEY=... AI_PROVIDER=kimi python generate_daily_pages.py --date 2026-04-14 --force
   ```
   断言：`docs/daily/2026-04-14.html` 含 `class="daily-core-section"`；方向点评非空；每篇核心卡片含 method_point/related_work/implication（或在 LLM 失败时三字段均为空但不崩）；`data-is-core="true"` 的卡片数 > 0 且 ≤ 8。
3. **集成级**（周报）：
   ```bash
   python weekly_summary.py
   ```
   断言：`docs/weekly/YYYY-MM-DD.html` 新顺序；"本周核心方向" 在 "相关外围" 之前。
4. **回归**：`CORE_FOCUS_CONFIG.enabled = False` 一键 fallback 到旧行为；老页面结构不破。
5. **成本**：跑 5 天日报、1 次周报，记录 Kimi 调用次数 & token 总量；确认 < 旧总量 × 1.3。
6. **审美**：浏览器打开日报页面，核心 section 金色高亮可见；移动端布局不断行。

---

## § 9. 明确不做的事（YAGNI）

- 不做"检索本 repo 历史日报做对比"（重度路径被用户弃选）。
- 不把"核心关注"从首页抽成独立子页面（当前是 section，足够）。
- 不给 fallback 页面写特殊提示语（fallback 只是少一个 section，不需 UX 解释）。
- 不对 deep-field 结果做 Chinese ratio 校验（prompt 已明确，且相对低风险；若将来出现英文串，再补校验）。
- 不做 core_focus 的 UI 开关（config 即可控制；无需前端交互）。
