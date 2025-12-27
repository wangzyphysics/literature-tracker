# 📚 RSS文献追踪系统

自动追踪学术RSS源，筛选关键词相关文献，翻译成中文，并通过GitHub Pages展示。

## ✨ 功能特性

### 核心功能
- 🔍 **RSS抓取**: 支持50+学术期刊RSS源（Nature、Science、APS、ACS、Wiley、RSC、Elsevier等）
- � ***关键词筛选**: 自动筛选包含指定关键词的文献
- 🌐 **自动翻译**: 使用Google翻译将标题和摘要翻译成中文
- 📝 **Markdown存储**: 每篇文献保存为独立Markdown文件
- �  **历史记录**: JSON文件保存所有历史数据
- ⏰ **定时任务**: 每12小时自动抓取
- �  **邮件通知**: 新文献自动发送邮件
- 💬 **微信推送**: 通过Server酱发送微信通知

### 前端界面 (V3)
- 🎴 **可折叠卡片**: 文献以卡片形式展示，点击展开查看详情
- 🤖 **AI分类筛选**: 自动识别AI相关文献，支持分类筛选
- 🌓 **深色/浅色主题**: 支持主题切换，护眼模式
- 📱 **响应式设计**: 完美适配手机、平板、电脑
- ⌨️ **键盘快捷键**: j/k导航，Enter展开，o打开原文，s收藏，r标记已读，l稍后阅读
- 🔍 **搜索功能**: 支持标题、摘要、作者搜索，带搜索历史
- ⭐ **收藏功能**: 标记喜欢的文献
- 📖 **阅读状态**: 标记已读/未读，追踪阅读进度
- 📌 **稍后阅读**: 添加到待读列表，集中阅读
- 📄 **导出功能**: 支持BibTeX/RIS格式导出，单篇或批量
- 🎨 **关键词高亮**: AI关键词自动高亮显示
- 📅 **日期筛选**: 按日期范围筛选文献
- 📚 **期刊筛选**: 按期刊或期刊分组筛选
- 📊 **统计信息**: 实时显示文献数量、分类统计

## 🚀 快速开始

### 1. 创建GitHub仓库

```bash
# 克隆或初始化仓库
git init literature-tracker
cd literature-tracker

# 复制所有文件到仓库
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置邮件（可选）

编辑 `config.py`，填写邮件配置：

```python
EMAIL_CONFIG = {
    "recipient": "your-email@example.com",
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "sender_email": "your-sender@qq.com",  # 发送邮箱
    "sender_password": "your-auth-code",    # QQ邮箱授权码
}
```

### 4. 本地运行

```bash
# 运行一次
python main.py --once

# 不发送邮件
python main.py --once --no-email

# 启动定时任务（每12小时）
python main.py --schedule
```

### 5. 部署到GitHub

```bash
git add -A
git commit -m "初始化文献追踪系统"
git remote add origin https://github.com/YOUR_USERNAME/literature-tracker.git
git push -u origin main
```

### 6. 配置GitHub Actions

在仓库设置中添加Secrets（用于邮件通知）：
- `EMAIL_SENDER`: 发送邮箱地址
- `EMAIL_PASSWORD`: 邮箱授权码

### 7. 启用GitHub Pages

1. 进入仓库 Settings → Pages
2. Source 选择 "GitHub Actions"
3. 等待部署完成

## 📁 项目结构

```
literature-tracker/
├── main.py              # 主程序
├── config.py            # 配置文件
├── rss_fetcher.py       # RSS抓取模块
├── translator.py        # 翻译模块
├── data_manager.py      # 数据管理模块
├── email_notifier.py    # 邮件通知模块
├── requirements.txt     # Python依赖
├── data/                # 数据目录
│   ├── history.json     # 历史记录
│   ├── favorites.json   # 收藏列表
│   └── index.json       # 网页索引
├── articles/            # Markdown文献
├── docs/                # GitHub Pages网站
│   ├── index.html
│   ├── style.css
│   └── app.js
└── .github/workflows/   # GitHub Actions
    ├── fetch.yml        # 定时抓取
    └── pages.yml        # 部署Pages
```

## 🔧 自定义配置

### 修改关键词

编辑 `config.py` 中的 `KEYWORDS` 列表：

```python
KEYWORDS = [
    "ferro",
    "machine",
    "learning",
    # 添加更多关键词...
]
```

### 添加RSS源

编辑 `config.py` 中的 `RSS_FEEDS` 列表。

### 修改抓取频率

编辑 `.github/workflows/fetch.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0,12 * * *'  # 每12小时
  # - cron: '0 */6 * * *'  # 每6小时
  # - cron: '0 8 * * *'    # 每天8点
