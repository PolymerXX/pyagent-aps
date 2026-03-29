"""调整Agent - 处理实时变更（增量调整）"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.agents.base import create_model_settings
from aps.agents.validator import ValidationResult
from aps.core.config import get_settings
from aps.engine.solver import APSSolver
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams
from aps.models.order import Order
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


class AdjustmentType(str, Enum):
    NEW_ORDER = "new_order"
    MACHINE_DOWN = "machine_down"
    ORDER_CHANGE = "order_change"
    PRIORITY_CHANGE = "priority_change"


class Adjustment(BaseModel):
    """调整动作"""

    action_type: AdjustmentType = Field(..., description="调整类型")
    affected_orders: list[str] = Field(
        default_factory=list, description="受影响的订单ID"
    )
    reason: str = Field(..., description="调整原因")
    new_schedule_id: str | None = Field(None, description="新排程ID")
    new_schedule: ScheduleResult | None = Field(
        default=None, description="调整后的完整排程（若有）"
    )
    changes: dict[str, Any] = Field(default_factory=dict, description="变更详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class AdjusterAgent:
    """调整Agent - 增量调整实现"""

    def __init__(self):
        self.config = get_settings()
        self.settings = create_model_settings(temperature=0.3)
        self.constraints = ProductionConstraints()

        self.agent = Agent(
            self.config.default_model,
            model_settings=self.settings,
            instructions=self._get_instructions(),
            output_type=Adjustment,
        )

    def _get_instructions(self) -> str:
        return """你是APS系统的方案调整Agent。

你的职责是处理实时变更并生成调整后的排程方案。

**处理场景**：
1. 新订单接入 - 增量添加
2. 设备故障 - 临时排除机器
3. 订单变更 - 更新属性

