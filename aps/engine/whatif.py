"""What-If 场景模拟引擎

对比基准排程方案与假设变更后的排程方案，生成差异报告。
"""

from __future__ import annotations

import copy
import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from aps.engine.solver import APSSolver
from aps.models.constraint import ChangeoverRule, ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult


class ScenarioChangeType(str, Enum):
    ADD_MACHINE = "add_machine"
    REMOVE_MACHINE = "remove_machine"
    ADD_ORDER = "add_order"
    REMOVE_ORDER = "remove_order"
    MODIFY_ORDER = "modify_order"
    CHANGE_CONSTRAINT = "change_constraint"
    MACHINE_DOWN = "machine_down"


class ScenarioChange(BaseModel):
    """单个场景变更"""
    change_type: ScenarioChangeType = Field(..., description="变更类型")
    params: dict[str, Any] = Field(default_factory=dict, description="变更参数")


class WhatIfScenario(BaseModel):
    """What-If 场景定义"""
    name: str = Field(..., description="场景名称")
    changes: list[ScenarioChange] = Field(default_factory=list, description="变更列表")
    description: str = Field(default="", description="场景描述")


class MetricComparison(BaseModel):
    """指标对比"""
    baseline_value: float = Field(..., description="基准值")
    scenario_value: float = Field(..., description="场景值")
    delta: float = Field(..., description="差值（场景 - 基准）")
    delta_percent: float = Field(..., description="变化百分比")
    improved: bool = Field(..., description="是否改善")


class WhatIfReport(BaseModel):
    """What-If 对比报告"""
    scenario_name: str = Field(..., description="场景名称")
    scenario_description: str = Field(default="", description="场景描述")

    makespan_comparison: MetricComparison | None = Field(None, description="完工时间对比")
    on_time_rate_comparison: MetricComparison | None = Field(None, description="准时率对比")
    changeover_comparison: MetricComparison | None = Field(None, description="换产时间对比")
    utilization_comparison: MetricComparison | None = Field(None, description="平均利用率对比")
    task_count_comparison: MetricComparison | None = Field(None, description="任务数对比")

    baseline_summary: dict[str, Any] = Field(default_factory=dict, description="基准方案摘要")
    scenario_summary: dict[str, Any] = Field(default_factory=dict, description="场景方案摘要")

    simulation_time_seconds: float = Field(default=0.0, description="模拟耗时")

    overall_improvement: bool = Field(default=False, description="总体是否改善")
    score_delta: float = Field(default=0.0, description="综合评分变化")


