"""异常处理Agent"""

from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.agents.base import create_model_settings
from aps.core.config import get_settings


class ExceptionType(str, Enum):
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    NO_MACHINE = "no_machine"
    CAPACITY_EXCEEDED = "capacity"
    CONSTRAINT_CONFLICT = "conflict"
    UNKNOWN = "unknown"


class ExceptionAnalysis(BaseModel):
    """异常分析结果"""

    exception_type: ExceptionType = Field(default=ExceptionType.UNKNOWN)
    root_cause: str = Field(default="")
    affected_orders: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    severity: int = Field(default=1, ge=1, le=5)


class ExceptionAgent:
    """异常处理Agent"""

    def __init__(self):
        config = get_settings()
        self.settings = create_model_settings(temperature=0.2)

        self.agent = Agent(
            config.default_model,
            model_settings=self.settings,
            instructions=self._get_instructions(),
            output_type=ExceptionAnalysis,
        )

    def _get_instructions(self) -> str:
        return """你是APS系统的异常处理专家。

当排产失败或出现问题时，你需要：
1. 诊断问题类型和根本原因
2. 识别受影响的订单
3. 提供可行的解决方案

**常见问题诊断**：
1. 无可行解：约束太严格
2. 超时：问题规模大
3. 无可用机器：产品类型不匹配
4. 产能超限：订单总量超产能
5. 约束冲突：多个约束矛盾
"""

    async def analyze(
        self, error_message: str, context: dict | None = None
    ) -> ExceptionAnalysis:
        """分析异常"""
        prompt = self._build_prompt(error_message, context)
        result = await self.agent.run(prompt)
        return result.output

    def _build_prompt(self, error_message: str, context: dict | None) -> str:
        parts = [f"## 错误信息\n{error_message}"]

        if context:
            if "orders" in context:
                parts.append(f"## 订单信息\n{context['orders']}")
            if "machines" in context:
                parts.append(f"## 机器信息\n{context['machines']}")

        parts.append("\n请分析这个排产问题的原因并提供解决方案。")
        return "\n\n".join(parts)
