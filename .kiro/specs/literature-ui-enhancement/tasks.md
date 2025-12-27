# Implementation Plan: Literature UI Enhancement

## Overview

本实现计划将文献追踪系统的前端页面进行全面升级，包括可折叠卡片、AI分类筛选、主题切换、响应式设计、键盘快捷键、关键词高亮，以及后端邮件发送bug修复。

## Tasks

- [x] 1. 重构CSS样式系统，支持主题切换
  - [x] 1.1 创建CSS变量系统，定义浅色和深色主题的设计令牌
    - 定义颜色、阴影、边框等CSS变量
    - 使用 `[data-theme="dark"]` 选择器定义深色主题
    - _Requirements: 4.1, 6.1, 6.2, 6.3_
  - [x] 1.2 添加关键词高亮样式
    - 定义 `.keyword-highlight` 类，粗体红色
    - 确保深色模式下可读性
    - _Requirements: 10.1, 10.4_
  - [x] 1.3 优化响应式布局
    - 添加移动端断点样式（< 768px）
    - 确保触摸目标足够大（44px x 44px）
    - 优化字体大小（最小14px）
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 2. 实现可折叠文献卡片组件
  - [x] 2.1 重构 `createArticleCard` 函数，支持折叠/展开状态
    - 折叠状态：显示中文标题、期刊、日期、AI标签
    - 展开状态：显示完整信息（英文标题、摘要、作者等）
    - _Requirements: 1.1, 1.2, 8.1, 8.2_
  - [x] 2.2 实现 `toggleCardExpansion` 函数
    - 管理展开状态的Set
    - 添加展开/折叠动画
    - _Requirements: 1.2, 1.3, 1.4_
  - [ ]* 2.3 编写卡片切换一致性属性测试
    - **Property 1: Card Toggle Consistency**
    - **Validates: Requirements 1.2, 1.3**

- [x] 3. 实现AI分类筛选功能
  - [x] 3.1 实现 `isAIRelated` 分类函数
    - 检查标题和摘要中的AI关键词
    - 大小写不敏感匹配
    - _Requirements: 3.2, 3.3, 3.5_
  - [x] 3.2 添加分类筛选UI控件
    - 添加"全部/AI相关/AI无关"筛选选项
    - 更新统计信息显示分类数量
    - _Requirements: 3.1, 8.4_
  - [x] 3.3 实现 `filterByCategory` 筛选函数
    - 根据选择的分类筛选文献列表
    - _Requirements: 3.4_
  - [ ]* 3.4 编写AI分类正确性属性测试

    - **Property 3: AI Classification Correctness**
    - **Validates: Requirements 3.2, 3.3, 3.5**
  - [ ]* 3.5 编写分类筛选完整性属性测试

    - **Property 4: Category Filter Completeness**
    - **Validates: Requirements 3.4**

- [x] 4. 实现关键词高亮功能
  - [x] 4.1 实现 `highlightKeywords` 函数
    - 使用正则表达式匹配关键词
    - 包装为高亮span元素
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 4.2 在卡片渲染中应用关键词高亮
    - 高亮标题和摘要中的关键词
    - _Requirements: 10.1, 10.2_
  - [ ]* 4.3 编写关键词高亮完整性属性测试

    - **Property 9: Keyword Highlighting Completeness**
    - **Validates: Requirements 10.1, 10.2, 10.3**

- [x] 5. 实现主题切换功能
  - [x] 5.1 实现主题管理函数
    - `getCurrentTheme()` - 获取当前主题
    - `setTheme(theme)` - 设置主题
    - `toggleTheme()` - 切换主题
    - `initTheme()` - 初始化主题
    - _Requirements: 4.1, 4.2, 4.4, 4.5, 4.6_
  - [x] 5.2 添加主题切换按钮UI
    - 在页面头部添加切换按钮
    - 显示当前主题图标（太阳/月亮）
    - _Requirements: 4.2, 4.3_
  - [ ]* 5.3 编写主题持久化往返属性测试

    - **Property 5: Theme Persistence Round-Trip**
    - **Validates: Requirements 4.4, 4.5**
  - [ ]* 5.4 编写主题切换幂等性属性测试

    - **Property 6: Theme Toggle Idempotence**
    - **Validates: Requirements 4.2**

- [x] 6. 更新分页系统
  - [x] 6.1 修改 PAGE_SIZE 为 50
    - 更新分页逻辑
    - _Requirements: 2.1_
  - [x] 6.2 优化分页导航UI
    - 确保分页控件在移动端可用
    - _Requirements: 2.2, 2.3_
  - [ ]* 6.3 编写分页大小约束属性测试

    - **Property 2: Pagination Size Constraint**
    - **Validates: Requirements 2.1**

- [x] 7. 实现键盘快捷键支持
  - [x] 7.1 实现键盘导航函数
    - `focusNext()` / `focusPrev()` - 上下导航
    - `toggleFocused()` - 展开/折叠
    - `openFocused()` - 打开原文
    - `starFocused()` - 收藏
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [x] 7.2 添加键盘事件监听器
    - 监听 j/k/Enter/o/s 按键
    - 添加聚焦状态视觉反馈
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  - [ ] 7.3 编写键盘导航边界属性测试

    - **Property 8: Keyboard Navigation Bounds**
    - **Validates: Requirements 9.1, 9.2**

- [x] 8. 实现悬停预览功能
  - [x] 8.1 实现预览提示框组件
    - 创建tooltip元素
    - 显示摘要预览
    - _Requirements: 8.3_
  - [x] 8.2 添加悬停事件处理
    - 鼠标悬停显示tooltip
    - 鼠标离开隐藏tooltip
    - _Requirements: 8.3_

- [x] 9. 更新HTML结构
  - [x] 9.1 更新 index.html
    - 添加主题切换按钮
    - 添加分类筛选控件
    - 添加tooltip容器
    - 更新统计信息区域
    - _Requirements: 3.1, 4.1, 8.4_

- [-] 10. 修复邮件发送Bug
  - [x] 10.1 添加邮件配置验证函数
    - 验证所有必需字段
    - 返回详细错误信息
    - _Requirements: 7.5_
  - [x] 10.2 增强错误处理
    - 捕获SMTP连接错误
    - 捕获认证错误
    - 记录详细错误日志
    - _Requirements: 7.2, 7.3, 7.4_
  - [ ] 10.3 编写邮件配置验证属性测试

    - **Property 7: Email Config Validation**
    - **Validates: Requirements 7.5**

- [x] 11. Checkpoint - 功能测试
  - 确保所有功能正常工作
  - 测试深色/浅色主题切换
  - 测试响应式布局
  - 测试键盘快捷键
  - 如有问题请告知

- [x] 12. 最终优化和清理
  - [x] 12.1 代码清理和注释
    - 添加必要的代码注释
    - 移除调试代码
  - [x] 12.2 性能优化
    - 优化DOM操作
    - 减少重绘重排

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快MVP开发
- 每个属性测试应运行至少100次迭代
- 前端使用 Vanilla JavaScript，无需额外框架
- 后端邮件模块使用 Python smtplib
