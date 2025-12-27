# Implementation Plan: Literature UI Advanced Features

## Overview

本实现计划将高级UI功能分解为可执行的任务，按照从基础到高级的顺序实现。每个任务都关联到具体的需求，并包含必要的测试。

## Tasks

- [-] 1. 实现布局管理器
  - [x] 1.1 创建 LayoutManager 类
    - 实现三种布局模式：list, grid, compact
    - 添加布局切换逻辑
    - 实现 localStorage 持久化
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_
  
  - [x] 1.2 添加布局切换UI
    - 在控制面板添加布局切换按钮
    - 添加图标和工具提示
    - 实现平滑过渡动画
    - _Requirements: 1.7, 1.10_
  
  - [x] 1.3 实现响应式网格布局
    - 根据屏幕宽度调整列数
    - 添加媒体查询
    - 测试不同屏幕尺寸
    - _Requirements: 1.9_
  
  - [x] 1.4 保持滚动位置
    - 在布局切换时记录滚动位置
    - 切换后恢复位置
    - _Requirements: 1.8_
  
  - [ ] 1.5 编写布局管理器测试

    - 测试布局切换功能
    - 测试持久化
    - 测试响应式行为
    - **Property 1: Layout Persistence**
    - **Validates: Requirements 1.5, 1.6**

- [ ] 2. 实现字体大小调节
  - [x] 2.1 创建 FontManager 类
    - 定义五个字体大小级别
    - 实现增大/减小/重置功能
    - 使用 CSS 自定义属性
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.10_
  
  - [x] 2.2 添加字体调节UI
    - 添加字体大小控制按钮
    - 显示当前字体大小级别
    - 添加视觉反馈
    - _Requirements: 2.7_
  
  - [x] 2.3 实现键盘快捷键
    - 监听 Ctrl/Cmd + Plus/Minus
    - 实现字体大小调节
    - _Requirements: 2.4_
  
  - [x] 2.4 实现字体大小边界检查
    - 限制最小值 12px
    - 限制最大值 24px
    - 调整行高
    - _Requirements: 2.8, 2.9_
  
  - [ ] 2.5 编写字体管理器测试

    - 测试字体大小调节
    - 测试边界条件
    - **Property 2: Font Size Bounds**
    - **Validates: Requirements 2.8**

- [ ] 3. 实现快捷键自定义
  - [x] 3.1 创建 ShortcutManager 类
    - 定义默认快捷键映射
    - 实现快捷键注册/注销
    - 实现冲突检测
    - _Requirements: 3.1, 3.3, 3.4, 3.5, 3.6, 3.9_
  
  - [x] 3.2 创建快捷键配置面板
    - 显示所有可用快捷键
    - 实现编辑模式
    - 显示冲突警告
    - _Requirements: 3.2, 3.10_
  
  - [x] 3.3 实现快捷键持久化
    - 保存到 localStorage
    - 加载自定义快捷键
    - 提供重置功能
    - _Requirements: 3.7, 3.8_
  
  - [ ] 3.4 编写快捷键管理器测试

    - 测试快捷键注册
    - 测试冲突检测
    - **Property 3: Shortcut Uniqueness**
    - **Validates: Requirements 3.5, 3.6**

- [ ] 4. 实现文献预览增强
  - [x] 4.1 创建 PreviewSystem 类
    - 实现悬停检测（500ms 延迟）
    - 创建预览工具提示
    - 实现智能定位
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
  
  - [x] 4.2 设计预览工具提示样式
    - 显示完整摘要（中英文）
    - 显示作者和日期
    - 添加滚动支持
    - 设置最大宽度 600px
    - _Requirements: 4.3, 4.7, 4.8_
  
  - [x] 4.3 实现移动端检测
    - 在触摸设备上禁用预览
    - _Requirements: 4.6_
  
  - [x] 4.4 添加搜索词高亮
    - 在预览中高亮搜索词
    - _Requirements: 4.9_
  
  - [ ] 4.5 编写预览系统测试

    - 测试悬停延迟
    - 测试定位逻辑
    - 测试移动端禁用

