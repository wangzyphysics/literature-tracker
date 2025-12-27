# Requirements Document

## Introduction

本文档定义文献追踪系统的高级功能需求，包括：数据分析与可视化、高级搜索、性能优化、RSS输出和AI摘要报告。

## Glossary

- **Analytics_Dashboard**: 数据分析仪表板，展示文献统计和趋势的独立页面
- **Trend_Chart**: 趋势图表，按时间维度展示文献发表趋势
- **Word_Cloud**: 词云组件，可视化展示高频关键词
- **Advanced_Search**: 高级搜索引擎，支持正则表达式和布尔运算
- **Virtual_Scroll**: 虚拟滚动技术，优化大量数据渲染性能
- **PWA**: Progressive Web App，支持离线访问的渐进式网页应用
- **RSS_Generator**: RSS生成器，输出标准RSS feed
- **AI_Summarizer**: AI摘要生成器，使用免费AI API生成每日摘要
- **Incremental_Index**: 增量索引，只更新变化的数据

## Requirements

### Requirement 1: 数据分析仪表板

**User Story:** As a 用户, I want 查看文献统计和趋势分析, so that 我可以了解研究领域的发展动态。

#### Acceptance Criteria

1. THE 系统 SHALL 提供独立的数据分析页面，可从主页点击进入
2. THE Analytics_Dashboard SHALL 在页面加载时自动计算所有统计数据
3. THE Analytics_Dashboard SHALL 使用响应式布局，适配不同屏幕尺寸
4. THE Analytics_Dashboard SHALL 支持深色/浅色主题切换
5. THE Analytics_Dashboard SHALL 提供返回主页的导航按钮

### Requirement 2: 文献发表趋势图表

**User Story:** As a 用户, I want 查看文献发表趋势, so that 我可以了解不同时间段的文献产出情况。

#### Acceptance Criteria

1. THE Trend_Chart SHALL 展示按月统计的文献发表数量折线图
2. THE Trend_Chart SHALL 展示按周统计的文献发表数量柱状图
3. THE Trend_Chart SHALL 支持切换时间维度（月/周）
4. THE Trend_Chart SHALL 区分显示AI相关和非AI相关文献的趋势
5. THE Trend_Chart SHALL 在图表上标注数据点的具体数值
6. THE Trend_Chart SHALL 支持鼠标悬停显示详细信息
7. THE Trend_Chart SHALL 使用图表库（Chart.js或ECharts）实现

### Requirement 3: 期刊分布饼图

**User Story:** As a 用户, I want 查看期刊分布情况, so that 我可以了解不同期刊的文献占比。

#### Acceptance Criteria

1. THE 系统 SHALL 展示期刊分布饼图，显示前10个期刊
2. THE 饼图 SHALL 显示每个期刊的文献数量和百分比
3. THE 饼图 SHALL 为每个期刊使用不同颜色
4. THE 饼图 SHALL 支持点击查看该期刊的所有文献
5. THE 饼图 SHALL 将其他期刊合并为"其他"类别

### Requirement 4: 关键词云

**User Story:** As a 用户, I want 查看研究热点关键词, so that 我可以快速了解领域的研究重点。

#### Acceptance Criteria

1. THE Word_Cloud SHALL 从所有文献的标题和摘要中提取关键词
2. THE Word_Cloud SHALL 根据词频大小展示关键词
3. THE Word_Cloud SHALL 过滤常见停用词（the, a, an, of等）
4. THE Word_Cloud SHALL 支持点击关键词搜索相关文献
5. THE Word_Cloud SHALL 最多显示50个高频关键词
6. THE Word_Cloud SHALL 使用词云库（wordcloud2.js或d3-cloud）实现

### Requirement 5: AI vs 非AI文献趋势对比

**User Story:** As a 用户, I want 对比AI和非AI文献的发展趋势, so that 我可以了解AI在该领域的渗透情况。

#### Acceptance Criteria

1. THE 系统 SHALL 展示AI相关和非AI相关文献的数量对比
2. THE 系统 SHALL 展示AI文献占比的时间趋势图
3. THE 系统 SHALL 计算并显示AI文献的增长率
4. THE 系统 SHALL 支持按期刊分组查看AI文献分布

### Requirement 6: 正则表达式搜索

**User Story:** As a 用户, I want 使用正则表达式搜索, so that 我可以进行更精确的模式匹配。

#### Acceptance Criteria

1. THE Advanced_Search SHALL 提供正则表达式搜索模式切换
2. WHEN 用户启用正则模式, THE Advanced_Search SHALL 将搜索词作为正则表达式处理
3. IF 正则表达式无效, THEN THE Advanced_Search SHALL 显示错误提示
4. THE Advanced_Search SHALL 支持常见正则语法（.*、\d、\w、^、$等）
5. THE Advanced_Search SHALL 在搜索框旁显示正则模式指示器

### Requirement 7: 布尔运算符搜索

**User Story:** As a 用户, I want 使用布尔运算符组合搜索条件, so that 我可以进行复杂的查询。