**调整策略**：
- 增量调整: 仅处理变更部分，冻结已有任务
- 局部调整: 最小化影响范围
- 优先级调整: 根据新情况重排
"""

    async def handle_new_order(
        self,
        order: Order,
        machines: list[ProductionLine],
        orders: list[Order],
        existing_result: ScheduleResult | None = None,
    ) -> Adjustment:
        """处理新订单 - 增量插入或全量求解"""
        if existing_result is not None and existing_result.assignments:
            return await self._incremental_new_order(
                order, machines, existing_result, orders
            )
        return await self._full_solve_new_order(order, machines, orders)

    async def _incremental_new_order(
        self,
        order: Order,
        machines: list[ProductionLine],
        existing_result: ScheduleResult,
        all_orders: list[Order],
    ) -> Adjustment:
        """增量插入新订单到已有排程"""
        best_assignment = self._find_best_slot(order, existing_result.assignments, machines)

        if best_assignment is not None:
            new_assignments = list(existing_result.assignments) + [best_assignment]
            new_schedule = self._build_result_from_assignments(new_assignments)
            return Adjustment(
                action_type=AdjustmentType.NEW_ORDER,
                affected_orders=[order.id],
                reason=f"新订单 {order.id} 增量插入",
                new_schedule_id=f"adj-inc-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                new_schedule=new_schedule,
                changes={"added_order": order.id, "method": "incremental"},
                timestamp=datetime.now(),
            )

        return await self._full_solve_new_order(order, machines, all_orders)

    async def _full_solve_new_order(
        self,
        order: Order,
        machines: list[ProductionLine],
        orders: list[Order],
    ) -> Adjustment:
        """全量求解新订单"""
        params = OptimizationParams()
        all_orders = list(orders) + [order]
        schedule, schedule_id = await self._run_solver(all_orders, machines, params)

        return Adjustment(
            action_type=AdjustmentType.NEW_ORDER,
            affected_orders=[order.id],
            reason=f"新订单 {order.id} 加入（全量求解）",
            new_schedule_id=schedule_id,
            new_schedule=schedule,
            changes={"added_order": order.id, "method": "full_resolve"},
            timestamp=datetime.now(),
        )

    async def handle_machine_down(
        self,
        machine_id: str,
        orders: list[Order],
        machines: list[ProductionLine],
        existing_result: ScheduleResult | None = None,
    ) -> Adjustment:
        """处理机器故障 - 增量重新分配受影响任务"""
        available_machines = [m for m in machines if m.id != machine_id]

        if not available_machines:
            return Adjustment(
                action_type=AdjustmentType.MACHINE_DOWN,
                affected_orders=[o.id for o in orders],
                reason=f"机器 {machine_id} 故障且无替代机器",
                changes={"disabled_machine": machine_id},
                timestamp=datetime.now(),
            )

        if existing_result is not None and existing_result.assignments:
            return await self._incremental_machine_down(
                machine_id, available_machines, existing_result
            )

        params = OptimizationParams()
        schedule, schedule_id = await self._run_solver(orders, available_machines, params)

        affected = [a.order_id for a in schedule.assignments]
        return Adjustment(
            action_type=AdjustmentType.MACHINE_DOWN,
            affected_orders=affected,
            reason=f"机器 {machine_id} 故障（全量求解）",
            new_schedule_id=schedule_id,
            new_schedule=schedule,
            changes={"disabled_machine": machine_id, "method": "full_resolve"},
            timestamp=datetime.now(),
        )

    async def _incremental_machine_down(
        self,
        machine_id: str,
        available_machines: list[ProductionLine],
        existing_result: ScheduleResult,
    ) -> Adjustment:
        """增量处理机器故障 - 仅重新分配故障机器上的任务"""
        frozen_assignments = [
            a
            for a in existing_result.assignments
            if a.machine_id != machine_id
            or a.status in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        ]

        displaced = [
            a
            for a in existing_result.assignments
            if a.machine_id == machine_id
            and a.status not in (TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        ]

        if not displaced:
            new_schedule = self._build_result_from_assignments(frozen_assignments)
            return Adjustment(
                action_type=AdjustmentType.MACHINE_DOWN,
                affected_orders=[],
                reason=f"机器 {machine_id} 故障，无需要迁移的计划任务",
                new_schedule_id=f"adj-inc-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                new_schedule=new_schedule,
                changes={"disabled_machine": machine_id, "method": "incremental", "displaced": 0},
                timestamp=datetime.now(),
            )

        new_assignments = list(frozen_assignments)
        affected_order_ids: list[str] = []

        for displaced_task in displaced:
            fake_order = Order(
                id=displaced_task.order_id,
                product=None,
                quantity=displaced_task.quantity,
                due_date=int(displaced_task.start_time + displaced_task.duration),
                priority=1,
            )
            best = self._find_best_slot_raw(
                order_id=displaced_task.order_id,
                product_name=displaced_task.product_name,
                product_type=displaced_task.product_type,
                quantity=displaced_task.quantity,
                due_date=fake_order.due_date,
                frozen_assignments=new_assignments,
                machines=available_machines,
            )
            if best is not None:
                new_assignments.append(best)
                affected_order_ids.append(displaced_task.order_id)
            else:
                affected_order_ids.append(displaced_task.order_id)

        new_schedule = self._build_result_from_assignments(new_assignments)
        return Adjustment(
            action_type=AdjustmentType.MACHINE_DOWN,
            affected_orders=affected_order_ids,
            reason=f"机器 {machine_id} 故障（增量迁移 {len(displaced)} 个任务）",
            new_schedule_id=f"adj-inc-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            new_schedule=new_schedule,
            changes={
                "disabled_machine": machine_id,
                "method": "incremental",
                "displaced": len(displaced),
                "reassigned": len(affected_order_ids),
            },
            timestamp=datetime.now(),
        )

    async def handle_order_change(
        self,
        order_id: str,
        changes: dict,
        orders: list[Order],
        machines: list[ProductionLine],
        existing_result: ScheduleResult | None = None,
    ) -> Adjustment:
        """处理订单变更 - 增量调整受影响订单及下游任务"""
        if existing_result is not None and existing_result.assignments:
            return await self._incremental_order_change(
                order_id, changes, orders, machines, existing_result
            )

        params = OptimizationParams()
        schedule, schedule_id = await self._run_solver(orders, machines, params)
        return Adjustment(
            action_type=AdjustmentType.ORDER_CHANGE,
            affected_orders=[order_id],
            reason=f"订单 {order_id} 属性变更（全量求解）",
            new_schedule_id=schedule_id,
            new_schedule=schedule,
            changes={**changes, "method": "full_resolve"},
            timestamp=datetime.now(),
        )

    async def _incremental_order_change(
        self,
        order_id: str,
        changes: dict,
        orders: list[Order],
        machines: list[ProductionLine],
        existing_result: ScheduleResult,
    ) -> Adjustment:
        """增量处理订单变更 - 仅重新安排受影响订单及其下游任务"""
        target_assignment = None
        for a in existing_result.assignments:
            if a.order_id == order_id:
                target_assignment = a
                break

        if target_assignment is None:
            params = OptimizationParams()
            schedule, schedule_id = await self._run_solver(orders, machines, params)
            return Adjustment(
                action_type=AdjustmentType.ORDER_CHANGE,
                affected_orders=[order_id],
                reason=f"订单 {order_id} 属性变更（全量求解，未找到已有分配）",
                new_schedule_id=schedule_id,
                new_schedule=schedule,
                changes={**changes, "method": "full_resolve"},
                timestamp=datetime.now(),
            )

        machine_id = target_assignment.machine_id
        downstream = [
            a
            for a in existing_result.assignments
            if a.machine_id == machine_id
            and a.start_time >= target_assignment.start_time
            and a.order_id != order_id
            and a.status == TaskStatus.PLANNED
        ]

        frozen = [
            a
            for a in existing_result.assignments
            if a.order_id != order_id
            and a not in downstream
        ]

        order_map = {o.id: o for o in orders}
        order_obj = order_map.get(order_id)
        if order_obj is None:
            order_obj = Order(
                id=order_id,
                product=None,
                quantity=changes.get("quantity", target_assignment.quantity),
                due_date=changes.get("due_date", target_assignment.end_time),
            )

        new_quantity = changes.get("quantity", order_obj.quantity)
        new_due = changes.get("due_date", order_obj.due_date)
        if isinstance(new_due, float):
            new_due = int(new_due)

        reassigned_assignments = list(frozen)
        affected_ids: list[str] = []

        best = self._find_best_slot_raw(
            order_id=order_id,
            product_name=target_assignment.product_name,
            product_type=target_assignment.product_type,
            quantity=new_quantity,
            due_date=new_due,
            frozen_assignments=reassigned_assignments,
            machines=machines,
        )
        if best is not None:
            reassigned_assignments.append(best)
            affected_ids.append(order_id)

        for ds_task in sorted(downstream, key=lambda a: a.start_time):
            ds_order = order_map.get(ds_task.order_id)
            ds_due = ds_order.due_date if ds_order else int(ds_task.end_time)
            ds_best = self._find_best_slot_raw(
                order_id=ds_task.order_id,
                product_name=ds_task.product_name,
                product_type=ds_task.product_type,
                quantity=ds_task.quantity,
                due_date=ds_due,
                frozen_assignments=reassigned_assignments,
                machines=machines,
            )
            if ds_best is not None:
                reassigned_assignments.append(ds_best)
                affected_ids.append(ds_task.order_id)

        new_schedule = self._build_result_from_assignments(reassigned_assignments)
        return Adjustment(
            action_type=AdjustmentType.ORDER_CHANGE,
            affected_orders=affected_ids,
            reason=f"订单 {order_id} 属性变更（增量调整 {len(affected_ids)} 个任务）",
            new_schedule_id=f"adj-inc-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            new_schedule=new_schedule,
            changes={**changes, "method": "incremental"},
            timestamp=datetime.now(),
        )

    def _find_best_slot(
        self,
        order: Order,
        frozen_assignments: list[TaskAssignment],
        machines: list[ProductionLine],
    ) -> TaskAssignment | None:
        """为订单在已有排程中找到最佳插入位置"""
        return self._find_best_slot_raw(
            order_id=order.id,
            product_name=order.product.name,
            product_type=order.product.product_type.value,
            quantity=order.quantity,
            due_date=order.due_date,
            frozen_assignments=frozen_assignments,
            machines=machines,
        )

    def _find_best_slot_raw(
        self,
        order_id: str,
        product_name: str,
        product_type: str,
        quantity: int,
        due_date: int,
        frozen_assignments: list[TaskAssignment],
        machines: list[ProductionLine],
    ) -> TaskAssignment | None:
        """在冻结任务的约束下寻找最佳时间槽插入新任务"""
        best_machine: ProductionLine | None = None
        best_start = float("inf")
        best_end = float("inf")

        for machine in machines:
            if not machine.can_produce(product_type):
                continue

            frozen_on_machine = sorted(
                [a for a in frozen_assignments if a.machine_id == machine.id],
                key=lambda a: a.start_time,
            )

            duration = quantity / machine.capacity_per_hour
            candidate_start = self._find_earliest_gap(
                frozen_on_machine, product_type, duration, machine
            )

            if candidate_start < best_start:
                best_start = candidate_start
                best_machine = machine
                best_end = candidate_start + duration

        if best_machine is None:
            return None

        end_time = best_start + (quantity / best_machine.capacity_per_hour)
        return TaskAssignment(
            order_id=order_id,
            machine_id=best_machine.id,
            product_name=product_name,
            product_type=product_type,
            start_time=best_start,
            end_time=end_time,
            quantity=quantity,
            status=TaskStatus.PLANNED,
            is_on_time=end_time <= due_date,
            delay_hours=max(0.0, end_time - due_date),
        )

    def _find_earliest_gap(
        self,
        frozen_on_machine: list[TaskAssignment],
        product_type: str,
        duration: float,
        machine: ProductionLine,
    ) -> float:
        """在冻结任务之间找到满足时长的最早可用起始时间"""
        earliest = float("inf")

        if frozen_on_machine:
            gap_end = frozen_on_machine[0].start_time
            if duration <= gap_end:
                candidate = 0.0
                if candidate < earliest:
                    earliest = candidate

            for i in range(len(frozen_on_machine) - 1):
                prev = frozen_on_machine[i]
                nxt = frozen_on_machine[i + 1]
                gap_start = prev.end_time
                gap_end = nxt.start_time

                changeover_in = self.constraints.get_changeover_time(
                    prev.product_type, product_type
                )
                changeover_out = self.constraints.get_changeover_time(
                    product_type, nxt.product_type
                )
                needed = changeover_in + duration + changeover_out

                if needed <= gap_end - gap_start:
                    candidate = gap_start + changeover_in
                    if candidate < earliest:
                        earliest = candidate

            last = frozen_on_machine[-1]
            changeover_in = self.constraints.get_changeover_time(
                last.product_type, product_type
            )
            candidate = last.end_time + changeover_in
            if candidate < earliest:
                earliest = candidate
        else:
            earliest = 0.0

        return earliest

    def _build_result_from_assignments(
        self, assignments: list[TaskAssignment]
    ) -> ScheduleResult:
        """从任务分配列表构建 ScheduleResult"""
        if not assignments:
            return ScheduleResult()

        sorted_assignments = sorted(assignments, key=lambda a: a.start_time)
        makespan = max(a.end_time for a in sorted_assignments)
        total_on_time = sum(1 for a in sorted_assignments if a.is_on_time)
        delivery_rate = total_on_time / len(sorted_assignments) if sorted_assignments else 1.0

        total_changeover = 0.0
        machine_groups: dict[str, list[TaskAssignment]] = {}
        for a in sorted_assignments:
            machine_groups.setdefault(a.machine_id, []).append(a)

        for machine_id, tasks in machine_groups.items():
            tasks_sorted = sorted(tasks, key=lambda t: t.start_time)
            for i in range(len(tasks_sorted) - 1):
                total_changeover += self.constraints.get_changeover_time(
                    tasks_sorted[i].product_type,
                    tasks_sorted[i + 1].product_type,
                )

        utilization: dict[str, float] = {}
        for machine_id, tasks in machine_groups.items():
            busy = sum(t.duration for t in tasks)
            utilization[machine_id] = busy / makespan if makespan > 0 else 0.0

        return ScheduleResult(
            assignments=sorted_assignments,
            total_makespan=makespan,
            on_time_delivery_rate=delivery_rate,
            total_changeover_time=total_changeover,
            machine_utilization=utilization,
        )

    async def _run_solver(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        params: OptimizationParams,
    ) -> tuple[ScheduleResult, str]:
        """运行求解器，返回排程结果与分配 ID。"""
        solver = APSSolver(
            orders=orders,
            machines=machines,
            params=params,
        )
        schedule = solver.solve()
        schedule_id = f"adj-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        return schedule, schedule_id

    async def analyze_and_adjust(
        self,
        result: ScheduleResult,
        validation: ValidationResult,
        orders: list[Order],
        machines: list[ProductionLine],
    ) -> Adjustment | None:
        """分析验证结果并增量调整"""
        if validation.is_valid:
            return None

        for violation in validation.constraint_violations:
            if violation.type == "due_date":
                return await self.handle_order_change(
                    order_id=violation.order_id or "",
                    changes={"priority": "high"},
                    orders=orders,
                    machines=machines,
                    existing_result=result,
                )

        return None
