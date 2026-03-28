"""求解器单元测试"""

import pytest

from aps.engine.solver import APSSolver
from aps.models.constraint import ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType


@pytest.fixture
def sample_product() -> Product:
    return Product(
        id="P001",
        name="测试产品A",
        product_type=ProductType.BEVERAGE,
        unit_profit=1.5,
        production_rate=100.0,
    )


@pytest.fixture
def sample_order(sample_product) -> Order:
    return Order(
        id="O001",
        product=sample_product,
        quantity=1000,
        due_date=24,
    )


@pytest.fixture
def sample_machine() -> ProductionLine:
    return ProductionLine(
        id="M001",
        name="测试产线1",
        supported_product_types=[ProductType.BEVERAGE],
        capacity_per_hour=100.0,
        setup_time_hours=0.5,
        status=MachineStatus(machine_id="M001", status="active"),
    )


@pytest.fixture
def sample_orders(sample_product) -> list[Order]:
    return [
        Order(
            id="O001",
            product=sample_product,
            quantity=1000,
            due_date=24,
        ),
        Order(
            id="O002",
            product=Product(
                id="P002", name="产品B", product_type=ProductType.BEVERAGE, production_rate=100.0
            ),
            quantity=500,
            due_date=12,
        ),
    ]


@pytest.fixture
def sample_machines(sample_machine) -> list[ProductionLine]:
    return [sample_machine]


class TestAPSSolver:
    """APSSolver测试类"""

    def test_solver_basic(self, sample_order, sample_machine):
        solver = APSSolver(
            orders=[sample_order],
            machines=[sample_machine],
            constraints=ProductionConstraints(),
            params=OptimizationParams(strategy=OptimizationStrategy.BALANCED),
        )
        result = solver.solve()

        assert result.task_count == 1
        assert result.total_makespan > 0
        assert len(result.assignments) == 1

    def test_solver_empty_orders(self, sample_machine):
        solver = APSSolver(
            orders=[],
            machines=[sample_machine],
        )
        result = solver.solve()

        assert result.task_count == 0
        assert result.total_makespan == 0.0

    def test_solver_empty_machines(self, sample_order):
        solver = APSSolver(
            orders=[sample_order],
            machines=[],
        )
        result = solver.solve()

        assert result.task_count == 0

    def test_solver_multiple_orders(self, sample_orders, sample_machines):
        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
        )
        result = solver.solve()

        assert result.task_count == 2
        assert len(result.assignments) == 2

    def test_solver_on_time_delivery(self, sample_order, sample_machine):
        solver = APSSolver(
            orders=[sample_order],
            machines=[sample_machine],
        )
        result = solver.solve()

        assignment = result.assignments[0]
        assert assignment.is_on_time or assignment.delay_hours >= 0

    def test_solver_machine_utilization(self, sample_orders, sample_machines):
        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
        )
        result = solver.solve()

        assert "M001" in result.machine_utilization
        assert 0.0 <= result.machine_utilization["M001"] <= 1.0


class TestOptimizationParams:
    """OptimizationParams测试类"""

    def test_default_params(self):
        params = OptimizationParams()
        assert params.strategy == OptimizationStrategy.BALANCED
        assert params.time_limit_seconds == 60

    def test_custom_strategy(self):
        params = OptimizationParams(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        assert params.strategy == OptimizationStrategy.ON_TIME_DELIVERY


class TestModels:
    """数据模型测试类"""

    def test_order_estimated_hours(self, sample_order):
        estimated = sample_order.estimated_production_hours
        assert estimated == sample_order.quantity / sample_order.product.production_rate

    def test_machine_can_produce(self, sample_machine):
        assert sample_machine.can_produce(ProductType.BEVERAGE) is True
        assert sample_machine.can_produce(ProductType.JUICE) is False

    def test_task_assignment_duration(self, sample_order, sample_machine):
        from aps.models.schedule import TaskAssignment, TaskStatus

        assignment = TaskAssignment(
            order_id=sample_order.id,
            machine_id=sample_machine.id,
            product_name=sample_order.product.name,
            product_type=sample_order.product.product_type.value,
            start_time=0.0,
            end_time=10.0,
            quantity=sample_order.quantity,
            status=TaskStatus.PLANNED,
        )

        assert assignment.duration == 10.0
