## APS项目应用于现实业务的8大核心问题分析（2026-03-29）

### 问题一：CP-SAT求解器建模严重不足 — 约束缺失导致结果不可用
- 文件: engine/cp_sat_solver.py
- 换产时间始终返回0.0从未建模，ChangeoverRule数据结构已完备但求解器未使用
- ProductionConstraints定义了max_daily_hours/max_consecutive_hours但求解器完全没使用
- Order.min_start_time存在于模型但求解器从未加入约束
- PlannerOutput.frozen_assignments存在但求解器完全忽略
- 不支持订单拆分（AddExactlyOne禁止多机器并行）

### 问题二：Cache和Profiler是死代码 — 从未接入实际求解流程
- APSSolver中_use_cache/_profiler从未在solve()中使用
- enable_cache()和set_profiler()无任何调用点

### 问题三：数据适配器是纸面实现 — 无法对接真实ERP/MES
- 所有适配器_parse_order硬编码product_type=ProductType.COLA（枚举里根本没有COLA）
- RESTAdapter在HTTPError时静默返回空列表
- push_schedule()只简单dump JSON无确认机制

### 问题四：多Agent流程的LLM依赖导致生产级不可靠
- 串行5个LLM Agent延迟10-50秒
- ValidatorAgent用LLM验证确定性约束可能产生幻觉
- AdjusterAgent是完全重新求解而非增量调整

### 问题五：时间模型过于简化 — 无法表达真实生产日历
- 使用相对小时数无日历/班次/假日概念

### 问题六：MCP工具层和Agent层完全割裂
- MCP用_global_state字典，Agent用APSSystem实例变量互不共享
- MCP的add_machine忽略了supported_products参数

### 问题七：缺少订单拆分产能瓶颈分析和What-If场景
### 问题八：并发和持久化缺失

### 最优先修复：在CP-SAT中加入换产时间约束，数据结构已完备只需建模时使用
