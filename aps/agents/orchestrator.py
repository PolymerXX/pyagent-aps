"""主控Agent和APS系统协调器

集成多Agent协作流程：
1. Orchestrator - 意图分析和任务协调
2. Planner - 需求理解和参数设置
3. Scheduler - 排程执行
4. Validator - 结果验证
5. Adjuster - 动态调整（如果验证失败）
6. Explainer - 结果解释
7. Monitor - 实时监控
"""

from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.agents.adjuster import AdjusterAgent
from aps.agents.base import AgentContext, create_model_settings
from aps.agents.explainer import ExplainAgent
from aps.agents.monitor import MonitorAgent, MonitorReport
from aps.agents.planner import PlannerAgent, PlannerOutput
from aps.agents.scheduler import SchedulerAgent
from aps.agents.validator import ValidationResult, ValidatorAgent
from aps.core.config import Settings, get_settings
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order
from aps.models.schedule import ScheduleExplanation, ScheduleResult


class TaskType(str, Enum):
    PLAN = "plan"
    SCHEDULE = "schedule"
    VALIDATE = "validate"
    ADJUST = "adjust"
    EXPLAIN = "explain"
    MONITOR = "monitor"


class OrchestratorResponse(BaseModel):
    """主控Agent响应"""

    user_intent: str = Field(..., description="用户意图分析")
    required_tasks: list[TaskType] = Field(
        default_factory=lambda: [TaskType.PLAN, TaskType.SCHEDULE, TaskType.EXPLAIN],
        description="需要执行的任务序列",
    )
    strategy_hint: str | None = Field(
        default=None, description="策略提示（如'优先交期'、'最小换产'）"
    )


