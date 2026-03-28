"""Pytest共享fixtures配置"""

import os

import pytest

from aps.models.constraint import ChangeoverRule, ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus

os.environ.setdefault("OPENROUTER_API_KEY", "test-key-for-ci")

for _proxy_var in (
    "all_proxy",
    "ALL_PROXY",
    "http_proxy",
    "HTTP_PROXY",
    "https_proxy",
    "HTTPS_PROXY",
):
    os.environ.pop(_proxy_var, None)


@pytest.fixture(autouse=True)
def _clear_proxy_env(monkeypatch):
    for var in ("all_proxy", "ALL_PROXY", "http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
        monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def _disable_logfire_for_tests(monkeypatch):
    monkeypatch.setenv("APS_LOGFIRE_ENABLED", "false")


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
def sample_product_b() -> Product:
    return Product(
        id="P002",
        name="测试产品B",
        product_type=ProductType.DAIRY,
        unit_profit=2.0,
        production_rate=80.0,
    )


@pytest.fixture
def sample_order(sample_product: Product) -> Order:
    return Order(
        id="O001",
        product=sample_product,
        quantity=1000,
        due_date=24,
        min_start_time=0,
    )


@pytest.fixture
def sample_order_b(sample_product_b: Product) -> Order:
    return Order(
        id="O002",
        product=sample_product_b,
        quantity=500,
        due_date=12,
        min_start_time=0,
    )


@pytest.fixture
def sample_orders(sample_product: Product, sample_product_b: Product) -> list[Order]:
    return [
        Order(
            id="O001",
            product=sample_product,
            quantity=1000,
            due_date=24,
        ),
        Order(
            id="O002",
            product=sample_product_b,
            quantity=500,
            due_date=12,
        ),
        Order(
            id="O003",
            product=sample_product,
            quantity=800,
            due_date=36,
        ),
    ]


@pytest.fixture
def sample_machine() -> ProductionLine:
    return ProductionLine(
        id="M001",
        name="测试产线1",
        supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY],
        capacity_per_hour=100.0,
        setup_time_hours=0.5,
        status=MachineStatus(machine_id="M001", status="active"),
    )


@pytest.fixture
def sample_machine_b() -> ProductionLine:
    return ProductionLine(
        id="M002",
        name="测试产线2",
        supported_product_types=[ProductType.BEVERAGE],
        capacity_per_hour=150.0,
        setup_time_hours=0.3,
        status=MachineStatus(machine_id="M002", status="active"),
    )


@pytest.fixture
def sample_machines(
    sample_machine: ProductionLine, sample_machine_b: ProductionLine
) -> list[ProductionLine]:
    return [sample_machine, sample_machine_b]


@pytest.fixture
def sample_constraints() -> ProductionConstraints:
    return ProductionConstraints(
        max_daily_hours=24.0,
        allow_overtime=True,
        max_overtime_hours=4.0,
    )


@pytest.fixture
def sample_params() -> OptimizationParams:
    return OptimizationParams(
        strategy=OptimizationStrategy.BALANCED,
        time_limit_seconds=60,
        planning_horizon_hours=168,
    )


@pytest.fixture
def sample_task_assignment() -> TaskAssignment:
    return TaskAssignment(
        order_id="O001",
        machine_id="M001",
        product_name="测试产品A",
        product_type="beverage",
        start_time=0.0,
        end_time=10.0,
        quantity=1000,
        status=TaskStatus.PLANNED,
        is_on_time=True,
        delay_hours=0.0,
    )


@pytest.fixture
def sample_result(sample_task_assignment: TaskAssignment) -> ScheduleResult:
    return ScheduleResult(
        assignments=[sample_task_assignment],
        total_makespan=10.0,
        on_time_delivery_rate=1.0,
        total_changeover_time=0.0,
        machine_utilization={"M001": 1.0},
        planning_time_seconds=0.1,
        is_optimal=False,
    )


@pytest.fixture
def sample_changeover_rule() -> ChangeoverRule:
    return ChangeoverRule(
        from_type="beverage",
        to_type="dairy",
        setup_hours=1.5,
        priority=5,
        enabled=True,
    )
