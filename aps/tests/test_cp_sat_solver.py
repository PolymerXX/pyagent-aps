"""CP-SAT求解器单元测试"""

import pytest

from aps.engine import HAS_ORTOOLS, APSSolver, CPSATSolver
from aps.models.constraint import ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType


@pytest.fixture
def sample_product() -> Product:
    return Product(
        id="P_A",
        name="产品A",
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
        name="产线1",
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
                id="P_B", name="产品B", product_type=ProductType.BEVERAGE, production_rate=100.0
            ),
            quantity=500,
            due_date=12,
        ),
        Order(
            id="O003",
            product=Product(
                id="P_C", name="产品C", product_type=ProductType.BEVERAGE, production_rate=100.0
            ),
            quantity=800,
            due_date=36,
        ),
    ]


@pytest.fixture
def sample_machines(sample_machine) -> list[ProductionLine]:
    machine2 = ProductionLine(
        id="M002",
        name="产线2",
        supported_product_types=[ProductType.BEVERAGE],
        capacity_per_hour=150.0,
        setup_time_hours=0.3,
        status=MachineStatus(machine_id="M002", status="active"),
    )
    return [sample_machine, machine2]


@pytest.mark.skipif(not HAS_ORTOOLS, reason="OR-Tools not installed")
class TestCPSATSolver:
    """CPSATSolver测试类"""

    def test_solver_basic(self, sample_order, sample_machine):
        solver = CPSATSolver(
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
        solver = CPSATSolver(
            orders=[],
            machines=[sample_machine],
        )
        result = solver.solve()

        assert result.task_count == 0
        assert result.total_makespan == 0.0

    def test_solver_empty_machines(self, sample_order):
        solver = CPSATSolver(
            orders=[sample_order],
            machines=[],
        )
        result = solver.solve()

        assert result.task_count == 0

    def test_solver_multiple_orders_machines(self, sample_orders, sample_machines):
        solver = CPSATSolver(
            orders=sample_orders,
            machines=sample_machines,
        )
        result = solver.solve()

        assert result.task_count == 3
        assert len(result.assignments) == 3

    def test_solver_makespan_strategy(self, sample_orders, sample_machines):
        params = OptimizationParams(strategy=OptimizationStrategy.BALANCED)
        solver = CPSATSolver(
            orders=sample_orders,
            machines=sample_machines,
            params=params,
        )
        result = solver.solve()

        assert result.total_makespan > 0
        assert result.is_optimal is not None

    def test_solver_on_time_strategy(self, sample_orders, sample_machines):
        params = OptimizationParams(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        solver = CPSATSolver(
            orders=sample_orders,
            machines=sample_machines,
            params=params,
        )
        result = solver.solve()

        assert result.on_time_delivery_rate is not None
        assert 0.0 <= result.on_time_delivery_rate <= 1.0

    def test_solver_time_limit(self, sample_orders, sample_machines):
        params = OptimizationParams(time_limit_seconds=5)
        solver = CPSATSolver(
            orders=sample_orders,
            machines=sample_machines,
            params=params,
        )
        result = solver.solve()

        assert result.planning_time_seconds < 10

    def test_solver_machine_utilization(self, sample_orders, sample_machines):
        solver = CPSATSolver(
            orders=sample_orders,
            machines=sample_machines,
        )
        result = solver.solve()

        assert len(result.machine_utilization) == 2
        for util in result.machine_utilization.values():
            assert 0.0 <= util <= 1.0


@pytest.mark.skipif(not HAS_ORTOOLS, reason="OR-Tools not installed")
class TestAPSSolverCPSATIntegration:
    """APSSolver CP-SAT集成测试"""

    def test_auto_uses_cp_sat(self, sample_orders, sample_machines):
        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            use_cp_sat=True,
        )
        assert solver.use_cp_sat is True

        result = solver.solve()
        assert result.task_count == 3

    def test_can_disable_cp_sat(self, sample_orders, sample_machines):
        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            use_cp_sat=False,
        )
        assert solver.use_cp_sat is False

        result = solver.solve()
        assert result.is_optimal is False
        assert result.task_count == 3

    def test_cp_sat_vs_heuristic_quality(self, sample_orders, sample_machines):
        solver_cp_sat = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            use_cp_sat=True,
        )
        result_cp_sat = solver_cp_sat.solve()

        solver_heuristic = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            use_cp_sat=False,
        )
        result_heuristic = solver_heuristic.solve()

        assert result_cp_sat.task_count == result_heuristic.task_count

        assert result_cp_sat.is_optimal or result_heuristic.is_optimal is False


class TestCPSATSolverFallback:
    """CP-SAT回退测试（不依赖OR-Tools）"""

    def test_fallback_when_disabled(self, sample_orders, sample_machines):
        solver = APSSolver(
            orders=sample_orders,
            machines=sample_machines,
            use_cp_sat=False,
        )
        result = solver.solve()

        assert result.is_optimal is False
        assert result.task_count == 3

    def test_fallback_empty_data(self):
        solver = APSSolver(
            orders=[],
            machines=[],
            use_cp_sat=False,
        )
        result = solver.solve()

        assert result.task_count == 0
        assert result.total_makespan == 0.0