class APSSystem:
    """APS系统主入口 - 多Agent协作"""

    def __init__(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints | None = None,
        settings: Settings | None = None,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.settings = settings or get_settings()

        # 初始化各Agent
        self.orchestrator_agent = OrchestratorAgent()
        self.planner = PlannerAgent()
        self.scheduler = SchedulerAgent(
            orders=orders, machines=machines, constraints=constraints
        )
        self.explainer = ExplainAgent()
        self.validator = ValidatorAgent()
        self.adjuster = AdjusterAgent()
        self.monitor = MonitorAgent()

        # 结果缓存
        self._last_params: OptimizationParams | None = None
        self._last_result: ScheduleResult | None = None
        self._last_validation: ValidationResult | None = None
        self._adjustment_count: int = 0
        self._max_adjustments: int = 3

    async def process_request(
        self, user_input: str, params: OptimizationParams | None = None
    ) -> dict:
        """处理用户请求 - 完整的多Agent协作流程"""

        # 1. 分析用户意图
        intent = await self._analyze_intent(user_input)

        # 2. 规划优化参数
        if params is None:
            params = await self._plan_optimization(user_input, intent)
        self._last_params = params

        # 3. 执行排产
        result = await self._execute_schedule(params)
        self._last_result = result

        # 4. 验证结果
        validation = await self._validate_result(result)
        self._last_validation = validation

        # 5. 如果验证失败，触发调整
        if not validation.is_valid:
            result = await self._adjust_if_needed(result, validation)

        # 6. 生成解释
        explanation = await self._explain_result(user_input, result, params)

        # 7. 生成监控报告
        monitor_report = await self._monitor_result(result)

        return {
            "intent": intent,
            "optimization_params": params.model_dump(),
            "schedule": result.model_dump(),
            "validation": validation.model_dump(),
            "explanation": explanation.model_dump(),
            "monitor_report": monitor_report.model_dump(),
        }

    async def _analyze_intent(self, user_input: str) -> str:
        """分析用户意图"""
        try:
            response = await self.orchestrator_agent.run(user_input)
            return response.user_intent
        except Exception:
            return "生产排程请求"

    async def _plan_optimization(
        self, user_input: str, intent: str
    ) -> OptimizationParams:
        """规划优化参数"""
        context = AgentContext(
            user_input=user_input,
            orders_info=self._format_orders(),
            machines_info=self._format_machines(),
        )

        try:
            planner_output = await self.planner.run(user_input, context)
            if isinstance(planner_output, PlannerOutput):
                return planner_output.to_optimization_params()
            return OptimizationParams()
        except Exception:
            return self._infer_params_from_input(user_input)

    def _infer_params_from_input(self, user_input: str) -> OptimizationParams:
        """从输入推断优化参数"""
        user_input_lower = user_input.lower()

        if any(kw in user_input_lower for kw in ["交期", "准时", "不延误", "截止"]):
            return OptimizationParams(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        elif any(kw in user_input_lower for kw in ["换产", "清洗", "切换"]):
            return OptimizationParams(strategy=OptimizationStrategy.MINIMIZE_CHANGEOVER)
        elif any(kw in user_input_lower for kw in ["利润", "收益"]):
            return OptimizationParams(strategy=OptimizationStrategy.MAXIMIZE_PROFIT)
        else:
            return OptimizationParams(strategy=OptimizationStrategy.BALANCED)

    async def _execute_schedule(self, params: OptimizationParams) -> ScheduleResult:
        """执行排产"""
        return self.scheduler.run_optimization(params)

    async def _explain_result(
        self, user_input: str, result: ScheduleResult, params: OptimizationParams
    ) -> ScheduleExplanation:
        """解释排程结果"""
        context = AgentContext(
            user_input=user_input,
            orders_info=self._format_orders(),
            machines_info=self._format_machines(),
            optimization_params=params.model_dump(),
            schedule_result=result.model_dump(),
        )

        try:
            explanation = await self.explainer.run(user_input, context)
            if isinstance(explanation, ScheduleExplanation):
                return explanation
        except Exception:
            pass

        return self._generate_simple_explanation(result)

    def _generate_simple_explanation(
        self, result: ScheduleResult
    ) -> ScheduleExplanation:
        """生成简单解释（后备方案）"""
        sequence = []
        for i, a in enumerate(result.get_sorted_assignments(), 1):
            seq = f"{i}. {a.machine_id}: {a.product_name} ({a.start_time:.1f}-{a.end_time:.1f}小时)"
            if not a.is_on_time:
                seq += f" [延期{a.delay_hours:.1f}小时]"
            sequence.append(seq)

        risks = []
        if result.on_time_delivery_rate < 1.0:
            risks.append(f"有{result.delayed_count}个订单延期")
        if result.total_changeover_time > 5:
            risks.append(f"换产时间较长({result.total_changeover_time:.1f}小时)")

        return ScheduleExplanation(
            summary=f"排产完成，共{result.task_count}个任务，总完工时间{result.total_makespan:.1f}小时",
            key_decisions=sequence,
            risks=risks if risks else ["无明显风险"],
            alternatives=self._generate_recommendations(result),
        )

    def _generate_recommendations(self, result: ScheduleResult) -> list[str]:
        """生成优化建议"""
        recs = []

        if result.delayed_count > 0:
            recs.append("建议增加产能或调整交期预期")

        avg_util = (
            sum(result.machine_utilization.values()) / len(self.machines)
            if self.machines
            else 0
        )
        if avg_util > 0.9:
            recs.append("设备利用率很高，建议考虑增加产能")
        elif avg_util < 0.5:
            recs.append("设备利用率较低，可考虑承接更多订单")

        if result.total_changeover_time > result.total_makespan * 0.2:
            recs.append("换产时间占比较高，建议优化生产序列")

        if not recs:
            recs.append("当前排程方案合理")

        return recs

    async def _validate_result(self, result: ScheduleResult) -> ValidationResult:
        """验证排程结果"""
        return await self.validator.validate(result)

    async def _adjust_if_needed(
        self, result: ScheduleResult, validation: ValidationResult
    ) -> ScheduleResult:
        """如果验证失败，尝试调整"""
        if self._adjustment_count >= self._max_adjustments:
            return result

        self._adjustment_count += 1

        try:
            adjustment = await self.adjuster.analyze_and_adjust(
                result=result,
                validation=validation,
                orders=self.orders,
                machines=self.machines,
            )
            if adjustment and adjustment.new_schedule is not None:
                return adjustment.new_schedule
        except Exception:
            pass

        return result

    async def _monitor_result(self, result: ScheduleResult) -> MonitorReport:
        """生成监控报告"""
        return await self.monitor.run(result)

    def _format_orders(self) -> str:
        """格式化订单信息"""
        lines = []
        for order in self.orders:
            lines.append(
                f"- {order.id}: {order.product.name} "
                f"{order.quantity}瓶, 截止{order.due_date}小时"
            )
        return "\n".join(lines)

    def _format_machines(self) -> str:
        """格式化机器信息"""
        lines = []
        for m in self.machines:
            types = ", ".join(t.value for t in m.supported_product_types)
            lines.append(f"- {m.id}({m.name}): 支持类型[{types}]")
        return "\n".join(lines)

    def process_request_sync(
        self, user_input: str, params: OptimizationParams | None = None
    ) -> dict:
        """处理用户请求（同步版本）"""
        import asyncio

        return asyncio.run(self.process_request(user_input, params))

    def quick_schedule(
        self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> ScheduleResult:
        """快速排产（不使用LLM）"""
        params = OptimizationParams(strategy=strategy)
        return self.scheduler.run_optimization(params)


class OrchestratorAgent:
    """主控Agent - 分析用户意图并协调任务"""

    def __init__(self):
        settings = get_settings()
        self.settings = create_model_settings(temperature=0.0)

        self.agent = Agent(
            settings.default_model,
            model_settings=self.settings,
            instructions=self._get_instructions(),
            output_type=OrchestratorResponse,
        )

    def _get_instructions(self) -> str:
        return """你是APS生产排程系统的主控Agent。

你的职责是：
1. 理解用户的生产排程请求
2. 分析用户的意图和优先级偏好
3. 确定需要执行的子任务序列

分析用户输入时，请注意：
- "交期"、"准时"、"不延误" → 优先准时交付策略
- "换产"、"清洗"、"切换" → 最小化换产策略
- "利润"、"收益" → 最大化利润策略
- 如果没有明确偏好 → 使用均衡策略

返回结构化的响应，包含：
- user_intent: 用户意图的简明描述
- required_tasks: 需要执行的任务（通常为[plan, schedule, explain]）
- strategy_hint: 策略提示
"""

    async def run(self, user_input: str) -> OrchestratorResponse:
        """运行Agent"""
        result = await self.agent.run(user_input)
        return result.output
