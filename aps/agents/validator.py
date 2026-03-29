"""验证Agent - 综合验证排程结果"""

from typing import cast

from pydantic import BaseModel, Field

from aps.agents.base import BaseAPSAgent, create_model_settings
from aps.core.config import get_settings
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.order import Order
from aps.models.schedule import ScheduleResult


class ConstraintViolation(BaseModel):
    """约束违反详情"""
    type: str = Field(..., description="违反类型")
    order_id: str | None = Field(None, description="相关订单ID")
    machine_id: str | None = Field(None, description="相关机器ID")
    description: str = Field(..., description="违反描述")
    severity: str = Field("warning", description="严重程度: info/warning/error")
    impact: float = Field(0.0, ge=0.0, le=1.0, description="影响程度")


class ValidationResult(BaseModel):
    """验证结果"""
    is_valid: bool = Field(..., description="是否有效")
    constraint_violations: list[ConstraintViolation] = Field(
        default_factory=list,
        description="约束违反列表",
    )
    historical_deviation: float = Field(
        default=0.0, ge=0.0, le=1.0, description="与历史排程偏差（0-1）"
    )
    warnings: list[str] = Field(default_factory=list, description="警告列表")
    recommendations: list[str] = Field(default_factory=list, description="改进建议")
    confidence_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="置信度 (0-1)"
    )
    quality_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="质量评分 (0-1)"
    )
    overall_status: str = Field(
        "normal", description="整体状态: normal/warning/critical"
    )


