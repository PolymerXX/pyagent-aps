"""规划Agent - 将用户请求转换为优化参数"""

from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.core.config import get_settings
from aps.models.optimization import (
    OptimizationParams,
    OptimizationStrategy,
    ObjectiveWeights,
)
from aps.agents.base import create_model_settings, BaseAPSAgent, AgentContext


class PlannerOutput(BaseModel):
    """规划Agent输出"""

    strategy: OptimizationStrategy = Field(
        default=OptimizationStrategy.BALANCED, description="优化策略"
    )
    weights: ObjectiveWeights = Field(
        default_factory=ObjectiveWeights, description="目标权重"
    )
    time_limit_seconds: int = Field(default=60, description="求解时间限制")
    allow_delays: bool = Field(default=True, description="是否允许延期")
    max_delay_hours: float = Field(default=24.0, description="最大延期小时数")
    priority_orders: List[str] = Field(
        default_factory=list, description="优先处理的订单ID"
    )
    frozen_assignments: List[str] = Field(
        default_factory=list, description="冻结的分配（不调整）"
    )
    explanation: str = Field(default="", description="规划决策说明")

    def to_optimization_params(self) -> OptimizationParams:
        """转换为优化参数"""
        return OptimizationParams(
            strategy=self.strategy,
            weights=self.weights,
            time_limit_seconds=self.time_limit_seconds,
            allow_delays=self.allow_delays,
            max_delay_hours=self.max_delay_hours,
        )


class PlannerAgent(BaseAPSAgent):
    """规划Agent"""

    def __init__(self):
        config = get_settings()
        settings = create_model_settings(temperature=0.0)

        super().__init__(
            model=config.default_model,
            settings=settings,
            instructions=self._get_instructions(),
            output_type=PlannerOutput,
        )

    def _get_instructions(self) -> str:
        return """你是APS生产排程系统的规划Agent。

你的职责是将用户的排程请求转换为结构化的优化参数。

**分析用户输入**：
- "交期"、"准时"、"不延误" → ON_TIME_DELIVERY策略
- "换产"、"清洗"、"切换" → MINIMIZE_CHANGEOVER策略
- "利润"、"收益" → MAXIMIZE_PROFIT策略
- "产能"、"利用率" → MAXIMIZE_UTILIZATION策略
- 没有明确偏好 → BALANCED策略

**设置权重**：
根据用户偏好调整各目标的权重，确保权重总和为1.0。

**输出要求**：
- strategy: 优化策略
- weights: 目标权重
- time_limit_seconds: 求解时间限制（通常60秒足够）
- explanation: 简要说明决策理由
"""

    async def run(
        self, user_input: str, context: Optional[AgentContext] = None
    ) -> PlannerOutput:
        """运行规划Agent"""
        prompt = self._build_prompt(user_input, context)
        result = await self.agent.run(prompt)
        return result.data

    def _build_prompt(self, user_input: str, context: Optional[AgentContext]) -> str:
        """构建提示"""
        parts = []

        if context:
            if context.orders_info:
                parts.append(f"## 订单信息\n{context.orders_info}")
            if context.machines_info:
                parts.append(f"## 机器信息\n{context.machines_info}")

        parts.append(f"## 用户请求\n{user_input}")

        return "\n\n".join(parts)
