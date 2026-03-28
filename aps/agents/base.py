"""基础Agent配置"""

from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models.openrouter import OpenRouterModelSettings

from aps.core.config import get_settings


def create_model_settings(
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
) -> OpenRouterModelSettings:
    """创建OpenRouter模型设置"""
    settings = get_settings()
    return OpenRouterModelSettings(
        temperature=temperature or settings.temperature,
        max_tokens=max_tokens or settings.max_tokens,
        top_p=top_p or settings.top_p,
    )


DEFAULT_SETTINGS = create_model_settings()


class AgentContext(BaseModel):
    """Agent上下文，用于在Agent之间传递信息"""

    user_input: str = ""
    orders_info: str = ""
    machines_info: str = ""
    constraints_info: str = ""
    optimization_params: dict | None = None
    schedule_result: dict | None = None

    class Config:
        arbitrary_types_allowed = True


class BaseAPSAgent:
    """APS Agent基类"""

    def __init__(
        self,
        model: str | None = None,
        settings: OpenRouterModelSettings | None = None,
        instructions: str = "",
        output_type: type = str,
    ):
        config = get_settings()
        self.model_name = model or config.default_model
        self.settings = settings or DEFAULT_SETTINGS
        self.instructions = instructions
        self.output_type = output_type
        self._agent: Agent | None = None

    @property
    def agent(self) -> Agent:
        """获取或创建Agent实例"""
        if self._agent is None:
            self._agent = Agent(
                self.model_name,
                model_settings=self.settings,
                instructions=self.instructions,
                output_type=self.output_type,
            )
        return self._agent

    async def run(
        self, user_input: str, context: AgentContext | None = None
    ) -> Any:
        """运行Agent"""
        if context:
            prompt = self._build_prompt(user_input, context)
        else:
            prompt = user_input

        result = await self.agent.run(prompt)
        return result.output

    def _build_prompt(self, user_input: str, context: AgentContext) -> str:
        """构建包含上下文的提示"""
        parts = []

        if context.orders_info:
            parts.append(f"## 订单信息\n{context.orders_info}")

        if context.machines_info:
            parts.append(f"## 机器信息\n{context.machines_info}")

        if context.constraints_info:
            parts.append(f"## 约束信息\n{context.constraints_info}")

        if context.optimization_params:
            parts.append(f"## 优化参数\n{context.optimization_params}")

        if context.schedule_result:
            parts.append(f"## 排程结果\n{context.schedule_result}")

        parts.append(f"## 用户请求\n{user_input}")

        return "\n\n".join(parts)

    def run_sync(self, user_input: str, context: AgentContext | None = None) -> Any:
        """同步运行Agent"""
        if context:
            prompt = self._build_prompt(user_input, context)
        else:
            prompt = user_input

        result = self.agent.run_sync(prompt)
        return result.output
