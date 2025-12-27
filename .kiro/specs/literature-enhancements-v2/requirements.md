# Requirements Document

## Introduction

本文档定义文献追踪系统的第二阶段增强功能，包括：阅读进度追踪、文献去重优化、搜索历史、微信推送通知、邮件摘要预览。

## Glossary

- **Read_Status**: 阅读状态，标记文献为"已读"或"未读"
- **Deduplication_Engine**: 去重引擎，基于DOI或标题相似度识别重复文献
- **Search_History**: 搜索历史，记录用户的搜索词
- **WeChat_Notifier**: 微信通知器，通过Server酱或企业微信发送推送
- **Email_Digest**: 邮件摘要，精简版邮件只包含标题列表

## Requirements

### Requirement 1: 阅读进度追踪

**User Story:** As a 用户, I want 标记文献的阅读状态, so that 我可以追踪哪些文献还没看。

#### Acceptance Criteria

1. THE 页面 SHALL 为每篇文献提供"已读/未读"状态切换按钮
2. WHEN 用户点击状态按钮, THE 系统 SHALL 切换该文献的阅读状态
3. THE 系统 SHALL 将阅读状态保存到本地存储
4. THE 页面 SHALL 提供筛选选项：全部、未读、已读
5. THE 统计信息 SHALL 显示未读文献数量
6. WHEN 页面加载, THE 系统 SHALL 恢复之前保存的阅读状态

### Requirement 2: 文献去重优化

**User Story:** As a 用户, I want 系统自动去除重复文献, so that 我不会看到同一篇文献多次。

#### Acceptance Criteria

1. WHEN 抓取文献时, THE Deduplication_Engine SHALL 基于DOI识别重复文献
2. IF DOI不可用, THEN THE Deduplication_Engine SHALL 基于标题相似度（>90%）识别重复
3. WHEN 发现重复文献, THE 系统 SHALL 保留信息最完整的版本
4. THE 系统 SHALL 记录去重数量并在日志中显示

### Requirement 3: 搜索历史

**User Story:** As a 用户, I want 系统记住我的搜索词, so that 我可以快速重复之前的搜索。

#### Acceptance Criteria

1. WHEN 用户执行搜索, THE 系统 SHALL 保存搜索词到历史记录
2. THE 系统 SHALL 最多保存10条最近的搜索历史
3. WHEN 用户点击搜索框, THE 页面 SHALL 显示搜索历史下拉列表
4. WHEN 用户点击历史记录项, THE 系统 SHALL 自动填充并执行搜索
5. THE 页面 SHALL 提供清除搜索历史的选项
6. THE 系统 SHALL 将搜索历史保存到本地存储

### Requirement 4: 微信推送通知

**User Story:** As a 用户, I want 通过微信接收新文献通知, so that 我可以更及时地了解更新。

#### Acceptance Criteria

1. THE 系统 SHALL 支持通过Server酱发送微信推送
2. WHEN 有新文献时, THE WeChat_Notifier SHALL 发送包含文献数量和标题列表的通知
3. IF Server酱配置不完整, THEN THE 系统 SHALL 跳过微信推送并记录日志
4. THE 通知内容 SHALL 包含文献标题（中文）、期刊和链接
5. THE 系统 SHALL 支持配置是否启用微信推送

### Requirement 5: 邮件摘要预览

**User Story:** As a 用户, I want 收到精简版邮件, so that 我可以快速浏览新文献列表。

#### Acceptance Criteria

1. THE Email_Digest SHALL 只包含文献标题列表，不包含完整摘要
2. THE Email_Digest SHALL 为每篇文献提供"查看详情"链接
3. THE 系统 SHALL 支持配置邮件模式：完整版或摘要版
4. THE Email_Digest SHALL 在邮件开头显示文献总数和AI相关/非AI分类统计
5. THE Email_Digest SHALL 按期刊分组显示文献
