import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from aps.models.order import Order, Product, ProductType
from aps.models.machine import ProductionLine
from aps.models.constraint import ProductionConstraints, DEFAULT_CHANGEOVER_RULES, ChangeoverRule, ChangeoverRule
from aps.models.optimization import OptimizationParams, OptimizationStrategy


@pytest.fixture
def sample_product_cola():
    return Product(
        id="cola",
        name="可乐",
        product_type=ProductType.BEVERAGE,
        production_rate=1000.0,
        unit_profit=0.5
    )


@pytest.fixture
def sample_product_milk():
    return Product(
        id="milk",
        name="牛奶",
        product_type=ProductType.DAIRY,
        production_rate=800.0,
        unit_profit=0.8
    )


@pytest.fixture
def sample_product_juice():
    return Product(
        id="orange_juice",
        name="橙汁",
        product_type=ProductType.JUICE,
        production_rate=600.0,
        unit_profit=0.6
    )


@pytest.fixture
def sample_order_cola(sample_product_cola):
    return Order(
        id="order_001",
        product=sample_product_cola,
        quantity=10000,
        due_date=72,
        priority=5
    )


@pytest.fixture
def sample_order_milk(sample_product_milk):
    return Order(
        id="order_002",
        product=sample_product_milk,
        quantity=5000,
        due_date=48,
        priority=8
    )


@pytest.fixture
def sample_order_juice(sample_product_juice):
    return Order(
        id="order_003",
        product=sample_product_juice,
        quantity=6000,
        due_date=96,
        priority=3
    )


@pytest.fixture
def sample_production_line():
    return ProductionLine(
        id="line_a",
        name="生产线A",
        capacity=1000,
        supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY, ProductType.JUICE]
    )


@pytest.fixture
def sample_constraints():
    return ProductionConstraints(
        max_continuous_hours=24,
        min_break_hours=2,
        changeover_rules=DEFAULT_CHANGEOVER_RULES
    )


@pytest.fixture
def sample_optimization_params():
    return OptimizationParams(
        strategy=OptimizationStrategy.BALANCED,
        time_limit_seconds=60
    )


@pytest.fixture
def sample_orders(sample_order_cola, sample_order_milk, sample_order_juice):
    return [sample_order_cola, sample_order_milk, sample_order_juice]


@pytest.fixture
def sample_machines(sample_production_line):
    return [sample_production_line]
