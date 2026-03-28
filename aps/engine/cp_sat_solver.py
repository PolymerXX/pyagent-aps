"""OR-Tools CP-SAT求解器

使用Google OR-Tools CP-SAT求解器进行生产排产优化
"""

import time

try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False

from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


class CPSATSolver:
    """OR-Tools CP-SAT求解器"""

    def __init__(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints | None = None,
        params: OptimizationParams | None = None,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.params = params or OptimizationParams()

    def solve(self) -> ScheduleResult:
        """执行CP-SAT求解"""
        start_time = time.time()

        if not self.orders or not self.machines:
            return ScheduleResult(
                assignments=[],
                total_makespan=0.0,
                planning_time_seconds=time.time() - start_time,
            )

        if not HAS_ORTOOLS:
            return self._fallback_solve(start_time)

        return self._solve_with_cp_sat(start_time)

    def _solve_with_cp_sat(self, start_time: float) -> ScheduleResult:
        """使用CP-SAT求解"""
        model = cp_model.CpModel()

        order_count = len(self.orders)
        machine_count = len(self.machines)

        max_horizon = sum(
            o.quantity / m.capacity_per_hour
            for o in self.orders
            for m in self.machines
        )
        horizon = int(max_horizon * 2) + 100

        starts = {}
        ends = {}
        intervals = {}
        assigned = {}

        for i, order in enumerate(self.orders):
            for j, machine in enumerate(self.machines):
                if not machine.can_produce(order.product.product_type):
                    continue

                duration = int(order.quantity / machine.capacity_per_hour)
                if duration <= 0:
                    duration = 1

                suffix = f"_{i}_{j}"
                starts[(i, j)] = model.NewIntVar(0, horizon, f"start{suffix}")
                ends[(i, j)] = model.NewIntVar(0, horizon, f"end{suffix}")
                assigned[(i, j)] = model.NewBoolVar(f"assigned{suffix}")

                intervals[(i, j)] = model.NewOptionalIntervalVar(
                    starts[(i, j)],
                    duration,
                    ends[(i, j)],
                    assigned[(i, j)],
                    f"interval{suffix}",
                )

        for i in range(order_count):
            compatible_machines = [
                j for j in range(machine_count)
                if (i, j) in assigned and self.machines[j].can_produce(
                    self.orders[i].product.product_type
                )
            ]
            if compatible_machines:
                model.AddExactlyOne([assigned[(i, j)] for j in compatible_machines])

        for j in range(machine_count):
            machine_intervals = [
                intervals[(i, j)]
                for i in range(order_count)
                if (i, j) in intervals
            ]
            if machine_intervals:
                model.AddNoOverlap(machine_intervals)

        makespan = model.NewIntVar(0, horizon, "makespan")
        all_ends = list(ends.values())
        if all_ends:
            model.AddMaxEquality(makespan, all_ends)

        total_delay = model.NewIntVar(0, horizon * order_count, "total_delay")
        delays = []
        for i, order in enumerate(self.orders):
            order_delay = model.NewIntVar(0, horizon, f"delay_{i}")
            compatible_machines = [
                j for j in range(machine_count)
                if (i, j) in ends and self.machines[j].can_produce(
                    self.orders[i].product.product_type
                )
            ]
            if compatible_machines:
                for j in compatible_machines:
                    due = int(order.due_date)
                    model.Add(order_delay >= ends[(i, j)] - due).OnlyEnforceIf(assigned[(i, j)])
                model.Add(order_delay == 0).OnlyEnforceIf(
                    [assigned[(i, j)].Not() for j in compatible_machines]
                )
            else:
                model.Add(order_delay == 0)
            delays.append(order_delay)

        if delays:
            model.Add(total_delay == sum(delays))

        if self.params.strategy == OptimizationStrategy.ON_TIME_DELIVERY:
            model.Minimize(total_delay)
        else:
            model.Minimize(makespan)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.params.time_limit_seconds
        solver.parameters.num_search_workers = 1

        status = solver.Solve(model)

        planning_time = time.time() - start_time

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return self._extract_solution(
                solver, starts, ends, assigned, planning_time,
                status == cp_model.OPTIMAL
            )

        return ScheduleResult(
            assignments=[],
            total_makespan=0.0,
            planning_time_seconds=planning_time,
            is_optimal=False,
        )

    def _extract_solution(
        self,
        solver,
        starts: dict,
        ends: dict,
        assigned: dict,
        planning_time: float,
        is_optimal: bool,
    ) -> ScheduleResult:
        """提取求解结果"""
        assignments = []

        for (i, j), var in assigned.items():
            if solver.Value(var):
                order = self.orders[i]
                machine = self.machines[j]

                start = solver.Value(starts[(i, j)])
                end = solver.Value(ends[(i, j)])

                is_on_time = end <= order.due_date
                delay_hours = max(0, end - order.due_date)

                assignment = TaskAssignment(
                    order_id=order.id,
                    machine_id=machine.id,
                    product_name=order.product.name,
                    product_type=order.product.product_type.value,
                    start_time=float(start),
                    end_time=float(end),
                    quantity=order.quantity,
                    status=TaskStatus.PLANNED,
                    is_on_time=is_on_time,
                    delay_hours=delay_hours,
                )
                assignments.append(assignment)

        assignments.sort(key=lambda a: a.start_time)

        makespan = max((a.end_time for a in assignments), default=0.0)
        on_time_count = sum(1 for a in assignments if a.is_on_time)
        on_time_rate = on_time_count / len(assignments) if assignments else 1.0

        utilization = self._calculate_utilization(assignments, makespan)

        return ScheduleResult(
            assignments=assignments,
            total_makespan=makespan,
            on_time_delivery_rate=on_time_rate,
            total_changeover_time=0.0,
            machine_utilization=utilization,
            planning_time_seconds=planning_time,
            is_optimal=is_optimal,
        )

    def _fallback_solve(self, start_time: float) -> ScheduleResult:
        """回退到启发式求解"""
        assignments = self._heuristic_schedule()

        makespan = max((a.end_time for a in assignments), default=0.0)
        on_time_count = sum(1 for a in assignments if a.is_on_time)
        on_time_rate = on_time_count / len(assignments) if assignments else 1.0

        utilization = self._calculate_utilization(assignments, makespan)

        return ScheduleResult(
            assignments=assignments,
            total_makespan=makespan,
            on_time_delivery_rate=on_time_rate,
            total_changeover_time=0.0,
            machine_utilization=utilization,
            planning_time_seconds=time.time() - start_time,
            is_optimal=False,
        )

    def _heuristic_schedule(self) -> list[TaskAssignment]:
        """启发式排产算法"""
        assignments = []
        sorted_orders = sorted(self.orders, key=lambda o: o.due_date)
        machine_times: dict[str, float] = {m.id: 0.0 for m in self.machines}

        for order in sorted_orders:
            best_machine = None
            best_start = float("inf")

            for machine in self.machines:
                if not machine.can_produce(order.product.product_type):
                    continue

                start_time = machine_times[machine.id]
                if start_time < best_start:
                    best_start = start_time
                    best_machine = machine

            if best_machine is None:
                continue

            duration = order.quantity / best_machine.capacity_per_hour
            end_time = best_start + duration

            assignment = TaskAssignment(
                order_id=order.id,
                machine_id=best_machine.id,
                product_name=order.product.name,
                product_type=order.product.product_type.value,
                start_time=best_start,
                end_time=end_time,
                quantity=order.quantity,
                status=TaskStatus.PLANNED,
                is_on_time=end_time <= order.due_date,
                delay_hours=max(0, end_time - order.due_date),
            )

            assignments.append(assignment)
            machine_times[best_machine.id] = end_time

        return assignments

    def _calculate_utilization(
        self, assignments: list[TaskAssignment], makespan: float
    ) -> dict[str, float]:
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
