# OpenClaw AI 日报自动化系统

## 设置完成 ✓

### 自动化流程

每天 **09:00**（北京时间），OpenClaw AI 会自动执行：

1. **抓取文献** - 运行 `run_optimized_sync.py` 获取最新文献
2. **筛选日报文章** - 根据关键词筛选目标领域的文章
3. **生成中文翻译** - 由 OpenClaw AI 直接生成标题、摘要和一句话总结
4. **生成HTML** - 创建美观的日报页面
5. **推送到GitHub** - 自动提交并推送更新

### 文件说明

| 文件 | 用途 |
|------|------|
| `daily_cron.sh` | Shell自动化脚本 |
| `ai_daily_helper.py` | Python辅助脚本（交互式） |
| `auto_daily.py` | 纯自动化脚本 |
| `cron_config.json` | Cron配置备份 |

### 手动触发

如果需要手动生成某天的日报：

```bash
cd /root/.openclaw/workspace/literature-tracker

# 方法1：使用helper脚本（推荐，支持AI翻译）
python3 ai_daily_helper.py 2026-04-15

# 方法2：纯自动化
python3 auto_daily.py

# 方法3：仅生成HTML（使用已有数据）
python3 generate_with_local_ai.py 2026-04-15
```

### 关闭GitHub Actions

如需完全禁用GitHub Actions：
1. 访问 https://github.com/Hongyu-yu/literature-tracker/settings/actions
2. 选择 "Disable actions for this repository"

或在仓库根目录创建 `.github/workflows` 的备份后删除该目录。

### 监控与日志

- 日志文件：`/tmp/literature_daily_YYYY-MM-DD.log`
- Cron任务状态：`/root/.openclaw/cron/jobs.json`
- 下次运行时间：每天 09:00

### 状态检查

```bash
# 查看最新日报
ls -lt docs/daily/2026-04-*.html | head -5

# 检查数据
python3 -c "from datetime import datetime; import json; d=datetime.now().strftime('%Y-%m-%d'); print(open(f'ai_prompts/{d}_data.json').read())" 2>/dev/null || echo "无数据"
```

---
*由 OpenClaw AI 配置 - 2026-04-15*
