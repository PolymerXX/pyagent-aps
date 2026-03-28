"""数据模型单元测试"""

import pytest
from pydantic import ValidationError

from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import ObjectiveWeights, OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


class TestProduct:
    """Product模型测试"""

    def test_product_creation(self, sample_product: Product):
        assert sample_product.name == "测试产品A"
        assert sample_product.product_type == ProductType.BEVERAGE
        assert sample_product.unit_profit == 1.5
        assert sample_product.production_rate == 100.0

    def test_product_default_values(self):
        product = Product(
            id="P_D", name="默认产品", product_type=ProductType.BEVERAGE, production_rate=100.0
        )
        assert product.unit_profit == 0.0

    def test_product_with_zero_profit(self):
        product = Product(
            id="P_T",
            name="测试",
            product_type=ProductType.BEVERAGE,
            production_rate=100.0,
            unit_profit=0.0,
        )
        assert product.unit_profit == 0.0


class TestOrder:
    """Order模型测试"""

    def test_order_creation(self, sample_order: Order, sample_product: Product):
        assert sample_order.id == "O001"
        assert sample_order.product == sample_product
        assert sample_order.quantity == 1000
        assert sample_order.due_date == 24

    def test_order_estimated_production_hours(self, sample_order: Order):
        hours = sample_order.estimated_production_hours
        assert hours == 10.0  # 1000 / 100

    def test_order_default_values(self, sample_product: Product):
        order = Order(id="O003", product=sample_product, quantity=500, due_date=72)
        assert order.priority == 1
        assert order.min_start_time == 0

    def test_order_invalid_quantity(self, sample_product: Product):
        with pytest.raises(ValidationError):
            Order(id="O003", product=sample_product, quantity=0, due_date=24)


class TestProductType:
    """ProductType枚举测试"""

    def test_product_type_values(self):
        assert ProductType.BEVERAGE.value == "beverage"
        assert ProductType.DAIRY.value == "dairy"
        assert ProductType.JUICE.value == "juice"

    def test_product_type_from_string(self):
        pt = ProductType("beverage")
        assert pt == ProductType.BEVERAGE


class TestProductionLine:
    """ProductionLine模型测试"""

    def test_machine_creation(self, sample_machine: ProductionLine):
        assert sample_machine.id == "M001"
        assert sample_machine.name == "测试产线1"
        assert sample_machine.capacity_per_hour == 100.0
        assert sample_machine.setup_time_hours == 0.5

    def test_machine_can_produce(self, sample_machine: ProductionLine):
        assert sample_machine.can_produce(ProductType.BEVERAGE) is True
        assert sample_machine.can_produce(ProductType.DAIRY) is True
        assert sample_machine.can_produce(ProductType.JUICE) is False

    def test_machine_default_values(self):
        machine = ProductionLine(
            id="M003",
            status=MachineStatus(machine_id="M003", status="active"),
        )
        assert machine.name == ""
        assert machine.capacity_per_hour == 1000.0
        assert machine.setup_time_hours == 0.0


class TestMachineStatus:
    """MachineStatus模型测试"""

    def test_status_creation(self):
        status = MachineStatus(machine_id="M001", status="active")
        assert status.machine_id == "M001"
        assert status.status == "active"
        assert status.current_task is None
        assert status.completed_tasks == 0


class TestTaskAssignment:
    """TaskAssignment模型测试"""

    def test_assignment_creation(self, sample_task_assignment: TaskAssignment):
        assert sample_task_assignment.order_id == "O001"
        assert sample_task_assignment.machine_id == "M001"
        assert sample_task_assignment.start_time == 0.0
        assert sample_task_assignment.end_time == 10.0

    def test_assignment_duration(self, sample_task_assignment: TaskAssignment):
        assert sample_task_assignment.duration == 10.0

    def test_assignment_defaults(self):
        assignment = TaskAssignment(
            order_id="O001",
            machine_id="M001",
            product_name="产品",
            product_type="beverage",
            start_time=0.0,
            end_time=5.0,
            quantity=100,
        )
        assert assignment.status == TaskStatus.PLANNED
        assert assignment.is_on_time is True
        assert assignment.delay_hours == 0.0


