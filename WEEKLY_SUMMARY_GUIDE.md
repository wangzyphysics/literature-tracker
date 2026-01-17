# 周报功能使用指南

## 功能概述

周报功能已成功添加到文献追踪系统！现在可以每周自动总结 Nature/Science 系列期刊中磁性/铁电相关的重要工作。

## 主要特性

### 1. 智能筛选
- **顶刊覆盖**：
  - Nature 系列（Nature、Nature Materials、Nature Physics 等）
  - Science 系列（**Science 正刊**、Science Advances）
  - ⚠️ **不包含** ScienceDirect（那只是数据库平台，包含2区3区期刊）
  - 其他顶刊：Physical Review Letters、Advanced Materials
- **领域聚焦**：自动识别磁性、铁电、多铁性、压电等相关研究
- **关键词匹配**：支持中英文关键词（ferroelectric、铁电、multiferroic、多铁等）
- **内容过滤**：自动排除 Table of Contents、Editor's Suggestions 等非研究内容

### 2. AI 分析
使用 Gemini AI 生成专业周报，包含：
- 📊 **本周总览**：文献总数、主要研究方向、重要发现
- ⭐ **重点文献**：5-8篇最重要文献的详细分析
  - 研究材料体系（如 BaTiO₃、BiFeO₃）
  - 研究性质和方法
  - 核心创新点
  - 研究意义
- 🔥 **研究趋势**：本周热点和趋势分析
- 🔮 **未来展望**：研究方向预测
- 📚 **期刊分布**：各期刊发表统计

### 3. 网页展示
- 主页新增"🔬 周报"入口
- 周报列表页面：`/weekly/`
- 每份周报独立页面，支持深色/浅色主题

## 使用方法

### 查看周报
1. 访问主页，点击顶部导航栏的"🔬 周报"
2. 在周报列表中选择要查看的周报
3. 点击"查看周报 →"按钮

### 手动生成周报

```bash
# 生成本周周报（自动计算本周一）
python weekly_summary.py

# 生成指定周的周报（指定周一日期）
python weekly_summary.py 2025-01-13
```

### 配置 AI API

在 `config.py` 中添加：

```python
AI_CONFIG = {
    'provider': 'gemini',
    'api_key': 'your-gemini-api-key'
}
```

或使用环境变量：

```bash
export AI_API_KEY="your-api-key"
export AI_PROVIDER="gemini"
```

### 自动化生成（可选）

可以设置 GitHub Actions 每周自动生成：

1. 在 GitHub 仓库设置中添加 Secret：`AI_API_KEY`
2. 创建 `.github/workflows/weekly-summary.yml`：

```yaml
name: Generate Weekly Summary

on:
  schedule:
    - cron: '0 0 * * 1'  # 每周一 00:00 UTC
  workflow_dispatch:  # 支持手动触发

jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Generate weekly summary
        run: python weekly_summary.py
        env:
          AI_API_KEY: ${{ secrets.AI_API_KEY }}
      
      - name: Commit and push
        uses: stefanzweifel/git-auto-commit-action@v4
        with:
          commit_message: "🔬 自动生成周报"
          file_pattern: "docs/weekly/*.html docs/weekly/index.json"
```

## 文件结构

```
docs/weekly/
├── index.html          # 周报列表页面
├── index.json          # 周报索引（自动生成）
├── README.md           # 功能说明
└── YYYY-MM-DD.html     # 各周周报（按周一日期命名）
```

## 降级模式

如果 AI API 不可用或超时，系统会自动使用降级模式：
- 仍然筛选和展示符合条件的文献
- 按期刊重要性排序
- 提供基础的统计信息
- 标注"（AI分析暂不可用）"

## 示例周报

已生成示例周报：`docs/weekly/2025-12-22.html`

包含：
- 本周文献总数统计
- ML相关和铁性相关文献数量
- 重点文献推荐
- 期刊分布统计

## 注意事项

1. **日期格式**：周报按周一日期命名（YYYY-MM-DD）
2. **数据来源**：从 `docs/data/index.json` 读取文献数据
3. **API 限制**：Gemini API 有速率限制，建议合理安排生成时间
4. **主题支持**：周报页面自动适配深色/浅色主题

## 下一步建议

1. **配置 AI API**：获取 Gemini API 密钥以启用 AI 分析
2. **设置自动化**：配置 GitHub Actions 实现每周自动生成
3. **定期查看**：每周一查看最新周报，了解领域动态
4. **反馈优化**：根据使用体验调整关键词和筛选条件

## 技术细节

- **脚本**：`weekly_summary.py`
- **AI 提供商**：支持 Gemini、SiliconFlow、Groq、DeepSeek
- **筛选逻辑**：
  - 期刊匹配：TOP_JOURNALS 列表
  - 关键词匹配：KEYWORDS 列表（支持中英文）
  - 日期范围：指定周的周一至周日
- **HTML 生成**：使用模板生成响应式页面
- **索引更新**：自动扫描并更新 `index.json`

## 支持

如有问题或建议，请在 GitHub 仓库提 Issue。