```

## 📧 QQ邮箱配置说明

1. 登录QQ邮箱 → 设置 → 账户
2. 开启 "POP3/SMTP服务"
3. 生成授权码
4. 将授权码填入配置

## 📄 许可证

MIT License

---

## 📖 V3 功能详细说明

### 稍后阅读功能 📌

**使用方法**:
- 点击文章的 📍 按钮添加到待读列表
- 按钮变为 📌，文章左侧显示紫色边框
- 点击"📌 待读"筛选按钮查看所有待读文章
- 键盘快捷键: 按 `l` 键标记当前文章

**特点**:
- 本地存储，刷新页面状态保持
- 统计栏显示待读数量
- 支持筛选只看待读文章

### 导出功能 📄

**单篇导出**:
1. 展开任意文章
2. 在文章底部点击"📄 BibTeX"或"📋 RIS"
3. 文件自动下载，文件名格式: `作者姓氏年份.bib`

**批量导出**:
1. 使用筛选功能选择想要的文章
2. 在控制面板找到"批量导出"区域
3. 点击"📄 BibTeX"或"📋 RIS"
4. 导出当前筛选结果的所有文章，文件名格式: `literature_export_日期.bib`

**支持格式**:
- **BibTeX**: 适用于 LaTeX 文档引用
- **RIS**: 适用于 EndNote、Mendeley、Zotero 等文献管理软件

### 键盘快捷键 ⌨️

| 快捷键 | 功能 |
|--------|------|
| `j` | 下一篇文章 |
| `k` | 上一篇文章 |
| `Enter` | 展开/折叠当前文章 |
| `o` | 在新标签页打开原文 |
| `s` | 收藏/取消收藏 |
| `r` | 标记已读/未读 |
| `l` | 添加到待读/移除待读 |

### 筛选功能 🔍

**分类筛选**:
- 全部 - 显示所有文章
- 🤖 AI相关 - 只显示包含AI关键词的文章
- 📚 非AI - 只显示不包含AI关键词的文章

**阅读状态筛选**:
- 全部 - 显示所有文章
- 未读 - 只显示未读文章
- 已读 - 只显示已读文章
- 📌 待读 - 只显示待读文章

**期刊筛选**:
- 支持按期刊分组筛选（顶刊、Nature系列、APS系列、ACS系列、Wiley系列、RSC系列、Elsevier系列、预印本、其他）
- 支持按单独期刊筛选

**日期筛选**:
- 支持按日期范围筛选文献

### 视觉标识 🎨

| 标识 | 含义 |
|------|------|
| 黄色左边框 | 收藏的文章 |
| 紫色左边框 | 待读的文章 |
| 半透明 | 已读的文章 |
| 📍 | 未添加到待读 |
| 📌 | 已添加到待读 |
| 🤖 AI | AI相关文章 |
| 📚 非AI | 非AI相关文章 |

---

## 📋 开发规范 (.kiro/specs)

本项目使用规范化的需求和设计文档来指导开发。所有规范文档位于 `.kiro/specs/` 目录。

### 已完成的功能规范

#### 1. literature-ui-enhancement (UI增强)
**状态**: ✅ 已完成

**包含功能**:
- 可折叠文献卡片
- AI分类筛选
- 深色/浅色主题切换
- 响应式设计
- 键盘快捷键
- 关键词高亮
- 悬停预览
- 邮件发送Bug修复

**文档**:
- `requirements.md` - 需求文档（10个需求，50+验收标准）
- `design.md` - 设计文档（架构、组件、数据模型、9个正确性属性）
- `tasks.md` - 实现任务（12个主任务，40+子任务）

#### 2. literature-enhancements-v2 (V2增强)
**状态**: ✅ 已完成

**包含功能**:
- 阅读进度追踪
- 文献去重优化
- 搜索历史
- 微信推送通知
- 邮件摘要预览

**文档**:
- `requirements.md` - 需求文档（5个需求，25+验收标准）

### V3 新增功能 (当前版本)

**已实现**:
- ✅ 稍后阅读队列
- ✅ 导出功能 (BibTeX/RIS)

**计划中**:
- ⏳ RSS 输出
- ⏳ 每周摘要报告
- ⏳ 关键词云/热点分析
- ⏳ PWA 离线支持

### 规范文档说明

**requirements.md** - 需求文档
- 使用 EARS 模式编写需求
- 每个需求包含用户故事和验收标准
- 遵循 INCOSE 质量规则

**design.md** - 设计文档
- 系统架构和组件设计
- 数据模型定义
- 正确性属性（Property-Based Testing）
- 错误处理策略
- 测试策略

**tasks.md** - 实现任务
- 将设计分解为可执行的任务
- 每个任务关联需求
- 标记可选任务（测试相关）
- 包含检查点
