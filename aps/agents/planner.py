"""规划Agent - 将用户请求转换为优化参数"""

import json
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from aps.agents.base import AgentContext, BaseAPSAgent, create_model_settings
from aps.core.config import get_settings
from aps.models.optimization import (
    ObjectiveWeights,
    OptimizationParams,
    OptimizationStrategy,
)


class PlannerOutput(BaseModel):
    """规划Agent输出。

    权重仅通过四个顶层标量字段表示。禁止输出名为 weights 的字段，禁止嵌套对象或 JSON 字符串；
    否则工具参数校验会把错误的 weights 当作 ObjectiveWeights 而失败。

    部分模型仍会把 weights 整段打成 JSON 字符串；在校验前展平到顶层字段并丢弃 weights，避免
    UnexpectedModelBehavior / ValidationError（见 Logfire issue 等）。
    """

    model_config = ConfigDict(extra="ignore")

    strategy: OptimizationStrategy = Field(
        default=OptimizationStrategy.BALANCED, description="优化策略"
    )
    on_time: float = Field(default=0.4, ge=0.0, le=1.0, description="准时交付权重 on_time")
    changeover: float = Field(default=0.2, ge=0.0, le=1.0, description="最小换产权重 changeover")
    utilization: float = Field(
        default=0.2, ge=0.0, le=1.0, description="设备利用率权重 utilization"
    )
    profit: float = Field(default=0.2, ge=0.0, le=1.0, description="利润权重 profit")
    time_limit_seconds: int = Field(default=60, description="求解时间限制")
    allow_delays: bool = Field(default=True, description="是否允许延期")
    max_delay_hours: float = Field(default=24.0, description="最大延期小时数")
    priority_orders: list[str] = Field(default_factory=list, description="优先处理的订单ID")
    frozen_assignments: list[str] = Field(default_factory=list, description="冻结的分配（不调整）")
    explanation: str = Field(default="", description="规划决策说明")

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_weights_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        raw = out.pop("weights", None)
        if raw is None:
            return out
        parsed: dict[str, Any] | None = None
        if isinstance(raw, str):
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                return out
            parsed = loaded if isinstance(loaded, dict) else None
        elif isinstance(raw, dict):
            parsed = raw
        if not parsed:
            return out
        for key in ("on_time", "changeover", "utilization", "profit"):
            if key in parsed and key not in out:
                out[key] = parsed[key]
        return out

    @property
    def weights(self) -> ObjectiveWeights:
        return ObjectiveWeights(
            on_time=self.on_time,
            changeover=self.changeover,
            utilization=self.utilization,
            profit=self.profit,
        )

    def to_optimization_params(self) -> OptimizationParams:
        """转换为优化参数"""
        return OptimizationParams(
            strategy=self.strategy,
            weights=self.weights,
            time_limit_seconds=self.time_limit_seconds,
            allow_late_delivery=self.allow_delays,
            max_late_hours=max(0, int(round(self.max_delay_hours))),
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
- "产能"、"利用率" → MAX_UTILIZATION策略
- 没有明确偏好 → BALANCED策略

**设置权重**：
在输出里只填四个顶层数字字段 on_time、changeover、utilization、profit（范围 0–1），总和应为 1.0。
不要输出 weights 字段，不要用嵌套对象或 JSON 字符串代替这四个数。

**输出要求**：
- strategy: 优化策略枚举
- on_time / changeover / utilization / profit: 四个权重数字
- time_limit_seconds: 求解时间限制（通常60秒足够）
- explanation: 简要说明决策理由
"""

    _STRATEGY_KEYWORDS: dict[OptimizationStrategy, list[str]] = {
        OptimizationStrategy.ON_TIME_DELIVERY: [
            "交期",
            "准时",
            "不延误",
            "截止",
            "按时",
        ],
        OptimizationStrategy.MINIMIZE_CHANGEOVER: [
            "换产",
            "清洗",
            "切换",
            "最少换产",
            "减少切换",
        ],
        OptimizationStrategy.MAXIMIZE_PROFIT: [
            "利润",
            "收益",
            "赚钱",
            "最大利润",
        ],
        OptimizationStrategy.MAX_UTILIZATION: [
            "产能",
            "利用率",
            "满载",
            "最大化产能",
        ],
    }

    async def run(self, user_input: str, context: AgentContext | None = None) -> PlannerOutput:
        """运行规划Agent — 关键词匹配优先，LLM 后备"""
        keyword_result = self._match_keywords(user_input)
        if keyword_result is not None:
            return keyword_result

        try:
            prompt = self._build_prompt(user_input, context)
            result = await self.agent.run(prompt)
            return cast(PlannerOutput, result.output)
        except Exception:
            return PlannerOutput()

    def _match_keywords(self, user_input: str) -> PlannerOutput | None:
        """关键词匹配策略（确定性，不调用 LLM）"""
        text = user_input.lower()
        for strategy, keywords in self._STRATEGY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                weights = self._default_weights_for(strategy)
                return PlannerOutput(
                    strategy=strategy,
                    on_time=weights.on_time,
                    changeover=weights.changeover,
                    utilization=weights.utilization,
                    profit=weights.profit,
                    explanation=f"关键词匹配策略: {strategy.value}",
                )
        return None

    @staticmethod
    def _default_weights_for(
        strategy: OptimizationStrategy,
    ) -> ObjectiveWeights:
        """根据策略返回默认权重"""
        presets: dict[OptimizationStrategy, dict] = {
            OptimizationStrategy.ON_TIME_DELIVERY: dict(
                on_time=0.6,
                changeover=0.1,
                utilization=0.2,
                profit=0.1,
            ),
            OptimizationStrategy.MINIMIZE_CHANGEOVER: dict(
                on_time=0.2,
                changeover=0.6,
                utilization=0.1,
                profit=0.1,
            ),
            OptimizationStrategy.MAXIMIZE_PROFIT: dict(
                on_time=0.2,
                changeover=0.1,
                utilization=0.1,
                profit=0.6,
            ),
            OptimizationStrategy.MAX_UTILIZATION: dict(
                on_time=0.1,
                changeover=0.1,
                utilization=0.6,
                profit=0.2,
            ),
        }
        return ObjectiveWeights(
            **presets.get(
                strategy,
                dict(
                    on_time=0.4,
                    changeover=0.2,
                    utilization=0.2,
                    profit=0.2,
                ),
            )
        )

    def _build_prompt(self, user_input: str, context: AgentContext | None) -> str:
        """构建提示"""
        parts = []

        if context:
            if context.orders_info:
                parts.append(f"## 订单信息\n{context.orders_info}")
            if context.machines_info:
                parts.append(f"## 机器信息\n{context.machines_info}")

        parts.append(f"## 用户请求\n{user_input}")

        return "\n\n".join(parts)
