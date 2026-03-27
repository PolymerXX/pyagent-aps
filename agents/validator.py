"""验证Agent - 综合验证排程结果"""

from typing import Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.core.config import get_settings
from aps.models.schedule import ScheduleResult
from aps.agents.base import create_model_settings, BaseAPSAgent


class ValidationResult(BaseModel):
    """验证结果"""

    is_valid: bool = Field(..., description="是否有效")
    constraint_violations: List[dict] = Field(
        default_factory=list, description="约束违反列表"
    )
    historical_deviation: float = Field(
        default=0.0, ge=0.0, le=1.0, description="与历史排程偏差（0-1）"
    )
    warnings: List[str] = Field(default_factory=list, description="警告列表")
    recommendations: List[str] = Field(default_factory=list, description="改进建议")
    confidence_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="置信度 (0-1)"
    )
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="质量评分 (0-1)"
    )


class ValidatorAgent(BaseAPSAgent):
    """验证Agent"""

    def __init__(self):
        config = get_settings()
        settings = create_model_settings(temperature=0.0)

        super().__init__(
            model=config.default_model,
            settings=settings,
            instructions=self._get_instructions(),
            output_type=ValidationResult,
        )

    def _get_instructions(self) -> str:
        return """你是APS排程系统的验证Agent。

你的职责是综合验证排程结果的可行性和质量。

**验证维度**：
1. 约束满足检查（机器兼容性、时间约束、产能限制）
2. 质量指标评估（准时率、利用率、换产效率）
3. 风险识别（延期风险、瓶颈、时间紧凑）

**输出要求**：
- is_valid: 总体是否有效
- constraint_violations: 违反的约束列表
- warnings: 风险警告
- recommendations: 改进建议
- quality_score: 质量评分
"""

    async def run(
        self, result: ScheduleResult, context: Optional[dict] = None
    ) -> ValidationResult:
        """验证排程结果"""
        prompt = self._build_validation_prompt(result, context)
        agent_result = await self.agent.run(prompt)
        return agent_result.data

    def _build_validation_prompt(
        self, result: ScheduleResult, context: Optional[dict]
    ) -> str:
        """构建验证提示"""
        parts = ["## 排程结果"]

        parts.append(f"- 任务数: {result.task_count}")
        parts.append(f"- 总完工时间: {result.total_makespan:.1f}小时")
        parts.append(f"- 准时率: {result.on_time_delivery_rate * 100:.1f}%")
        parts.append(f"- 换产时间: {result.total_changeover_time:.1f}小时")

        parts.append("\n## 机器利用率")
        for machine_id, util in result.machine_utilization.items():
            status = "正常" if util < 0.85 else ("警告" if util < 0.9 else "危险")
            parts.append(f"- {machine_id}: {util * 100:.1f}% [{status}]")

        parts.append("\n请验证此排程结果的质量和可行性。")

        return "\n".join(parts)

    def validate_constraints(
        self, result: ScheduleResult, constraints: dict
    ) -> List[dict]:
        """验证约束（无LLM的后备方法）"""
        violations = []

        for assignment in result.assignments:
            if not assignment.is_on_time:
                violations.append(
                    {
                        "type": "due_date",
                        "order_id": assignment.order_id,
                        "description": f"订单延期 {assignment.delay_hours:.1f}小时",
                        "severity": "warning"
                        if assignment.delay_hours < 2
                        else "error",
                    }
                )

        return violations

    def calculate_quality_score(self, result: ScheduleResult) -> float:
        """计算质量评分"""
        score = 0.0

        score += result.on_time_delivery_rate * 0.4

        avg_util = (
            sum(result.machine_utilization.values()) / len(result.machine_utilization)
            if result.machine_utilization
            else 0
        )
        util_score = 1.0 - abs(avg_util - 0.8)
        score += max(0, util_score) * 0.3

        if result.total_makespan > 0:
            changeover_ratio = result.total_changeover_time / result.total_makespan
            changeover_score = 1.0 - min(1.0, changeover_ratio * 2)
            score += changeover_score * 0.3

        return min(1.0, max(0.0, score))
