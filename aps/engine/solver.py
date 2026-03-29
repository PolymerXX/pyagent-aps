"""APS排产求解器

自动选择最优求解器：
- OR-Tools CP-SAT（如果可用）- 提供最优解
- 启发式算法（回退）- 快速但可能非最优
"""

import time

from pydantic import BaseModel, Field

from aps.engine.cp_sat_solver import HAS_ORTOOLS, CPSATSolver
from aps.engine.schedule_metrics import calculate_machine_utilization
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams
from aps.models.order import Order
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


class FeasibilityReport(BaseModel):
    """产能可行性报告"""

    is_feasible: bool = Field(..., description="是否可行")
    total_demand_hours: float = Field(..., description="总需求工时")
    total_capacity_hours: float = Field(..., description="总可用工时")
    utilization_estimate: float = Field(..., ge=0.0, description="预估利用率")
    bottleneck_machine: str | None = Field(None, description="瓶颈机器ID")
    bottleneck_utilization: float = Field(default=0.0, description="瓶颈机器利用率")
    recommendations: list[str] = Field(default_factory=list, description="建议")
    per_machine_analysis: dict[str, dict] = Field(default_factory=dict, description="各机器分析")


class APSSolver:
    """APS排产求解器

    自动检测并使用最优求解器：
    - 当OR-Tools可用时，使用CP-SAT求解器获得最优解
    - 否则回退到启发式算法
    """

    def __init__(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints | None = None,
        params: OptimizationParams | None = None,
        use_cp_sat: bool = True,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.params = params or OptimizationParams()
        self.use_cp_sat = use_cp_sat and HAS_ORTOOLS
        self._use_cache = True
        self._profiler = None

    def solve(self) -> ScheduleResult:
        """执行求解

        自动选择求解器：
        - CP-SAT（如果use_cp_sat=True且OR-Tools可用）
        - 启发式算法（回退）
        """
        from aps.engine.cache import get_solver_cache
        from aps.engine.profiler import get_profiler

        start_time = time.time()
        profiler = self._profiler or get_profiler()

        if not self.orders:
            return ScheduleResult(
                assignments=[],
                total_makespan=0.0,
                planning_time_seconds=time.time() - start_time,
            )

        if not self.machines:
            return ScheduleResult(
                assignments=[],
                total_makespan=0.0,
                planning_time_seconds=time.time() - start_time,
            )

        solver_type = "cp_sat" if self.use_cp_sat else "heuristic"

        if self._use_cache:
            cached = get_solver_cache().get(
                self.orders,
                self.machines,
                self.constraints,
                self.params,
                solver_type=solver_type,
            )
            if cached is not None:
                profiler.record_result(cached, from_cache=True)
                return cached

        with profiler.measure("solve"):
            if self.use_cp_sat:
                result = self._solve_with_cp_sat()
            else:
                result = self._solve_with_heuristic(start_time)

        profiler.record_result(result, from_cache=False)

        if self._use_cache:
            get_solver_cache().set(
                self.orders,
                self.machines,
                self.constraints,
                self.params,
                result,
                solver_type=solver_type,
            )

        return result

    def _solve_with_cp_sat(self) -> ScheduleResult:
        """使用CP-SAT求解器"""
        solver = CPSATSolver(
            orders=self.orders,
            machines=self.machines,
            constraints=self.constraints,
            params=self.params,
        )
        return solver.solve()

    def _solve_with_heuristic(self, start_time: float) -> ScheduleResult:
        """使用启发式算法求解"""
        assignments = self._heuristic_schedule()
        makespan = max(a.end_time for a in assignments) if assignments else 0.0
        on_time_count = sum(1 for a in assignments if a.is_on_time)
        on_time_rate = on_time_count / len(assignments) if assignments else 1.0

        total_changeover = 0.0
        for machine in self.machines:
            machine_assignments = sorted(
                [a for a in assignments if a.machine_id == machine.id],
                key=lambda a: a.start_time,
            )
            for k in range(1, len(machine_assignments)):
                prev_type = machine_assignments[k - 1].product_type
                curr_type = machine_assignments[k].product_type
                total_changeover += self.constraints.get_changeover_time(prev_type, curr_type)

        utilization = calculate_machine_utilization(assignments, self.machines, makespan)
        planning_time = time.time() - start_time

        return ScheduleResult(
            assignments=assignments,
            total_makespan=makespan,
            on_time_delivery_rate=on_time_rate,
            total_changeover_time=total_changeover,
            machine_utilization=utilization,
            planning_time_seconds=planning_time,
            is_optimal=False,
        )

    def _heuristic_schedule(self) -> list[TaskAssignment]:
        """启发式排产算法"""
        assignments = []
        sorted_orders = sorted(self.orders, key=lambda o: o.due_date)
        machine_times: dict[str, float] = {m.id: 0.0 for m in self.machines}
        machine_last_type: dict[str, str] = {}

        for order in sorted_orders:
            best_machine = None
            best_start = float("inf")

            for machine in self.machines:
                if not machine.can_produce(order.product.product_type):
                    continue

                start_time = machine_times[machine.id]
                last_type = machine_last_type.get(machine.id)
                if last_type is not None and last_type != order.product.product_type.value:
                    start_time += self.constraints.get_changeover_time(
                        last_type, order.product.product_type.value
                    )

                if start_time < best_start:
                    best_start = start_time
                    best_machine = machine

            if best_machine is None:
                continue

            duration = order.quantity / best_machine.capacity_per_hour
            end_time = best_start + duration

            is_on_time = end_time <= order.due_date
            delay_hours = max(0, end_time - order.due_date)

            assignment = TaskAssignment(
                order_id=order.id,
                machine_id=best_machine.id,
                product_name=order.product.name,
                product_type=order.product.product_type.value,
                start_time=best_start,
                end_time=end_time,
                quantity=order.quantity,
                status=TaskStatus.PLANNED,
                is_on_time=is_on_time,
                delay_hours=delay_hours,
            )

            assignments.append(assignment)
            machine_times[best_machine.id] = end_time
            machine_last_type[best_machine.id] = order.product.product_type.value

        return assignments

    def enable_cache(self, enabled: bool = True) -> "APSSolver":
        """启用/禁用缓存"""
        self._use_cache = enabled
        return self

    def set_profiler(self, profiler) -> "APSSolver":
        """设置性能分析器"""
        self._profiler = profiler
        return self

    @staticmethod
    def check_feasibility(
        orders: list[Order],
        machines: list[ProductionLine],
        horizon: float = 168.0,
        constraints: ProductionConstraints | None = None,
    ) -> FeasibilityReport:
        """快速产能可行性检查（不完整求解）

        Args:
            orders: 订单列表
            machines: 机器列表
            horizon: 计划周期（小时），默认 168（一周）
            constraints: 生产约束

        Returns:
            FeasibilityReport 包含可行性和瓶颈分析
        """
        if not orders or not machines:
            return FeasibilityReport(
                is_feasible=True,
                total_demand_hours=0.0,
                total_capacity_hours=0.0,
                utilization_estimate=0.0,
            )

        per_machine: dict[str, dict] = {}
        constraints = constraints or ProductionConstraints()

        for machine in machines:
            compatible_orders = [o for o in orders if machine.can_produce(o.product.product_type)]
            demand_hours = sum(o.quantity / machine.capacity_per_hour for o in compatible_orders)
            capacity_hours = machine.capacity_per_hour * horizon

            per_machine[machine.id] = {
                "demand_hours": round(demand_hours, 2),
                "capacity_hours": round(capacity_hours, 2),
                "utilization": round(demand_hours / capacity_hours, 4)
                if capacity_hours > 0
                else 0.0,
                "compatible_orders": len(compatible_orders),
            }

        total_demand_hours = 0.0
        for order in orders:
            best_rate = 0.0
            for machine in machines:
                if machine.can_produce(order.product.product_type):
                    rate = machine.capacity_per_hour
                    if rate > best_rate:
                        best_rate = rate
            if best_rate > 0:
                total_demand_hours += order.quantity / best_rate

        total_capacity_hours = sum(m.capacity_per_hour * horizon for m in machines)

        utilization_estimate = (
            total_demand_hours / total_capacity_hours if total_capacity_hours > 0 else 0.0
        )

        bottleneck_machine = None
        bottleneck_util = 0.0
        for machine_id, analysis in per_machine.items():
            if analysis["utilization"] > bottleneck_util:
                bottleneck_util = analysis["utilization"]
                bottleneck_machine = machine_id

        is_feasible = utilization_estimate <= 1.0 and bottleneck_util <= 1.0

        recommendations = []
        if not is_feasible:
            if utilization_estimate > 1.0:
                recommendations.append(
                    f"总产能不足：需求 {total_demand_hours:.1f}h > 可用 {total_capacity_hours:.1f}h，"
                    f"建议增加机器或减少订单"
                )
            if bottleneck_util > 1.0:
                recommendations.append(
                    f"机器 {bottleneck_machine} 是瓶颈（利用率 {bottleneck_util * 100:.0f}%），"
                    f"建议增加同类机器或转移部分订单"
                )
        elif utilization_estimate > 0.85:
            recommendations.append("产能利用率较高，建议预留缓冲应对变更")
        elif utilization_estimate < 0.5:
            recommendations.append("产能利用率较低，可考虑承接更多订单")
        else:
            recommendations.append("产能利用率合理")

        for order in orders:
            has_compatible = any(m.can_produce(order.product.product_type) for m in machines)
            if not has_compatible:
                is_feasible = False
                recommendations.append(
                    f"订单 {order.id}（产品类型 {order.product.product_type.value}）无可用机器"
                )

        return FeasibilityReport(
            is_feasible=is_feasible,
            total_demand_hours=round(total_demand_hours, 2),
            total_capacity_hours=round(total_capacity_hours, 2),
            utilization_estimate=round(utilization_estimate, 4),
            bottleneck_machine=bottleneck_machine,
            bottleneck_utilization=round(bottleneck_util, 4),
            recommendations=recommendations,
            per_machine_analysis=per_machine,
        )


def check_feasibility(
    orders: list[Order],
    machines: list[ProductionLine],
    horizon: float = 168.0,
    constraints: ProductionConstraints | None = None,
) -> FeasibilityReport:
    """快速产能可行性检查（模块级便捷函数）

    详见 :meth:`APSSolver.check_feasibility`
    """
    return APSSolver.check_feasibility(orders, machines, horizon, constraints)
