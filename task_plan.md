# Task Plan: 激光指向误差分析系统 - 温度与误差关系分析

## Goal
完成每个终端的激光指向误差与在轨温度关系分析，包括：
- **单独分析**：每颗星的每个终端的温度-误差关系（前光路/后光路/载荷温度）
- **联合分析**：同一颗星的多个终端的温度-误差关系对比
- **链路分析**：32-31和31-61链路的温度-误差交叉分析

## Current Phase
Phase 3

## Phases

### Phase 1: Requirements & Discovery
- [x] Understand user intent
- [x] Identify constraints and requirements
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Planning & Structure
- [x] Define technical approach
- [x] Create project structure if needed
- [x] Document decisions with rationale
- **Status:** complete

### Phase 3: Implementation
- [x] 创建卫星分组配置文件 (`src/config/satellite_groups.py`)
- [x] 创建 jg02 终端配置
- [x] 重构 verify_complete.py，支持动态配置
- [x] 同步修改其他脚本
- [x] 删除需求文档中的链路配对分析章节
- [x] 完成31-32和31-61链路重点终端分析
- [x] **当前分支不考虑7天数据处理**
- [x] 实现温度参数配置文件 (`src/config/temperature_params.py`)
- [x] 实现温度与误差关系分析模块（每个终端单独分析）
- [x] 增强可视化功能（温度变化率、频谱分析、温度梯度）
- **Status:** complete

### Phase 4: Testing & Verification
- [x] 验证 jg01 和 jg02 组卫星参数映射加载
- [x] 验证终端配置切换（确认jg02组无B1、B2）
- [x] 验证误差计算正确性
- [x] 验证所有终端温度参数提取：
  - 31star：B1、B2、A1-1、A1-2
  - 32star：B1、B2、A1-1
  - 61star：A1-1、A2-1、A2-2、A1-2
- [x] 完整流程测试所有终端数据处理
- [x] 验证每个终端单独分析功能
- [x] 验证温度与误差关系分析
- [x] 验证32-31和31-61链路温度-误差交叉分析
- **Status:** complete

### Phase 5: Delivery
- [x] 整理所有文档
- [x] 确保所有功能正常运行
- [x] 生成每个终端的分析报告
- [x] 生成联合分析报告
- [x] 生成链路分析报告
- **Status:** complete

### Phase 5: Delivery
- [ ] 整理所有文档
- [ ] 确保所有功能正常运行
- [ ] 生成每个终端的分析报告
- [ ] 生成联合分析报告
- [ ] 生成链路分析报告
- **Status:** pending

## Key Questions
1. 如何确保每个终端的温度-误差关系分析全面且准确？
2. 如何更有效地展示同一颗星多个终端的对比结果？
3. 如何优化链路分析的可视化效果？

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 创建 satellite_groups.py 配置文件 | 实现卫星分组和动态配置加载 |
| 重构 verify_complete.py | 支持动态加载参数映射和终端配置 |
| 删除需求文档中的链路配对分析章节 | 简化分析流程，重点关注31-32和31-61链路 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| 32star激光A终端无数据 | 1 | 修改终端配置，使用13B包而非134包 |
| A1-1和A1-2参数匹配错误 | 2 | 优化find_column函数，优先匹配包含"目标"或"当前"关键字的列名 |

## Notes
- 更新phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions
- Log ALL errors - they help avoid repetition