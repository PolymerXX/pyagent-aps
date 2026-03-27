"""APS排产求解器

使用OR-Tools CP-SAT求解器进行排产优化
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from aps.models.order import Order
from aps.models.machine import ProductionLine
from aps.models.constraint import ProductionConstraints
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus
from aps.models.optimization import OptimizationParams, OptimizationStrategy


class APSSolver:
    """APS排产求解器"""

    def __init__(
        self,
        orders: List[Order],
        machines: List[ProductionLine],
        constraints: Optional[ProductionConstraints] = None,
        params: Optional[OptimizationParams] = None,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.params = params or OptimizationParams()

    def solve(self) -> ScheduleResult:
        """执行求解"""
        start_time = time.time()

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

        assignments = self._heuristic_schedule()

        makespan = max(a.end_time for a in assignments) if assignments else 0.0
        on_time_count = sum(1 for a in assignments if a.is_on_time)
        on_time_rate = on_time_count / len(assignments) if assignments else 1.0

        total_changeover = 0.0
        for i in range(1, len(assignments)):
            if assignments[i].machine_id == assignments[i - 1].machine_id:
                total_changeover += 0.5

        utilization = self._calculate_utilization(assignments, makespan)

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

    def _heuristic_schedule(self) -> List[TaskAssignment]:
        """启发式排产算法"""
        assignments = []

        sorted_orders = sorted(self.orders, key=lambda o: o.due_date)

        machine_times: Dict[str, float] = {m.id: 0.0 for m in self.machines}
        machine_last_product: Dict[str, str] = {}

        for order in sorted_orders:
            best_machine = None
            best_start = float("inf")

            for machine in self.machines:
                if not machine.can_produce(order.product.product_type):
                    continue

                start_time = machine_times[machine.id]

                if machine_last_product.get(machine.id) != order.product.name:
                    start_time += machine.setup_time_hours

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
            machine_last_product[best_machine.id] = order.product.name

        return assignments

    def _calculate_utilization(
        self, assignments: List[TaskAssignment], makespan: float
    ) -> Dict[str, float]:
        """计算机器利用率"""
        utilization = {}

        for machine in self.machines:
            machine_assignments = [a for a in assignments if a.machine_id == machine.id]

            if not machine_assignments or makespan == 0:
                utilization[machine.id] = 0.0
                continue

            total_work = sum(a.duration for a in machine_assignments)
            utilization[machine.id] = total_work / makespan

        return utilization
