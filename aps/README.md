# APS - Multi-Agent Advanced Planning and Scheduling System

智能生产排程系统，基于 LLM 多智能体 + 约束求解器混合架构，面向制造业（饮料/乳制品/果汁）。

## 分层架构

```
┌─────────────────────────────────────────────────┐
│                  UI 层 (Streamlit)               │
│  app.py · state.py · 5个页面 · gantt/metrics    │
├─────────────────────────────────────────────────┤
│              MCP 工具层 (对外接口)                │
│  registry.py (注册表) · tools.py (14个工具)      │
├─────────────────────────────────────────────────┤
│            Agent 协作层 (多智能体)                │
│  orchestrator → planner → scheduler → validator  │
│                → adjuster → explainer → monitor  │
├─────────────────────────────────────────────────┤
│              求解引擎层 (Engine)                  │
│  solver.py → cp_sat_solver.py (OR-Tools)         │
│  profiler.py · cache.py                          │
├─────────────────────────────────────────────────┤
│            领域模型层 (Models)                    │
│  Order · Product · ProductionLine · Constraint   │
│  ScheduleResult · OptimizationParams             │
├─────────────────────────────────────────────────┤
│          基础设施层 (Adapters + Core)             │
│  REST · Database(SQLite) · File(JSON) · Config   │
└─────────────────────────────────────────────────┘
```

## 核心模块

| 模块 | 核心类/文件 | 职责 |
|------|-----------|------|
| `models/` | `Order`, `Product`, `ProductionLine`, `ProductionConstraints`, `ScheduleResult`, `OptimizationParams` | Pydantic 领域模型 |
| `engine/` | `APSSolver` → `CPSATSolver` | 双引擎：OR-Tools CP-SAT（最优解）+ 启发式回退 |
| `engine/profiler.py` | `Profiler`, `PerformanceMetrics` | 求解性能监控 |
| `engine/cache.py` | `SolverCache` | MD5 键 + TTL 的 LRU 求解结果缓存 |
| `agents/orchestrator.py` | `APSSystem`, `OrchestratorAgent` | 系统主入口，编排 7 个 Agent 协作 |
| `agents/base.py` | `BaseAPSAgent`, `AgentContext` | Agent 基类，封装 pydantic-ai |
| `agents/planner.py` | `PlannerAgent` → `PlannerOutput` | 自然语言 → 优化参数 |
| `agents/scheduler.py` | `SchedulerAgent` | 调用求解引擎执行排产 |
| `agents/validator.py` | `ValidatorAgent` → `ValidationResult` | 约束满足 + 质量评分 + 风险识别 |
| `agents/adjuster.py` | `AdjusterAgent` | 处理实时变更（新订单/故障/订单修改） |
| `agents/explainer.py` | `ExplainAgent` | 生成排程结果的可读解释 |
| `agents/monitor.py` | `MonitorAgent` → `MonitorReport` | 实时监控 + 告警 |
| `agents/exception_handler.py` | `ExceptionAgent` | 异常诊断（无可行解/超时等） |
| `adapters/` | `RESTAdapter`, `DatabaseAdapter`, `FileAdapter` | 数据源适配，统一 Protocol 接口 |
| `mcp/` | `MCPToolRegistry`, `tools.py` | 14 个 MCP 工具，供外部 LLM 调用 |
| `realtime/` | `RealtimeMonitor`, `RealtimeAdjuster` | 轻量级实时监控/调整（非 LLM） |
| `ui/` | `AppState` + 5 页面 + Gantt 图 | Streamlit Web UI |
| `core/config.py` | `Settings` | pydantic-settings 配置，`APS_` 前缀环境变量 |

## Agent 协作流程

```
用户请求
  │
  ▼
OrchestratorAgent ── 意图分析 → OrchestratorResponse
  │
  ▼
PlannerAgent ── 参数规划 → PlannerOutput → OptimizationParams
  │
  ▼
SchedulerAgent ── APSSolver.solve() → ScheduleResult
  │
  ▼
ValidatorAgent ── 约束/质量验证 → ValidationResult
  │                              │
  │          is_valid=False      │ is_valid=True
  ▼                              ▼
AdjusterAgent (最多3次)    ExplainAgent → ScheduleExplanation
  │                              │
  └──────────────────────────────▼
                                 ▼
                          MonitorAgent → MonitorReport
```

## 求解引擎

- **OR-Tools CP-SAT**（优先）：构建整数规划模型（`NoOverlap`, `AddExactlyOne`），支持 makespan 最小化和 total_delay 最小化
- **启发式回退**：按交期排序（EDD），贪心分配到最早可用机器，考虑换产时间
- 所有 Agent 均有**非 LLM 后备逻辑**，确保 LLM 不可用时系统仍可运行

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| 数据模型 | Pydantic v2 |
| LLM Agent | pydantic-ai (OpenRouter) |
| 约束求解 | OR-Tools CP-SAT |
| Web UI | Streamlit + Plotly |
| 数据适配 | httpx (REST), sqlite3, JSON |
| 配置 | pydantic-settings (.env) |
| 工具链 | pytest, ruff, mypy, hatch |

## 设计特点

1. **LLM + 算法混合**：Agent 层用 LLM 做意图理解和解释，Engine 层用确定性算法做约束求解
2. **优雅降级**：每个 Agent 都有 `quick_*` / `_generate_*` 后备方法
3. **双入口**：`APSSystem`（多 Agent 流程）和 `APSSolver`（纯算法）可独立使用
4. **MCP 标准接口**：14 个工具覆盖订单/机器/约束/排程全生命周期
5. **适配器模式**：REST/DB/File 统一接口，支持 `CompositeAdapter` 组合

## 可观测性 (Logfire)

通过 [Pydantic Logfire](https://pydantic.dev/logfire) 监控所有 Agent 的 LLM 调用。项目依赖已包含 `logfire`（提供 `instrument_pydantic_ai`），使用统一入口：

```python
from aps.core.logfire_setup import init_logfire

init_logfire()
```

`instrument_pydantic_ai()` 会全局挂钩所有 `pydantic_ai.Agent` 的运行，无需改各 Agent 源码。

### 配置

- `LOGFIRE_TOKEN`：从 [logfire.pydantic.dev](https://logfire.pydantic.dev) 获取；未设置时不会向云端发送（`send_to_logfire='if-token-present'`），本地仍可控制台输出。
- `APS_LOGFIRE_ENABLED`：默认 `true`，设为 `false` 可完全跳过 Logfire（见 `core/config.py`）。

### 初始化位置

- **Streamlit UI**：已在 [`ui/app.py`](ui/app.py) 启动路径就绪后自动调用 `init_logfire()`。
- **库 / 脚本 / Notebook**：在首次创建或运行 Agent **之前**手动调用一次 `init_logfire()`。

## 快速开始

```bash
# 安装依赖
pip install -e ".[dev]"

# 配置 Logfire（可选）
export LOGFIRE_TOKEN="your-token-here"

# 启动 UI
streamlit run ui/app.py

# 运行测试
pytest
```