#### Acceptance Criteria

1. THE Advanced_Search SHALL 支持 AND 运算符（所有关键词都匹配）
2. THE Advanced_Search SHALL 支持 OR 运算符（任一关键词匹配）
3. THE Advanced_Search SHALL 支持 NOT 运算符（排除关键词）
4. THE Advanced_Search SHALL 支持括号分组（优先级控制）
5. THE Advanced_Search SHALL 提供布尔搜索语法帮助提示
6. THE Advanced_Search SHALL 在搜索框下方显示解析后的查询逻辑

### Requirement 8: 虚拟滚动优化

**User Story:** As a 用户, I want 系统流畅处理大量文献, so that 我可以快速浏览数千篇文献而不卡顿。

#### Acceptance Criteria

1. THE Virtual_Scroll SHALL 只渲染可见区域的文献卡片
2. WHEN 用户滚动, THE Virtual_Scroll SHALL 动态加载和卸载卡片
3. THE Virtual_Scroll SHALL 维护滚动位置的准确性
4. THE Virtual_Scroll SHALL 支持至少10000篇文献的流畅滚动
5. THE Virtual_Scroll SHALL 预加载可见区域上下各一屏的内容

### Requirement 9: PWA离线支持

**User Story:** As a 用户, I want 离线访问文献, so that 我可以在没有网络时继续浏览。

#### Acceptance Criteria

1. THE PWA SHALL 注册Service Worker实现离线缓存
2. THE PWA SHALL 缓存所有静态资源（HTML、CSS、JS）
3. THE PWA SHALL 缓存文献数据（index.json）
4. THE PWA SHALL 提供manifest.json支持安装到桌面
5. WHEN 离线时, THE PWA SHALL 显示离线提示但仍可访问缓存内容
6. THE PWA SHALL 在网络恢复时自动更新缓存

### Requirement 10: 增量索引更新

**User Story:** As a 系统管理员, I want 只更新变化的数据, so that 我可以减少处理时间和资源消耗。

#### Acceptance Criteria

1. THE Incremental_Index SHALL 记录上次更新的时间戳
2. WHEN 抓取新文献时, THE Incremental_Index SHALL 只处理新增或修改的文献
3. THE Incremental_Index SHALL 检测并跳过已存在的文献
4. THE Incremental_Index SHALL 更新index.json时保留现有数据
5. THE Incremental_Index SHALL 在日志中显示新增、更新、跳过的文献数量

### Requirement 11: RSS Feed输出

**User Story:** As a 用户, I want 订阅RSS feed, so that 我可以在RSS阅读器中接收更新。

#### Acceptance Criteria

1. THE RSS_Generator SHALL 生成符合RSS 2.0标准的XML文件
2. THE RSS_Generator SHALL 包含最近100篇文献
3. THE RSS_Generator SHALL 为每篇文献提供标题、摘要、链接、发布日期
4. THE RSS_Generator SHALL 在每次数据更新后重新生成RSS文件
5. THE RSS_Generator SHALL 将RSS文件保存为 docs/feed.xml
6. THE 主页 SHALL 在HTML head中添加RSS feed链接

### Requirement 12: AI每日摘要报告

**User Story:** As a 用户, I want 收到AI生成的每日摘要, so that 我可以快速了解当天的重要文献。

#### Acceptance Criteria

1. THE AI_Summarizer SHALL 使用免费AI API（如OpenRouter、Groq、DeepSeek）
2. THE AI_Summarizer SHALL 每日生成一次摘要报告
3. THE AI_Summarizer SHALL 选择当天最重要的5-10篇文献
4. THE AI_Summarizer SHALL 为每篇文献生成简短摘要（50-100字）
5. THE AI_Summarizer SHALL 识别当天的研究热点和趋势
6. THE AI_Summarizer SHALL 将摘要通过邮件发送
7. THE AI_Summarizer SHALL 将摘要保存为HTML文件在网站展示
8. IF API调用失败, THEN THE AI_Summarizer SHALL 降级为简单统计摘要

### Requirement 13: 数据导出增强

**User Story:** As a 用户, I want 导出分析数据, so that 我可以在其他工具中进一步分析。

#### Acceptance Criteria

1. THE Analytics_Dashboard SHALL 提供导出统计数据为CSV的功能
2. THE Analytics_Dashboard SHALL 提供导出图表为PNG的功能
3. THE 导出的CSV SHALL 包含时间序列数据和统计指标
4. THE 导出的PNG SHALL 保持图表的清晰度和样式

### Requirement 14: 性能监控

**User Story:** As a 系统管理员, I want 监控系统性能, so that 我可以及时发现和解决性能问题。

#### Acceptance Criteria

1. THE 系统 SHALL 记录页面加载时间
2. THE 系统 SHALL 记录搜索响应时间
3. THE 系统 SHALL 记录渲染性能指标（FPS、内存使用）
4. THE 系统 SHALL 在控制台输出性能日志
5. THE 系统 SHALL 在性能低于阈值时显示警告