class ValidatorAgent(BaseAPSAgent):
    """验证Agent — 默认使用确定性校验，LLM 作为可选第二意见"""

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

    # ------------------------------------------------------------------
    # 确定性校验（默认路径）
    # ------------------------------------------------------------------

    def validate_deterministic(
        self,
        result: ScheduleResult,
        orders: list[Order] | None = None,
        machines: list[ProductionLine] | None = None,
        constraints: ProductionConstraints | None = None,
    ) -> ValidationResult:
        """确定性校验（不调用 LLM），作为默认验证路径。"""
        violations: list[ConstraintViolation] = []

        violations.extend(self._check_constraint_violations(result))

        if machines:
            violations.extend(self._check_machine_compatibility(result, machines))
        if orders:
            violations.extend(self._check_time_feasibility(result, orders))
        if machines and constraints:
            violations.extend(
                self._check_changeover_feasibility(result, machines, constraints)
            )

        warnings = self._generate_warnings(result)
        quality_score = self._calculate_quality_score(result)
        recommendations = self._generate_recommendations(result, quality_score)

        is_valid = len([v for v in violations if v.severity == "error"]) == 0

        if quality_score >= 0.8:
            overall_status = "normal"
        elif quality_score >= 0.6:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return ValidationResult(
            is_valid=is_valid,
            constraint_violations=violations,
            warnings=warnings,
            recommendations=recommendations,
            confidence_score=0.95,
            quality_score=quality_score,
            overall_status=overall_status,
        )

    def _check_machine_compatibility(
        self, result: ScheduleResult, machines: list[ProductionLine]
    ) -> list[ConstraintViolation]:
        """检查每个分配的产品类型是否在机器的 supported_product_types 中"""
        violations = []
        machine_map = {m.id: m for m in machines}

        for a in result.assignments:
            machine = machine_map.get(a.machine_id)
            if machine is None:
                violations.append(
                    ConstraintViolation(
                        type="machine_not_found",
                        order_id=a.order_id,
                        machine_id=a.machine_id,
                        description=f"机器 {a.machine_id} 不存在",
                        severity="error",
                        impact=1.0,
                    )
                )
                continue
            if not machine.can_produce(a.product_type):
                violations.append(
                    ConstraintViolation(
                        type="machine_compatibility",
                        order_id=a.order_id,
                        machine_id=a.machine_id,
                        description=(
                            f"机器 {a.machine_id} 不支持产品类型 {a.product_type}"
                        ),
                        severity="error",
                        impact=0.9,
                    )
                )
        return violations

    def _check_time_feasibility(
        self, result: ScheduleResult, orders: list[Order]
    ) -> list[ConstraintViolation]:
        """检查时间可行性：min_start_time、负时间、end < start 等"""
        violations = []
        order_map = {o.id: o for o in orders}

        for a in result.assignments:
            if a.end_time < a.start_time:
                violations.append(
                    ConstraintViolation(
                        type="time_consistency",
                        order_id=a.order_id,
                        machine_id=a.machine_id,
                        description=(
                            f"订单 {a.order_id} "
                            f"结束时间({a.end_time})早于开始时间({a.start_time})"
                        ),
                        severity="error",
                        impact=1.0,
                    )
                )

            if a.start_time < 0:
                violations.append(
                    ConstraintViolation(
                        type="negative_time",
                        order_id=a.order_id,
                        machine_id=a.machine_id,
                        description=(
                            f"订单 {a.order_id} 开始时间为负({a.start_time})"
                        ),
                        severity="error",
                        impact=1.0,
                    )
                )

            order = order_map.get(a.order_id)
            if order and a.start_time < order.min_start_time:
                violations.append(
                    ConstraintViolation(
                        type="min_start_time",
                        order_id=a.order_id,
                        machine_id=a.machine_id,
                        description=(
                            f"订单 {a.order_id} "
                            f"开始时间({a.start_time})早于"
                            f"最早开始时间({order.min_start_time})"
                        ),
                        severity="error",
                        impact=0.8,
                    )
                )

        return violations

    def _check_changeover_feasibility(
        self,
        result: ScheduleResult,
        machines: list[ProductionLine],
        constraints: ProductionConstraints,
    ) -> list[ConstraintViolation]:
        """检查同一机器上相邻任务的换产时间是否充足"""
        violations = []
        for machine in machines:
            machine_assignments = sorted(
                [a for a in result.assignments if a.machine_id == machine.id],
                key=lambda a: a.start_time,
            )
            for k in range(1, len(machine_assignments)):
                prev = machine_assignments[k - 1]
                curr = machine_assignments[k]
                required_changeover = constraints.get_changeover_time(
                    prev.product_type, curr.product_type
                )
                actual_gap = curr.start_time - prev.end_time
                if actual_gap < required_changeover - 0.01:
                    violations.append(
                        ConstraintViolation(
                            type="changeover_feasibility",
                            order_id=curr.order_id,
                            machine_id=machine.id,
                            description=(
                                f"机器 {machine.id}: "
                                f"{prev.order_id}→{curr.order_id} "
                                f"间隙({actual_gap:.1f}h) < "
                                f"所需换产时间({required_changeover:.1f}h)"
                            ),
                            severity="error",
                            impact=0.7,
                        )
                    )
        return violations

    def quick_validate(self, result: ScheduleResult) -> ValidationResult:
        """快速验证（无LLM的后备方法）— 保持向后兼容"""
        violations = self._check_constraint_violations(result)
        warnings = self._generate_warnings(result)
        quality_score = self._calculate_quality_score(result)
        recommendations = self._generate_recommendations(result, quality_score)

        is_valid = len([v for v in violations if v.severity == "error"]) == 0

        if quality_score >= 0.8:
            overall_status = "normal"
        elif quality_score >= 0.6:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return ValidationResult(
            is_valid=is_valid,
            constraint_violations=violations,
            warnings=warnings,
            recommendations=recommendations,
            confidence_score=0.9,
            quality_score=quality_score,
            overall_status=overall_status,
        )

    def _check_constraint_violations(
        self, result: ScheduleResult
    ) -> list[ConstraintViolation]:
        """检查约束违反"""
        violations = []

        for assignment in result.assignments:
            if not assignment.is_on_time:
                violations.append(
                    ConstraintViolation(
                        type="due_date",
                        order_id=assignment.order_id,
                        machine_id=assignment.machine_id,
                        description=f"订单延期 {assignment.delay_hours:.1f}小时",
                        severity="warning" if assignment.delay_hours < 2 else "error",
                        impact=min(1.0, assignment.delay_hours / 10),
                    )
                )

        for machine_id, util in result.machine_utilization.items():
            if util > 0.95:
                violations.append(
                    ConstraintViolation(
                        type="capacity",
                        order_id=None,
                        machine_id=machine_id,
                        description=f"机器利用率过高 {util * 100:.1f}%",
                        severity="warning" if util < 0.98 else "error",
                        impact=util - 0.9,
                    )
                )

        return violations

    def _generate_warnings(self, result: ScheduleResult) -> list[str]:
        """生成警告"""
        warnings = []

        if result.on_time_delivery_rate < 1.0:
            delayed = result.delayed_count
            warnings.append(f"有 {delayed} 个订单延期")

        if result.total_changeover_time > result.total_makespan * 0.15:
            warnings.append("换产时间占比较高，建议优化生产序列")

        for machine_id, util in result.machine_utilization.items():
            if util > 0.9:
                warnings.append(f"机器 {machine_id} 负载过高 ({util * 100:.1f}%)")

        return warnings

    def _calculate_quality_score(self, result: ScheduleResult) -> float:
        """计算质量评分"""
        if result.task_count == 0:
            return 0.0

        score = 0.0

        on_time_weight = 0.4
        score += result.on_time_delivery_rate * on_time_weight

        utilization_weight = 0.3
        if result.machine_utilization:
            avg_util = sum(result.machine_utilization.values()) / len(
                result.machine_utilization
            )
            if avg_util > 0.85:
                util_score = min(1.0, avg_util)
            else:
                util_score = avg_util
            score += util_score * utilization_weight

        changeover_weight = 0.3
        if result.total_makespan > 0:
            changeover_ratio = result.total_changeover_time / result.total_makespan
            if changeover_ratio < 0.1:
                score += changeover_weight
            elif changeover_ratio < 0.2:
                score += changeover_weight * 0.7
            else:
                score += changeover_weight * 0.3

        return min(1.0, max(0.0, score))

    def _generate_recommendations(
        self, result: ScheduleResult, quality_score: float
    ) -> list[str]:
        """生成改进建议"""
        recommendations = []

        if quality_score >= 0.8:
            recommendations.append("当前排程方案质量良好")
        else:
            if result.on_time_delivery_rate < 0.9:
                recommendations.append("建议增加产能或调整交期")

            if result.total_changeover_time > result.total_makespan * 0.15:
                recommendations.append("优化生产序列可减少换产时间")

            high_load_machines = [
                m for m, u in result.machine_utilization.items() if u > 0.9
            ]
            if high_load_machines:
                recommendations.append(
                    f"考虑平衡 {', '.join(high_load_machines)} 的负载"
                )

        return recommendations if recommendations else ["当前排程方案可行"]

    # ------------------------------------------------------------------
    # LLM 验证（可选的第二意见）
    # ------------------------------------------------------------------

    async def validate_with_llm(
        self, result: ScheduleResult
    ) -> ValidationResult:
        """使用 LLM 验证（可选的第二意见）"""
        prompt = self._build_validation_prompt(result)
        agent_result = await self.agent.run(prompt)
        return cast(ValidationResult, agent_result.output)

    def validate_with_llm_sync(
        self, result: ScheduleResult
    ) -> ValidationResult:
        """使用 LLM 同步验证（可选的第二意见）"""
        prompt = self._build_validation_prompt(result)
        agent_result = self.agent.run_sync(prompt)
        return cast(ValidationResult, agent_result.output)

    async def validate(self, result: ScheduleResult) -> ValidationResult:
        """验证排程结果 — 默认使用确定性校验"""
        return self.validate_deterministic(result)

    def validate_sync(self, result: ScheduleResult) -> ValidationResult:
        """同步验证排程结果 — 默认使用确定性校验"""
        return self.validate_deterministic(result)

    def _build_validation_prompt(self, result: ScheduleResult) -> str:
        """构建验证提示（供 LLM 方法使用）"""
        parts = ["## 排程结果"]

        parts.append(f"- 任务数: {result.task_count}")
        parts.append(f"- 总完工时间: {result.total_makespan:.1f}小时")
        parts.append(f"- 准时率: {result.on_time_delivery_rate * 100:.1f}%")
        parts.append(f"- 换产时间: {result.total_changeover_time:.1f}小时")

        parts.append("\n## 机器利用率")
        for machine_id, util in result.machine_utilization.items():
            status = "正常" if util < 0.85 else ("警告" if util < 0.9 else "危险")
            parts.append(f"- {machine_id}: {util * 100:.1f}% [{status}]")

        parts.append(
            "\n请验证此排程结果的质量和可行性。请检查:\n"
            "1. 所有约束是否满足\n"
            "2. 准时交付风险\n"
            "3. 机器负载均衡\n"
            "4. 换产时间合理性"
        )

        return "\n".join(parts)
