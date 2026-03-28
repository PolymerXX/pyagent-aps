"""MCP工具单元测试"""

from aps.models.constraint import ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType


class TestMCPTools:
    """MCP工具测试"""

    def test_create_order_tool(self, sample_product: Product):
        order = Order(
            id="O001",
            product=sample_product,
            quantity=1000,
            due_date=24,
        )

        assert order.id == "O001"
        assert order.quantity == 1000

    def test_create_machine_tool(self):
        machine = ProductionLine(
            id="M001",
            name="产线1",
            supported_product_types=[ProductType.BEVERAGE],
            capacity_per_hour=100.0,
            status=MachineStatus(machine_id="M001", status="active"),
        )

        assert machine.id == "M001"
        assert machine.can_produce(ProductType.BEVERAGE)

    def test_create_constraints_tool(self):
        constraints = ProductionConstraints(
            max_daily_hours=24.0,
            allow_overtime=True,
        )

        assert constraints.max_daily_hours == 24.0

    def test_create_optimization_params_tool(self):
        params = OptimizationParams(
            strategy=OptimizationStrategy.BALANCED,
            time_limit_seconds=60,
        )

        assert params.strategy == OptimizationStrategy.BALANCED


class TestScheduleTools:
    """排程工具测试"""

    def test_get_schedule_summary(self, sample_result):
        summary = {
            "task_count": sample_result.task_count,
            "makespan": sample_result.total_makespan,
            "on_time_rate": sample_result.on_time_delivery_rate,
        }

        assert summary["task_count"] == 1
        assert summary["makespan"] == 10.0


class TestDataValidation:
    """数据验证工具测试"""

    def test_validate_order(self, sample_order: Order):
        is_valid = (
            sample_order.id is not None
            and sample_order.quantity > 0
            and sample_order.due_date >= 0
        )
        assert is_valid

    def test_validate_machine(self, sample_machine: ProductionLine):
        is_valid = (
            sample_machine.id is not None
            and sample_machine.capacity_per_hour > 0
        )
        assert is_valid

    def test_validate_constraints(self, sample_constraints: ProductionConstraints):
        is_valid = (
            sample_constraints.max_daily_hours > 0
            and sample_constraints.max_consecutive_hours > 0
        )
        assert is_valid


class TestToolOutput:
    """工具输出测试"""

    def test_order_to_dict(self, sample_order: Order):
        order_dict = sample_order.model_dump()
        assert "id" in order_dict
        assert "quantity" in order_dict

    def test_machine_to_dict(self, sample_machine: ProductionLine):
        machine_dict = sample_machine.model_dump()
        assert "id" in machine_dict
        assert "capacity_per_hour" in machine_dict

    def test_result_to_dict(self, sample_result):
        result_dict = sample_result.model_dump()
        assert "assignments" in result_dict
        assert "total_makespan" in result_dict
