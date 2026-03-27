"""APS Multi-Agent 系统入口

通过MCP Server调用APS工具完成排程
"""

from __future__ import annotations
import logfire
import asyncio
import json
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openrouter import OpenRouterModelSettings, OpenRouterProviderConfig

logfire.configure()
logfire.instrument_pydantic_ai()

settings = OpenRouterModelSettings(
    temperature=0.0,
    max_tokens=10000,
    top_p=1.0,
    openrouter_provider=OpenRouterProviderConfig(
        require_parameters=True,
    )
)


class OrderPriority(str, Enum):
    deadline = "deadline"
    profit = "profit"
    inventory = "inventory"
    setup = "setup"
    throughput = "throughput"


class ConstraintType(str, Enum):
    machine_capacity = "machine_capacity"
    changeover = "changeover"
    due_date = "due_date"
    inventory_limit = "inventory_limit"
    machine_compatibility = "machine_compatibility"
    cleaning_required = "cleaning_required"
    batch_size = "batch_size"
    frozen_sequence = "frozen_sequence"


class ObjectiveWeights(BaseModel):
    minimize_lateness: float = Field(default=0.0, ge=0.0, le=1.0)
    maximize_profit: float = Field(default=0.0, ge=0.0, le=1.0)
    minimize_inventory: float = Field(default=0.0, ge=0.0, le=1.0)
    minimize_changeover: float = Field(default=0.0, ge=0.0, le=1.0)
    maximize_throughput: float = Field(default=0.0, ge=0.0, le=1.0)


class Constraint(BaseModel):
    type: ConstraintType
    description: str = Field(min_length=3)
    params: dict = Field(default_factory=dict)


class SolverConfig(BaseModel):
    horizon_hours: int = Field(default=72, ge=1, le=24 * 90)
    time_limit_seconds: int = Field(default=10, ge=1, le=300)
    use_cp_sat: bool = True
    objective_scale: int = Field(default=1000, ge=1, le=1_000_000)


class APSJob(BaseModel):
    job_id: str
    product: str
    quantity: int = Field(gt=0)
    due_in_hours: int | None = Field(default=None, ge=0)
    profit_priority: int | None = Field(default=None, ge=0, le=100)
    allowed_machines: list[str] = Field(default_factory=list)


class APSMachine(BaseModel):
    machine_id: str
    capacity_per_hour: int = Field(gt=0)
    supported_products: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    intent: str = "optimize_schedule"
    priorities: list[OrderPriority] = Field(default_factory=list)
    objective: ObjectiveWeights
    constraints: list[Constraint] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    solver_config: SolverConfig = Field(default_factory=SolverConfig)
    explanation: str = Field(min_length=10)


class APSInput(BaseModel):
    jobs: list[APSJob] = Field(default_factory=list)
    machines: list[APSMachine] = Field(default_factory=list)
    planner_output: PlannerOutput


MCP_SERVER = MCPServerStreamableHTTP('http://localhost:8800/mcp')


PlannerAgent = Agent(
    'openrouter:xiaomi/mimo-v2-flash',
    model_settings=settings,
    system_prompt="""你是工业APS排程Agent。你可以通过MCP工具来完成任务。

将用户排程请求转换为严格的结构化输出，用于下游APS求解器。

    始终只输出可执行的约束。
    不要输出模糊的语言。
    归一化目标权重，使总和 <= 1.0 且 > 0。
    当信息缺失时使用假设，而不是编造事实。
    优先使用求解器安全的解释。""",
    toolsets=[MCP_SERVER],
)


async def run_agent(user_input: str) -> dict:
    """运行Agent处理用户请求"""
    result = await PlannerAgent.run(user_input)
    if hasattr(result, 'output') and result.output is not None:
        if hasattr(result.output, 'model_dump'):
            return result.output.model_dump()
        return {}
    return {}


async def initialize_demo():
    """初始化演示数据"""
    from APS.mcp.tools import add_order, add_machine
    
    add_machine("L1", 2200, ["cola", "orange_juice"])
    add_machine("L2", 1600, ["cola", "milk"])
    
    add_order("O-1001", "cola", 10000, 48, 70, ["L1", "L2"])
    add_order("O-1002", "milk", 5000, 16, 50, ["L2"])
    add_order("O-1003", "orange_juice", 8000, 24, 60, ["L1"])


async def demo():
    """运行演示"""
    print("=" * 60)
    print("APS Multi-Agent 系统")
    print("=" * 60)
    
    print("\n[1] 初始化演示数据...")
    await initialize_demo()
    
    print("\n[2] 运行Agent...")
    user_input = "优先准时交付，同时别让库存爆掉，换线清洗成本也要考虑"
    result = await run_agent(user_input)
    
    print("\n[3] Agent输出:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("演示完成")
    print("=" * 60)


async def interactive():
    """交互模式"""
    print("APS Multi-Agent 交互模式 (输入 'quit' 退出)")
    print("-" * 40)
    
    await initialize_demo()
    
    while True:
        try:
            user_input = input("\n请输入排程需求: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            print("\n处理中...")
            result = await run_agent(user_input)
            
            print("\n结果:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n错误: {e}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        asyncio.run(interactive())
    else:
        asyncio.run(demo())
