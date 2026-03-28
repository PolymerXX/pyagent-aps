"""SchedulerAgent 单元测试 - 不依赖LLM"""

import pytest

from aps.agents.scheduler import SchedulerAgent
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType


@pytest.fixture
def sample_orders():
    return [
        Order(
            id="O001",
            product=Product(
                id="P001", name="可乐", product_type=ProductType.BEVERAGE, production_rate=100
            ),
            quantity=1000,
            due_date=24,
        ),
        Order(
            id="O002",
            product=Product(
                id="P002", name="牛奶", product_type=ProductType.DAIRY, production_rate=80
            ),
            quantity=500,
            due_date=12,
        ),
    ]


@pytest.fixture
def sample_machines():
    return [
        ProductionLine(
            id="M001",
            name="产线A",
            supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY],
            capacity_per_hour=100,
            setup_time_hours=0.5,
            status=MachineStatus(machine_id="M001", status="running"),
        ),
    ]


@pytest.fixture
def scheduler(sample_orders, sample_machines):
    return SchedulerAgent(orders=sample_orders, machines=sample_machines)


class TestSchedulerAgentInit:
    def test_init(self, scheduler, sample_orders, sample_machines):
        assert scheduler.orders == sample_orders
        assert scheduler.machines == sample_machines

    def test_init_default_constraints(self, sample_orders, sample_machines):
        scheduler = SchedulerAgent(orders=sample_orders, machines=sample_machines)
        assert scheduler.constraints is not None


class TestRunOptimization:
    def test_basic(self, scheduler):
        result = scheduler.run_optimization()
        assert result.task_count == 2
        assert result.total_makespan > 0

    def test_with_params(self, scheduler):
        params = OptimizationParams(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        result = scheduler.run_optimization(params)
        assert result.task_count == 2

    def test_default_params(self, scheduler):
        result = scheduler.run_optimization(None)
        assert result.task_count == 2


class TestQuickSchedule:
    def test_balanced(self, scheduler):
        result = scheduler.quick_schedule()
        assert result.task_count == 2

    def test_on_time(self, scheduler):
        result = scheduler.quick_schedule(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        assert result.task_count == 2


class TestOrderManagement:
    def test_add_order(self, scheduler):
        new_order = Order(
            id="O003",
            product=Product(
                id="P003", name="橙汁", product_type=ProductType.JUICE, production_rate=120
            ),
            quantity=800,
            due_date=36,
        )
        scheduler.add_order(new_order)
        assert len(scheduler.orders) == 3
        assert scheduler.orders[-1].id == "O003"

    def test_remove_order(self, scheduler):
        removed = scheduler.remove_order("O001")
        assert removed is True
        assert len(scheduler.orders) == 1
        assert scheduler.orders[0].id == "O002"

    def test_remove_nonexistent(self, scheduler):
        removed = scheduler.remove_order("O999")
        assert removed is False
        assert len(scheduler.orders) == 2

    def test_get_order(self, scheduler):
        order = scheduler.get_order("O001")
        assert order is not None
        assert order.id == "O001"

    def test_get_nonexistent(self, scheduler):
        order = scheduler.get_order("O999")
        assert order is None