- [x] 5. 实现虚拟滚动
  - [ ] 5.1 创建 VirtualScrollManager 类
    - 实现可见范围计算
    - 实现动态渲染
    - 添加缓冲区（10项）
    - _Requirements: 5.1, 5.2, 5.4, 5.10_
  
  - [ ] 5.2 实现滚动监听
    - 监听滚动事件
    - 更新可见范围
    - 优化性能（节流）
    - _Requirements: 5.3_
  
  - [ ] 5.3 实现动态高度计算
    - 缓存每项高度
    - 处理可变高度卡片
    - _Requirements: 5.6_
  
  - [ ] 5.4 保持滚动位置
    - 在筛选/排序时保持位置
    - 实现 scrollToIndex
    - _Requirements: 5.5, 5.7_
  
  - [ ] 5.5 集成键盘导航
    - 确保虚拟滚动支持键盘导航
    - _Requirements: 5.8_
  
  - [ ] 5.6 编写虚拟滚动测试

    - 测试大数据集（1000+ 项）
    - 测试可见范围计算
    - **Property 4: Virtual Scroll Consistency**
    - **Validates: Requirements 5.2, 5.4, 5.10**

- [ ] 6. 实现图片懒加载
  - [ ] 6.1 创建 LazyLoadManager 类
    - 使用 Intersection Observer API
    - 实现图片加载逻辑
    - 添加占位符
    - _Requirements: 6.1, 6.2, 6.3, 6.5_
  
  - [ ] 6.2 实现预加载
    - 预加载视口附近 200px 的图片
    - _Requirements: 6.6_
  
  - [ ] 6.3 实现错误处理
    - 显示失败占位符
    - 提供重试功能
    - _Requirements: 6.4, 6.10_
  
  - [ ] 6.4 支持多种图片类型
    - 期刊 logo
    - 作者头像
    - _Requirements: 6.7_
  
  - [ ] 6.5 编写懒加载测试

    - 测试 Intersection Observer
    - 测试预加载逻辑
    - **Property 8: Lazy Load Coverage**
    - **Validates: Requirements 6.2, 6.6**

- [ ] 7. 实现增量加载
  - [ ] 7.1 创建 IncrementalLoader 类
    - 实现分批加载（每批 50 项）
    - 跟踪加载状态
    - 实现自动加载
    - _Requirements: 7.1, 7.2, 7.8, 7.10_
  
  - [ ] 7.2 添加加载指示器
    - 显示加载中状态
    - 显示"已加载全部"消息
    - _Requirements: 7.3, 7.4_
  
  - [ ] 7.3 实现"加载更多"按钮
    - 作为自动加载的替代
    - _Requirements: 7.6_
  
  - [ ] 7.4 实现错误处理
    - 显示重试按钮
    - 防止重复请求
    - _Requirements: 7.7_
  
  - [ ] 7.5 保持筛选和排序
    - 在批次间保持设置
    - 保持滚动位置
    - _Requirements: 7.5, 7.9_
  
  - [ ] 7.6 编写增量加载测试

    - 测试批次加载
    - 测试完整性
    - **Property 6: Incremental Loading Completeness**
    - **Validates: Requirements 7.1, 7.2, 7.5**

- [ ] 8. 实现搜索结果缓存
  - [ ] 8.1 创建 CacheManager 类
    - 实现 LRU 缓存
    - 设置最大容量 50
    - 实现缓存键生成
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6_
  
  - [ ] 8.2 实现缓存失效
    - 在新文献添加时失效
    - _Requirements: 8.5_
  
  - [ ] 8.3 添加缓存统计
    - 显示命中率
    - 显示缓存大小
    - _Requirements: 8.7, 8.8_
  
  - [ ] 8.4 实现手动清除
    - 提供清除缓存按钮
    - _Requirements: 8.9_
  
  - [ ] 8.5 使用 sessionStorage
    - 持久化到会话存储
    - _Requirements: 8.10_
  
  - [ ] 8.6 编写缓存管理器测试

    - 测试 LRU 逻辑
    - 测试缓存失效
    - **Property 5: Cache LRU Ordering**
    - **Validates: Requirements 8.4**

