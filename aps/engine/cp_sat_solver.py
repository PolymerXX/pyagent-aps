"""OR-Tools CP-SAT求解器

使用Google OR-Tools CP-SAT求解器进行生产排产优化
"""

import time
from typing import Any

try:
    from ortools.sat.python import cp_model

    HAS_ORTOOLS = True
except ImportError:
    cp_model = None
    HAS_ORTOOLS = False

from aps.engine.schedule_metrics import calculate_machine_utilization
from aps.models.calendar import ProductionCalendar
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
        calendar: ProductionCalendar | None = None,
        max_splits: int = 1,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.params = params or OptimizationParams()
        self.calendar = calendar
        self.max_splits = max(1, max_splits)

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
        assert cp_model is not None
        model: Any = cp_model.CpModel()

        order_count = len(self.orders)
        machine_count = len(self.machines)

        max_horizon = sum(
            o.quantity / m.capacity_per_hour for o in self.orders for m in self.machines
        )
        horizon = int(max_horizon * 2) + 100

        starts: dict[tuple[int, int], Any] = {}
        ends: dict[tuple[int, int], Any] = {}
        intervals: dict[tuple[int, int], Any] = {}
        assigned: dict[tuple[int, int], Any] = {}

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
                j
                for j in range(machine_count)
                if (i, j) in assigned
                and self.machines[j].can_produce(self.orders[i].product.product_type)
            ]
            if not compatible_machines:
                continue
            if self.max_splits <= 1:
                model.AddExactlyOne([assigned[(i, j)] for j in compatible_machines])
            else:
                total_assigned_for_order = sum(
                    assigned[(i, j)] for j in compatible_machines
                )
                model.Add(total_assigned_for_order >= 1)
                model.Add(
                    total_assigned_for_order
                    <= min(self.max_splits, len(compatible_machines))
                )

        for i, order in enumerate(self.orders):
            for j in range(machine_count):
                if (i, j) in assigned:
                    model.Add(starts[(i, j)] >= order.min_start_time).OnlyEnforceIf(
                        assigned[(i, j)]
                    )

        for j in range(machine_count):
            machine_intervals = [
                intervals[(i, j)] for i in range(order_count) if (i, j) in intervals
            ]

            if self.calendar:
                machine = self.machines[j]
                maint_intervals_data = self.calendar.get_maintenance_intervals(
                    machine.id, horizon
                )
                for idx, (m_start, m_end) in enumerate(maint_intervals_data):
                    m_duration = int(m_end - m_start)
                    if m_duration <= 0:
                        continue
                    maint_interval = model.NewFixedSizeIntervalVar(
                        int(m_start), m_duration, f"maint_{j}_{idx}"
                    )
                    machine_intervals.append(maint_interval)

            if machine_intervals:
                model.AddNoOverlap(machine_intervals)

        changeover_vars: list[Any] = []
        for j in range(machine_count):
            machine_order_indices = [i for i in range(order_count) if (i, j) in assigned]
            for idx_a in range(len(machine_order_indices)):
                for idx_b in range(idx_a + 1, len(machine_order_indices)):
                    i = machine_order_indices[idx_a]
                    k = machine_order_indices[idx_b]

                    before = model.NewBoolVar(f"before_{i}_{k}_{j}")

                    type_i = self.orders[i].product.product_type.value
                    type_k = self.orders[k].product.product_type.value
                    setup_ik = int(self.constraints.get_changeover_time(type_i, type_k))
                    setup_ki = int(self.constraints.get_changeover_time(type_k, type_i))

                    model.Add(starts[(k, j)] >= ends[(i, j)] + setup_ik).OnlyEnforceIf(
                        [before, assigned[(i, j)], assigned[(k, j)]]
                    )

                    model.Add(starts[(i, j)] >= ends[(k, j)] + setup_ki).OnlyEnforceIf(
                        [before.Not(), assigned[(i, j)], assigned[(k, j)]]
                    )

                    max_setup = max(setup_ik, setup_ki, 1)
                    changeover = model.NewIntVar(0, max_setup, f"changeover_{i}_{k}_{j}")
                    both_assigned = model.NewBoolVar(f"both_assigned_{i}_{k}_{j}")
                    model.AddBoolAnd([assigned[(i, j)], assigned[(k, j)]]).OnlyEnforceIf(
                        both_assigned
                    )
                    model.AddBoolOr([assigned[(i, j)].Not(), assigned[(k, j)].Not()]).OnlyEnforceIf(
                        both_assigned.Not()
                    )

                    model.Add(changeover == setup_ik).OnlyEnforceIf([both_assigned, before])
                    model.Add(changeover == setup_ki).OnlyEnforceIf([both_assigned, before.Not()])
                    model.Add(changeover == 0).OnlyEnforceIf(both_assigned.Not())

                    changeover_vars.append(changeover)

        makespan = model.NewIntVar(0, horizon, "makespan")
        all_ends = list(ends.values())
        if all_ends:
            model.AddMaxEquality(makespan, all_ends)

        total_delay = model.NewIntVar(0, horizon * order_count, "total_delay")
        delays = []
        for i, order in enumerate(self.orders):
            order_delay = model.NewIntVar(0, horizon, f"delay_{i}")
            compatible_machines = [
                j
                for j in range(machine_count)
                if (i, j) in ends
                and self.machines[j].can_produce(self.orders[i].product.product_type)
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

        total_changeover_model = model.NewIntVar(0, horizon * order_count, "total_changeover")
        if changeover_vars:
            model.Add(total_changeover_model == sum(changeover_vars))
        else:
            model.Add(total_changeover_model == 0)

        if self.params.strategy == OptimizationStrategy.ON_TIME_DELIVERY:
            model.Minimize(total_delay)
        elif self.params.strategy == OptimizationStrategy.MINIMIZE_CHANGEOVER:
            model.Minimize(total_changeover_model)
        elif self.params.strategy == OptimizationStrategy.MAX_UTILIZATION:
            model.Minimize(makespan)
        elif self.params.strategy == OptimizationStrategy.MAXIMIZE_PROFIT:
            model.Minimize(makespan)
        else:
            nw = self.params.weights.normalize()
            coeff_delay = max(1, int(nw.on_time * 100))
            coeff_changeover = max(1, int(nw.changeover * 100))
            coeff_makespan = max(1, int((nw.utilization + nw.profit) * 100))
            model.Minimize(
                coeff_delay * total_delay
                + coeff_changeover * total_changeover_model
                + coeff_makespan * makespan
            )

        solver: Any = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.params.time_limit_seconds
        solver.parameters.num_search_workers = 1

        status = solver.Solve(model)

        planning_time = time.time() - start_time

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return self._extract_solution(
                solver, starts, ends, assigned, planning_time, status == cp_model.OPTIMAL
            )

        return ScheduleResult(
            assignments=[],
            total_makespan=0.0,
            planning_time_seconds=planning_time,
            is_optimal=False,
        )

    def _extract_solution(
        self,
        solver: Any,
        starts: dict,
        ends: dict,
        assigned: dict,
        planning_time: float,
        is_optimal: bool,
    ) -> ScheduleResult:
        order_assignments: dict[int, list[int]] = {}

        for (i, j), var in assigned.items():
            if solver.Value(var):
                order_assignments.setdefault(i, []).append(j)

        assignments = []
        for i, machine_indices in order_assignments.items():
            order = self.orders[i]
            num_splits = len(machine_indices)

            for split_idx, j in enumerate(machine_indices):
                machine = self.machines[j]

                start = solver.Value(starts[(i, j)])
                end = solver.Value(ends[(i, j)])

                if num_splits > 1:
                    base_qty = order.quantity // num_splits
                    if split_idx == num_splits - 1:
                        split_quantity = order.quantity - base_qty * (num_splits - 1)
                    else:
                        split_quantity = base_qty
                else:
                    split_quantity = order.quantity

                is_on_time = end <= order.due_date
                delay_hours = max(0, end - order.due_date)

                assignment = TaskAssignment(
                    order_id=order.id,
                    machine_id=machine.id,
                    product_name=order.product.name,
                    product_type=order.product.product_type.value,
                    start_time=float(start),
                    end_time=float(end),
                    quantity=split_quantity,
                    status=TaskStatus.PLANNED,
                    is_on_time=is_on_time,
                    delay_hours=delay_hours,
                    parent_order_id=order.id if num_splits > 1 else None,
                    split_index=split_idx if num_splits > 1 else 0,
                )
                assignments.append(assignment)

        assignments.sort(key=lambda a: a.start_time)

        makespan = max((a.end_time for a in assignments), default=0.0)
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

        return ScheduleResult(
            assignments=assignments,
            total_makespan=makespan,
            on_time_delivery_rate=on_time_rate,
            total_changeover_time=total_changeover,
            machine_utilization=utilization,
            planning_time_seconds=planning_time,
            is_optimal=is_optimal,
        )

    def _fallback_solve(self, start_time: float) -> ScheduleResult:
        if self.max_splits > 1:
            assignments = self._heuristic_schedule_with_splits()
        else:
            assignments = self._heuristic_schedule()

        makespan = max((a.end_time for a in assignments), default=0.0)
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

        return ScheduleResult(
            assignments=assignments,
            total_makespan=makespan,
            on_time_delivery_rate=on_time_rate,
            total_changeover_time=total_changeover,
            machine_utilization=utilization,
            planning_time_seconds=time.time() - start_time,
            is_optimal=False,
        )

    def _heuristic_schedule(self) -> list[TaskAssignment]:
        assignments = []
        sorted_orders = sorted(self.orders, key=lambda o: o.due_date)
        machine_times: dict[str, float] = {m.id: 0.0 for m in self.machines}
        machine_last_product: dict[str, str] = {}

        for order in sorted_orders:
            best_machine = None
            best_start = float("inf")

            for machine in self.machines:
                if not machine.can_produce(order.product.product_type):
                    continue

                start_time = machine_times[machine.id]
                last_product = machine_last_product.get(machine.id)
                if last_product is not None and last_product != order.product.product_type.value:
                    start_time += self.constraints.get_changeover_time(
                        last_product, order.product.product_type.value
                    )

                if self.calendar:
                    start_time = self.calendar.next_available_time(
                        start_time, machine.id
                    )

                if start_time < best_start:
                    best_start = start_time
                    best_machine = machine

            if best_machine is None:
                continue

            duration = order.quantity / best_machine.capacity_per_hour
            end_time = best_start + duration

            if self.calendar:
                end_time = self.calendar.next_available_time(
                    end_time, best_machine.id
                )
                if end_time > best_start + duration:
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
            machine_last_product[best_machine.id] = order.product.product_type.value

        return assignments

    def _heuristic_schedule_with_splits(self) -> list[TaskAssignment]:
        assignments = []
        sorted_orders = sorted(self.orders, key=lambda o: o.due_date)
        machine_times: dict[str, float] = {m.id: 0.0 for m in self.machines}
        machine_last_product: dict[str, str] = {}

        for order in sorted_orders:
            compatible = [
                m for m in self.machines if m.can_produce(order.product.product_type)
            ]
            if not compatible:
                continue

            full_duration = order.quantity / compatible[0].capacity_per_hour

            if full_duration <= 2.0 or len(compatible) < 2:
                best_machine = None
                best_start = float("inf")

                for machine in compatible:
                    start_time = machine_times[machine.id]
                    last_product = machine_last_product.get(machine.id)
                    if last_product is not None and last_product != order.product.product_type.value:
                        start_time += self.constraints.get_changeover_time(
                            last_product, order.product.product_type.value
                        )
                    if self.calendar:
                        start_time = self.calendar.next_available_time(start_time, machine.id)
                    if start_time < best_start:
                        best_start = start_time
                        best_machine = machine

                if best_machine is None:
                    continue

                duration = order.quantity / best_machine.capacity_per_hour
                end_time = best_start + duration
                if self.calendar:
                    cal_end = self.calendar.next_available_time(end_time, best_machine.id)
                    if cal_end > best_start + duration:
                        end_time = best_start + duration
                    else:
                        end_time = cal_end

                assignments.append(
                    TaskAssignment(
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
                        parent_order_id=None,
                        split_index=0,
                    )
                )
                machine_times[best_machine.id] = end_time
                machine_last_product[best_machine.id] = order.product.product_type.value
            else:
                candidates = []
                for machine in compatible:
                    start_time = machine_times[machine.id]
                    last_product = machine_last_product.get(machine.id)
                    if last_product is not None and last_product != order.product.product_type.value:
                        start_time += self.constraints.get_changeover_time(
                            last_product, order.product.product_type.value
                        )
                    if self.calendar:
                        start_time = self.calendar.next_available_time(start_time, machine.id)
                    candidates.append((start_time, machine))

                candidates.sort(key=lambda x: x[0])
                num_splits = min(self.max_splits, len(candidates))
                base_qty = order.quantity // num_splits

                for split_idx in range(num_splits):
                    _, machine = candidates[split_idx]
                    split_quantity = base_qty
                    if split_idx == num_splits - 1:
                        split_quantity = order.quantity - base_qty * (num_splits - 1)

                    start_time = machine_times[machine.id]
                    last_product = machine_last_product.get(machine.id)
                    if last_product is not None and last_product != order.product.product_type.value:
                        start_time += self.constraints.get_changeover_time(
                            last_product, order.product.product_type.value
                        )
                    if self.calendar:
                        start_time = self.calendar.next_available_time(start_time, machine.id)

                    split_duration = split_quantity / machine.capacity_per_hour
                    end_time = start_time + split_duration
                    if self.calendar:
                        cal_end = self.calendar.next_available_time(end_time, machine.id)
                        if cal_end > start_time + split_duration:
                            end_time = start_time + split_duration
                        else:
                            end_time = cal_end

                    assignments.append(
                        TaskAssignment(
                            order_id=order.id,
                            machine_id=machine.id,
                            product_name=order.product.name,
                            product_type=order.product.product_type.value,
                            start_time=start_time,
                            end_time=end_time,
                            quantity=split_quantity,
                            status=TaskStatus.PLANNED,
                            is_on_time=end_time <= order.due_date,
                            delay_hours=max(0, end_time - order.due_date),
                            parent_order_id=order.id,
                            split_index=split_idx,
                        )
                    )
                    machine_times[machine.id] = end_time
                    machine_last_product[machine.id] = order.product.product_type.value

        return assignments