class TestScheduleResult:
    """ScheduleResult模型测试"""

    def test_result_creation(self, sample_result: ScheduleResult):
        assert sample_result.task_count == 1
        assert sample_result.total_makespan == 10.0
        assert sample_result.on_time_delivery_rate == 1.0

    def test_result_task_count(self, sample_task_assignment: TaskAssignment):
        result = ScheduleResult(assignments=[sample_task_assignment, sample_task_assignment])
        assert result.task_count == 2

    def test_result_on_time_count(self, sample_task_assignment: TaskAssignment):
        result = ScheduleResult(assignments=[sample_task_assignment])
        assert result.on_time_count == 1

    def test_result_delayed_count(self, sample_task_assignment: TaskAssignment):
        delayed = TaskAssignment(
            order_id="O002",
            machine_id="M001",
            product_name="产品",
            product_type="beverage",
            start_time=0.0,
            end_time=30.0,
            quantity=100,
            is_on_time=False,
            delay_hours=6.0,
        )
        result = ScheduleResult(assignments=[sample_task_assignment, delayed])
        assert result.delayed_count == 1

    def test_result_get_assignments_by_machine(self, sample_result: ScheduleResult):
        assignments = sample_result.get_assignments_by_machine("M001")
        assert len(assignments) == 1

    def test_result_get_sorted_assignments(self, sample_task_assignment: TaskAssignment):
        earlier = TaskAssignment(
            order_id="O002",
            machine_id="M001",
            product_name="产品",
            product_type="beverage",
            start_time=0.0,
            end_time=5.0,
            quantity=100,
        )
        later = TaskAssignment(
            order_id="O003",
            machine_id="M001",
            product_name="产品",
            product_type="beverage",
            start_time=10.0,
            end_time=20.0,
            quantity=100,
        )
        result = ScheduleResult(assignments=[later, earlier])
        sorted_assignments = result.get_sorted_assignments()
        assert sorted_assignments[0].start_time == 0.0
        assert sorted_assignments[1].start_time == 10.0


class TestOptimizationParams:
    """OptimizationParams模型测试"""

    def test_params_creation(self, sample_params: OptimizationParams):
        assert sample_params.strategy == OptimizationStrategy.BALANCED
        assert sample_params.time_limit_seconds == 60
        assert sample_params.planning_horizon_hours == 168

    def test_params_defaults(self):
        params = OptimizationParams()
        assert params.strategy == OptimizationStrategy.BALANCED
        assert params.time_limit_seconds == 60
        assert params.allow_late_delivery is True

    def test_params_custom_strategy(self):
        params = OptimizationParams(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        assert params.strategy == OptimizationStrategy.ON_TIME_DELIVERY


class TestObjectiveWeights:
    """ObjectiveWeights模型测试"""

    def test_weights_creation(self):
        weights = ObjectiveWeights()
        assert weights.on_time == 0.4
        assert weights.changeover == 0.2
        assert weights.utilization == 0.2
        assert weights.profit == 0.2

    def test_weights_total(self):
        weights = ObjectiveWeights()
        assert weights.total == 1.0

    def test_weights_normalize(self):
        weights = ObjectiveWeights(on_time=0.5, changeover=0.5, utilization=0.0, profit=0.0)
        normalized = weights.normalize()
        assert normalized.on_time == 0.5
        assert normalized.changeover == 0.5

    def test_weights_normalize_zero(self):
        weights = ObjectiveWeights(on_time=0.0, changeover=0.0, utilization=0.0, profit=0.0)
        normalized = weights.normalize()
        assert normalized.on_time == 0.4
        assert normalized.changeover == 0.2


class TestTaskStatus:
    """TaskStatus枚举测试"""

    def test_status_values(self):
        assert TaskStatus.PLANNED.value == "planned"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.DELAYED.value == "delayed"