- [ ] 9. 实现移动端专属布局
  - [ ] 9.1 创建 MobileAdapter 类
    - 检测移动设备
    - 激活移动布局
    - _Requirements: 9.1, 9.2_
  
  - [ ] 9.2 实现滑动手势
    - 左滑显示操作按钮
    - 右滑标记已读
    - _Requirements: 9.3, 9.4, 9.5_
  
  - [ ] 9.3 创建底部导航栏
    - 替换侧边栏
    - 优化触摸目标（44x44px）
    - _Requirements: 9.6, 9.8_
  
  - [ ] 9.4 实现下拉刷新
    - 添加 pull-to-refresh
    - _Requirements: 9.7_
  
  - [ ] 9.5 优化移动端显示
    - 隐藏次要信息
    - 支持捏合缩放
    - _Requirements: 9.9, 9.10_
  
  - [ ] 9.6 编写移动端适配测试

    - 测试设备检测
    - 测试手势识别
    - **Property 7: Mobile Detection Consistency**
    - **Validates: Requirements 9.1**

- [ ] 10. 实现研究趋势预测
  - [ ] 10.1 创建 TrendPredictor 类
    - 分析历史数据
    - 计算增长率
    - 实现线性回归预测
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ] 10.2 识别新兴和衰退主题
    - 识别快速增长主题
    - 识别负增长主题
    - _Requirements: 10.6, 10.7_
  
  - [ ] 10.3 计算置信度
    - 基于数据量和趋势稳定性
    - _Requirements: 10.4_
  
  - [ ] 10.4 可视化趋势预测
    - 创建趋势折线图
    - 显示置信区间
    - 比较 AI vs 非AI 趋势
    - _Requirements: 10.5, 10.8_
  
  - [ ] 10.5 添加预测说明
    - 解释每个预测
    - _Requirements: 10.10_
  
  - [ ] 10.6 编写趋势预测测试

    - 测试增长率计算
    - 测试预测准确性
    - **Property 9: Trend Prediction Monotonicity**
    - **Validates: Requirements 10.2, 10.3**

- [ ] 11. 实现研究主题演化分析
  - [ ] 11.1 创建 TopicEvolutionAnalyzer 类
    - 创建时间切片
    - 提取每个时期的主题
    - _Requirements: 11.1, 11.2_
  
  - [ ] 11.2 计算主题相似度
    - 实现相似度算法
    - 跟踪主题演化
    - _Requirements: 11.6_
  
  - [ ] 11.3 识别主题合并和分裂
    - 检测主题合并
    - 检测主题分裂
    - _Requirements: 11.3, 11.4_
  
  - [ ] 11.4 确定主题生命周期
    - 分类：新兴、增长、成熟、衰退
    - _Requirements: 11.5_
  
  - [ ] 11.5 可视化主题演化
    - 创建 Sankey 图或流图
    - 添加时间轴滑块
    - 显示共现模式
    - _Requirements: 11.2, 11.8, 11.9_
  
  - [ ] 11.6 识别突破性论文
    - 标记引入新主题的论文
    - _Requirements: 11.7_
  
  - [ ] 11.7 导出演化数据
    - 支持 CSV 导出
    - _Requirements: 11.10_
  
  - [ ] 11.8 编写主题演化测试

    - 测试时间切片
    - 测试主题跟踪
    - **Property 10: Topic Evolution Continuity**
    - **Validates: Requirements 11.1, 11.2**

- [ ] 12. 集成和优化
  - [x] 12.1 集成所有功能到主应用
    - 更新 app.js
    - 添加初始化代码
    - 确保功能协同工作
  
  - [ ] 12.2 性能优化
    - 优化虚拟滚动性能
    - 优化缓存策略
    - 减少重绘和回流
  
  - [ ] 12.3 更新样式表
    - 添加新布局样式
    - 添加移动端样式
    - 添加过渡动画
  
  - [ ] 12.4 更新文档
    - 更新 README.md
    - 添加功能说明
    - 添加使用指南
  
  - [ ] 12.5 端到端测试

    - 测试完整用户流程
    - 测试功能交互
    - 性能基准测试

- [ ] 13. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，询问用户是否有问题

## Notes

- 任务标记 `*` 的为可选测试任务
- 每个任务都关联到具体需求以便追溯
- 虚拟滚动和增量加载是性能关键功能，需要特别关注
- 移动端功能需要在真实设备上测试
- 趋势预测和主题演化需要足够的历史数据
- 建议分阶段实现：先基础功能（1-4），再性能优化（5-8），最后高级分析（9-11）
