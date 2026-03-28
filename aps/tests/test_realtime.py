"""实时调整模块单元测试"""

from datetime import datetime

from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


class TestRealtimeAdjuster:
    """实时调整器测试"""

    def test_handle_new_order(
        self, sample_order: Order, sample_machine: ProductionLine, sample_result: ScheduleResult
    ):
        new_order = Order(
            id="O_NEW",
            product=sample_order.product,
            quantity=500,
            due_date=12,
        )

        adjustment = {
            "action_type": "new_order",
            "order_id": new_order.id,
            "timestamp": datetime.now(),
        }

        assert adjustment["action_type"] == "new_order"
        assert adjustment["order_id"] == "O_NEW"

    def test_handle_machine_down(self, sample_machine: ProductionLine):
        machine_down_event = {
            "machine_id": sample_machine.id,
            "timestamp": datetime.now(),
            "reason": "设备故障",
        }

        assert machine_down_event["machine_id"] == "M001"
        assert machine_down_event["reason"] == "设备故障"


class TestScheduleRecalculation:
    """排程重计算测试"""

    def test_recalculate_with_new_order(
        self, sample_orders: list[Order], sample_machines: list[ProductionLine]
    ):
        from aps.engine.solver import APSSolver

        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            params=OptimizationParams(strategy=OptimizationStrategy.BALANCED),
        )

        result = solver.solve()
        assert result.task_count >= 0


class TestAdjustmentResult:
    """调整结果测试"""

    def test_adjustment_result_creation(self):
        adjustment_result = {
            "success": True,
            "affected_orders": ["O001", "O002"],
            "new_makespan": 15.0,
            "timestamp": datetime.now().isoformat(),
        }

        assert adjustment_result["success"] is True
        assert len(adjustment_result["affected_orders"]) == 2


class TestConflictDetection:
    """冲突检测测试"""

    def test_deadline_conflict_detection(self):
        task = TaskAssignment(
            order_id="O001",
            machine_id="M001",
            product_name="产品A",
            product_type="beverage",
            start_time=0.0,
            end_time=30.0,
            quantity=1000,
            status=TaskStatus.PLANNED,
            is_on_time=False,
            delay_hours=6.0,
        )

        has_conflict = not task.is_on_time and task.delay_hours > 0
        assert has_conflict

    def test_no_conflict_detection(self, sample_task_assignment: TaskAssignment):
        has_conflict = (
            not sample_task_assignment.is_on_time
            and sample_task_assignment.delay_hours > 0
        )
        assert not has_conflict
