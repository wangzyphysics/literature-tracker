# 周报功能说明

## 功能介绍

周报功能每周自动总结 Nature/Science 系列期刊中磁性/铁电相关的重要工作，使用 AI 生成专业的研究分析报告。

## 涵盖期刊

**严格筛选顶刊，确保质量：**

- **Nature 系列**：Nature, Nature Materials, Nature Physics, Nature Chemistry, Nature Communications, Nature Nanotechnology, Nature Electronics, Nature Energy
- **Science 系列**：Science（正刊）, Science Advances
  - ⚠️ 注意：不包含 ScienceDirect（那只是数据库平台，包含2区3区期刊）
- **其他顶刊**：Physical Review Letters (PRL), Advanced Materials

**排除内容**：
- ScienceDirect 平台期刊（非顶刊）
- Table of Contents（目录页）
- Editor's Suggestions（编辑推荐）
- News & Highlights（新闻）

## 关注领域

- 铁电材料 (ferroelectric)
- 铁磁材料 (ferromagnetic)
- 多铁性材料 (multiferroic)
- 压电材料 (piezoelectric)
- 反铁电/反铁磁材料
- 磁电耦合
- 相关的极化、磁化、畴壁、斯格明子等研究

## 周报内容

每份周报包含：

1. **本周总览** - 文献总数、主要研究方向、重要发现
2. **重点文献** - 5-8篇最重要的文献详细分析
   - 研究材料体系
   - 研究性质和方法
   - 核心创新点
   - 研究意义
3. **研究趋势** - 本周研究热点和趋势分析
4. **未来展望** - 研究方向预测
5. **期刊分布** - 各期刊发表统计

## 手动生成周报

```bash
# 生成本周周报（自动计算本周一）
python weekly_summary.py

# 生成指定周的周报（指定周一日期）
python weekly_summary.py 2025-01-13
```

## 自动化生成

可以使用 GitHub Actions 或 cron 任务每周自动生成周报：

```yaml
# .github/workflows/weekly-summary.yml
name: Generate Weekly Summary

on:
  schedule:
    - cron: '0 0 * * 1'  # 每周一 00:00 UTC
  workflow_dispatch:

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python weekly_summary.py
        env:
          AI_API_KEY: ${{ secrets.AI_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "🔬 自动生成周报"
```

## 配置 AI API

在 `config.py` 中配置 AI API：

```python
AI_CONFIG = {
    'provider': 'gemini',  # 或 'siliconflow', 'groq', 'deepseek'
    'api_key': 'your-api-key-here'
}
```

或使用环境变量：

```bash
export AI_API_KEY="your-api-key-here"
export AI_PROVIDER="gemini"
```

## 查看周报

访问 `/weekly/` 页面查看所有周报列表，点击即可查看详细内容。

## 注意事项

- 周报按周一日期命名（如 `2025-01-13.html`）
- 如果 AI API 不可用，会使用降级模式生成基础周报
- 周报索引文件 `index.json` 会自动更新
- 建议每周一凌晨运行，确保包含完整一周的文献
