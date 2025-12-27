# Requirements Document

## Introduction

本文档定义了文献追踪系统前端页面的增强需求，包括：可折叠文献卡片布局、AI相关分类筛选、深色/浅色主题切换、响应式设计优化，以及邮件发送功能的bug修复。

## Glossary

- **Literature_Card**: 文献卡片组件，展示单篇文献信息的UI元素
- **Theme_Switcher**: 主题切换器，用于在深色模式和浅色模式之间切换的组件
- **Category_Filter**: 分类筛选器，根据AI相关关键词对文献进行分类的功能
- **Pagination_System**: 分页系统，控制每页显示文献数量的组件
- **Email_Notifier**: 邮件通知模块，负责发送新文献通知邮件的Python模块
- **AI_Keywords**: AI相关关键词列表，包含 "machine", "learn", "neural", "network"

## Requirements

### Requirement 1: 可折叠文献卡片

**User Story:** As a 用户, I want 文献以可折叠卡片形式展示, so that 我可以快速浏览大量文献并按需查看详情。

#### Acceptance Criteria

1. WHEN 页面加载完成, THE Literature_Card SHALL 默认以折叠状态显示，仅展示文章中文标题和期刊信息
2. WHEN 用户点击折叠状态的 Literature_Card, THE Literature_Card SHALL 展开显示完整信息，包括英文标题、中文摘要、发表时间和作者
3. WHEN 用户点击已展开的 Literature_Card, THE Literature_Card SHALL 折叠回默认状态
4. THE Literature_Card SHALL 在折叠和展开状态之间提供平滑的过渡动画

### Requirement 2: 分页系统调整

**User Story:** As a 用户, I want 每页显示50篇文献, so that 我可以在单页内浏览更多内容。

#### Acceptance Criteria

1. THE Pagination_System SHALL 每页显示50篇文献
2. WHEN 文献总数超过50篇, THE Pagination_System SHALL 显示分页导航控件
3. WHEN 用户切换页面, THE Pagination_System SHALL 平滑滚动到页面顶部

### Requirement 3: AI分类筛选功能

**User Story:** As a 用户, I want 按AI相关性筛选文献, so that 我可以快速找到AI相关或非AI相关的文献。

#### Acceptance Criteria

1. THE Category_Filter SHALL 提供三个筛选选项：全部、AI相关、AI无关
2. WHEN 文献标题或摘要包含 AI_Keywords 中任一关键词（machine, learn, neural, network）, THE Category_Filter SHALL 将该文献分类为"AI相关"
3. WHEN 文献标题和摘要均不包含 AI_Keywords 中任何关键词, THE Category_Filter SHALL 将该文献分类为"AI无关"
4. WHEN 用户选择筛选选项, THE Category_Filter SHALL 立即更新文献列表显示对应分类的文献
5. THE Category_Filter SHALL 对关键词匹配执行大小写不敏感的搜索

### Requirement 4: 深色/浅色主题切换

**User Story:** As a 用户, I want 在深色和浅色主题之间切换, so that 我可以根据环境和个人偏好选择舒适的阅读模式。

#### Acceptance Criteria

1. THE Theme_Switcher SHALL 提供深色模式和浅色模式两种主题
2. WHEN 用户点击 Theme_Switcher, THE Theme_Switcher SHALL 在两种主题之间切换
3. WHEN 主题切换时, THE Theme_Switcher SHALL 应用平滑的颜色过渡效果
4. THE Theme_Switcher SHALL 将用户的主题偏好保存到本地存储
5. WHEN 页面重新加载, THE Theme_Switcher SHALL 恢复用户之前选择的主题
6. IF 用户未设置主题偏好, THEN THE Theme_Switcher SHALL 默认使用浅色模式

### Requirement 5: 响应式设计优化

**User Story:** As a 用户, I want 页面在手机和电脑上都能良好显示, so that 我可以在任何设备上舒适地浏览文献。

#### Acceptance Criteria

1. WHEN 屏幕宽度小于768px, THE Literature_Card SHALL 调整为适合移动设备的单列布局
2. WHEN 屏幕宽度大于等于768px, THE Literature_Card SHALL 使用适合桌面设备的布局
3. THE 页面控件 SHALL 在所有屏幕尺寸下保持可用性和可读性
4. THE 字体大小 SHALL 在移动设备上保持足够的可读性（最小14px）
5. THE 触摸目标 SHALL 在移动设备上具有足够的点击区域（最小44px x 44px）

### Requirement 6: 页面美化

**User Story:** As a 用户, I want 页面更加美观, so that 我有更好的使用体验。

#### Acceptance Criteria

1. THE 页面 SHALL 使用现代化的视觉设计，包括圆角、阴影和渐变效果
2. THE 深色模式 SHALL 使用护眼的深色配色方案
3. THE 浅色模式 SHALL 使用清新明亮的配色方案
4. THE Literature_Card SHALL 在悬停时提供视觉反馈
5. THE 所有交互元素 SHALL 具有一致的视觉风格

### Requirement 7: 邮件发送Bug修复

**User Story:** As a 系统管理员, I want 邮件发送功能正常工作, so that 我可以收到新文献的通知。

#### Acceptance Criteria

1. WHEN 邮件配置完整且有效, THE Email_Notifier SHALL 成功发送邮件通知
2. IF SMTP连接失败, THEN THE Email_Notifier SHALL 记录详细的错误信息
3. IF 邮件发送失败, THEN THE Email_Notifier SHALL 提供有意义的错误提示
4. THE Email_Notifier SHALL 正确处理SSL/TLS连接
5. THE Email_Notifier SHALL 在发送前验证邮件配置的完整性

### Requirement 8: 快速预览增强

**User Story:** As a 用户, I want 快速预览文献关键信息, so that 我可以更高效地筛选感兴趣的文献。

#### Acceptance Criteria

1. THE Literature_Card SHALL 在折叠状态下显示AI分类标签（AI相关/AI无关）
2. THE Literature_Card SHALL 在折叠状态下显示发表日期
3. WHEN 用户悬停在折叠的 Literature_Card 上, THE Literature_Card SHALL 显示摘要预览提示框
4. THE 统计信息 SHALL 显示当前筛选条件下AI相关和AI无关文献的数量

### Requirement 9: 键盘快捷键支持

**User Story:** As a 用户, I want 使用键盘快捷键操作, so that 我可以更快速地浏览文献。

#### Acceptance Criteria

1. WHEN 用户按下 "j" 键, THE 页面 SHALL 聚焦到下一篇文献
2. WHEN 用户按下 "k" 键, THE 页面 SHALL 聚焦到上一篇文献
3. WHEN 用户按下 "Enter" 键且有文献被聚焦, THE Literature_Card SHALL 切换展开/折叠状态
4. WHEN 用户按下 "o" 键且有文献被聚焦, THE 页面 SHALL 在新标签页打开原文链接
5. WHEN 用户按下 "s" 键且有文献被聚焦, THE Literature_Card SHALL 切换收藏状态

### Requirement 10: 关键词高亮显示

**User Story:** As a 用户, I want 关键词在文献中高亮显示, so that 我可以快速定位匹配的内容。

#### Acceptance Criteria

1. WHEN 文献标题或摘要包含 AI_Keywords 中的关键词, THE 页面 SHALL 将匹配的关键词以粗体红色显示
2. THE 关键词高亮 SHALL 同时应用于中文和英文内容
3. THE 关键词高亮 SHALL 执行大小写不敏感的匹配
4. THE 关键词高亮 SHALL 在深色和浅色主题下都保持良好的可读性
