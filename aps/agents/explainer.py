"""解释Agent - 生成排程解释报告"""

from typing import cast

from aps.agents.base import AgentContext, BaseAPSAgent, create_model_settings
from aps.core.config import get_settings
from aps.models.schedule import ScheduleExplanation


class ExplainAgent(BaseAPSAgent):
    """解释Agent"""

    def __init__(self):
        config = get_settings()
        settings = create_model_settings(temperature=0.3)

        super().__init__(
            model=config.default_model,
            settings=settings,
            instructions=self._get_instructions(),
            output_type=ScheduleExplanation,
        )

    def _get_instructions(self) -> str:
        return """你是APS生产排程系统的解释Agent。

你的职责是生成排程结果的可读解释报告。

**报告内容**：
1. summary: 排程摘要（任务数、总完工时间等）
2. sequence_description: 每台机器的生产序列
3. key_decisions: 关键决策说明（为什么这样安排）
4. risk_alerts: 风险提示（延期订单、紧张时段等）
5. recommendations: 优化建议

**格式要求**：
- 使用清晰简洁的语言
- 突出关键信息
- 提供可操作的建议
"""

    async def run(
        self, user_input: str, context: AgentContext | None = None
    ) -> ScheduleExplanation:
        """运行解释Agent"""
        prompt = self._build_prompt(user_input, context)
        result = await self.agent.run(prompt)
        return cast(ScheduleExplanation, result.output)

    def _build_prompt(self, user_input: str, context: AgentContext | None) -> str:
        """构建提示"""
        parts = [f"## 用户请求\n{user_input}"]

        if context:
            if context.orders_info:
                parts.append(f"## 订单信息\n{context.orders_info}")
            if context.machines_info:
                parts.append(f"## 机器信息\n{context.machines_info}")
            if context.optimization_params:
                parts.append(f"## 优化参数\n{context.optimization_params}")
            if context.schedule_result:
                parts.append(
                    f"## 排程结果\n{self._format_result(context.schedule_result)}"
                )

        parts.append("\n请生成排程解释报告。")

        return "\n\n".join(parts)

    def _format_result(self, result: dict) -> str:
        """格式化排程结果"""
        lines = []
        lines.append(f"- 任务数: {result.get('task_count', 0)}")
        lines.append(f"- 总完工时间: {result.get('total_makespan', 0):.1f}小时")
        lines.append(f"- 准时率: {result.get('on_time_delivery_rate', 1.0) * 100:.1f}%")

        if result.get("assignments"):
            lines.append("\n生产序列:")
            for a in sorted(
                result["assignments"], key=lambda x: x.get("start_time", 0)
            ):
                mark = "✓" if a.get("is_on_time", True) else "✗"
                lines.append(
                    f"  [{mark}] {a.get('machine_id')}: {a.get('product_name')} "
                    f"({a.get('start_time', 0):.1f}-{a.get('end_time', 0):.1f}h)"
                )

        return "\n".join(lines)