class WhatIfEngine:
    """What-If 模拟引擎"""

    def __init__(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints | None = None,
        params: OptimizationParams | None = None,
    ):
        self.orders = list(orders)
        self.machines = list(machines)
        self.constraints = constraints or ProductionConstraints()
        self.params = params or OptimizationParams()

    def compare(
        self,
        baseline: ScheduleResult | None = None,
        scenario: WhatIfScenario | None = None,
    ) -> WhatIfReport:
        """执行 What-If 模拟，返回对比报告"""
        start_time = time.time()

        if baseline is None:
            baseline = self._solve_baseline()

        if scenario is None:
            return WhatIfReport(
                scenario_name="empty",
                simulation_time_seconds=time.time() - start_time,
            )

        modified_orders, modified_machines, modified_constraints = self._apply_changes(
            scenario.changes
        )

        scenario_result = self._solve_scenario(modified_orders, modified_machines, modified_constraints)

        report = self._build_report(baseline, scenario_result, scenario, time.time() - start_time)

        return report

    def _solve_baseline(self) -> ScheduleResult:
        """求解基准方案"""
        solver = APSSolver(
            orders=self.orders,
            machines=self.machines,
            constraints=self.constraints,
            params=self.params,
        )
        solver.enable_cache(False)
        return solver.solve()

    def _solve_scenario(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints,
    ) -> ScheduleResult:
        """求解场景方案"""
        if not orders or not machines:
            return ScheduleResult()

        solver = APSSolver(
            orders=orders,
            machines=machines,
            constraints=constraints,
            params=self.params,
        )
        solver.enable_cache(False)
        return solver.solve()

    def _apply_changes(
        self,
        changes: list[ScenarioChange],
    ) -> tuple[list[Order], list[ProductionLine], ProductionConstraints]:
        """应用场景变更，返回修改后的数据（克隆）"""
        orders = list(self.orders)
        machines = list(self.machines)
        constraints = self.constraints.model_copy(deep=True)

        for change in changes:
            if change.change_type == ScenarioChangeType.ADD_MACHINE:
                machine_data = change.params
                new_machine = ProductionLine(
                    id=machine_data.get("id", "new_machine"),
                    name=machine_data.get("name", "新机器"),
                    capacity_per_hour=machine_data.get("capacity_per_hour", 1000),
                    supported_product_types=machine_data.get("supported_product_types", []),
                    setup_time_hours=machine_data.get("setup_time_hours", 0.0),
                )
                machines.append(new_machine)

            elif change.change_type == ScenarioChangeType.REMOVE_MACHINE:
                machine_id = change.params.get("machine_id", "")
                machines = [m for m in machines if m.id != machine_id]

            elif change.change_type == ScenarioChangeType.ADD_ORDER:
                order_data = change.params
                product_type = ProductType.BEVERAGE
                pt_raw = order_data.get("product_type")
                if pt_raw:
                    try:
                        from aps.adapters.parsers import parse_product_type
                        product_type = parse_product_type(pt_raw)
                    except ValueError:
                        pass
                new_order = Order(
                    id=order_data.get("id", "new_order"),
                    product=Product(
                        id=f"prod_{order_data.get('id', 'new_order')}",
                        name=order_data.get("product_name", "新产品"),
                        product_type=product_type,
                        production_rate=order_data.get("production_rate", 100.0),
                    ),
                    quantity=order_data.get("quantity", 1000),
                    due_date=order_data.get("due_date", 72),
                    priority=order_data.get("priority", 1),
                    min_start_time=order_data.get("min_start_time", 0),
                )
                orders.append(new_order)

            elif change.change_type == ScenarioChangeType.REMOVE_ORDER:
                order_id = change.params.get("order_id", "")
                orders = [o for o in orders if o.id != order_id]

            elif change.change_type == ScenarioChangeType.MODIFY_ORDER:
                order_id = change.params.get("order_id", "")
                for idx, order in enumerate(orders):
                    if order.id == order_id:
                        new_data = order.model_copy()
                        if "quantity" in change.params:
                            new_data.quantity = change.params["quantity"]
                        if "due_date" in change.params:
                            new_data.due_date = change.params["due_date"]
                        if "priority" in change.params:
                            new_data.priority = change.params["priority"]
                        if "min_start_time" in change.params:
                            new_data.min_start_time = change.params["min_start_time"]
                        orders[idx] = new_data
                        break

            elif change.change_type == ScenarioChangeType.CHANGE_CONSTRAINT:
                if "max_daily_hours" in change.params:
                    constraints.max_daily_hours = change.params["max_daily_hours"]
                if "allow_overtime" in change.params:
                    constraints.allow_overtime = change.params["allow_overtime"]
                if "max_overtime_hours" in change.params:
                    constraints.max_overtime_hours = change.params["max_overtime_hours"]

            elif change.change_type == ScenarioChangeType.MACHINE_DOWN:
                machine_id = change.params.get("machine_id", "")
                machines = [m for m in machines if m.id != machine_id]

        return orders, machines, constraints

    def _build_report(
        self,
        baseline: ScheduleResult,
        scenario_result: ScheduleResult,
        scenario: WhatIfScenario,
        simulation_time: float,
    ) -> WhatIfReport:
        """构建对比报告"""
        baseline_util = self._avg_utilization(baseline)
        scenario_util = self._avg_utilization(scenario_result)

        return WhatIfReport(
            scenario_name=scenario.name,
            scenario_description=scenario.description,
            makespan_comparison=self._compare_metric(
                baseline.total_makespan, scenario_result.total_makespan, lower_is_better=True
            ),
            on_time_rate_comparison=self._compare_metric(
                baseline.on_time_delivery_rate, scenario_result.on_time_delivery_rate, lower_is_better=False
            ),
            changeover_comparison=self._compare_metric(
                baseline.total_changeover_time, scenario_result.total_changeover_time, lower_is_better=True
            ),
            utilization_comparison=self._compare_metric(
                baseline_util, scenario_util, lower_is_better=False
            ),
            task_count_comparison=self._compare_metric(
                float(baseline.task_count), float(scenario_result.task_count), lower_is_better=False
            ),
            baseline_summary={
                "makespan": baseline.total_makespan,
                "on_time_rate": baseline.on_time_delivery_rate,
                "changeover": baseline.total_changeover_time,
                "tasks": baseline.task_count,
                "utilization": baseline_util,
            },
            scenario_summary={
                "makespan": scenario_result.total_makespan,
                "on_time_rate": scenario_result.on_time_delivery_rate,
                "changeover": scenario_result.total_changeover_time,
                "tasks": scenario_result.task_count,
                "utilization": scenario_util,
            },
            simulation_time_seconds=simulation_time,
            overall_improvement=self._is_improvement(baseline, scenario_result),
            score_delta=self._compute_score_delta(baseline, scenario_result),
        )

    @staticmethod
    def _compare_metric(
        baseline: float, scenario: float, lower_is_better: bool = True
    ) -> MetricComparison:
        """对比单个指标"""
        delta = scenario - baseline
        delta_percent = (delta / baseline * 100) if baseline != 0 else 0.0
        if lower_is_better:
            improved = delta < 0
        else:
            improved = delta > 0
        return MetricComparison(
            baseline_value=baseline,
            scenario_value=scenario,
            delta=delta,
            delta_percent=delta_percent,
            improved=improved,
        )

    @staticmethod
    def _avg_utilization(result: ScheduleResult) -> float:
        if not result.machine_utilization:
            return 0.0
        return sum(result.machine_utilization.values()) / len(result.machine_utilization)

    @staticmethod
    def _is_improvement(baseline: ScheduleResult, scenario: ScheduleResult) -> bool:
        """综合判断场景是否优于基准"""
        score_b = (
            baseline.on_time_delivery_rate * 0.4
            + WhatIfEngine._avg_utilization(baseline) * 0.3
            + (1.0 - min(1.0, baseline.total_changeover_time / max(1.0, baseline.total_makespan))) * 0.3
        )
        score_s = (
            scenario.on_time_delivery_rate * 0.4
            + WhatIfEngine._avg_utilization(scenario) * 0.3
            + (1.0 - min(1.0, scenario.total_changeover_time / max(1.0, scenario.total_makespan))) * 0.3
        )
        return score_s > score_b

    @staticmethod
    def _compute_score_delta(baseline: ScheduleResult, scenario: ScheduleResult) -> float:
        """计算综合评分变化"""
        def score(r: ScheduleResult) -> float:
            return (
                r.on_time_delivery_rate * 0.4
                + WhatIfEngine._avg_utilization(r) * 0.3
                + (1.0 - min(1.0, r.total_changeover_time / max(1.0, r.total_makespan))) * 0.3
            )
        return score(scenario) - score(baseline)
