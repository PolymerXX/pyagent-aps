import pytest
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import TaskAssignment, ScheduleResult, TaskStatus
from aps.models.optimization import OptimizationParams, OptimizationStrategy, ObjectiveWeights


class TestProduct:
    def test_product_creation(self, sample_product_cola):
        assert sample_product_cola.id == "cola"
        assert sample_product_cola.name == "可乐"
        assert sample_product_cola.product_type == ProductType.BEVERAGE
        assert sample_product_cola.production_rate == 1000.0

    def test_product_type_enum(self):
        assert ProductType.BEVERAGE.value == "beverage"
        assert ProductType.DAIRY.value == "dairy"
        assert ProductType.JUICE.value == "juice"


class TestOrder:
    def test_order_creation(self, sample_order_cola):
        assert sample_order_cola.id == "order_001"
        assert sample_order_cola.quantity == 10000
        assert sample_order_cola.due_date == 72
        assert sample_order_cola.priority == 5

    def test_estimated_production_hours(self, sample_order_cola):
        expected = 10000 / 1000.0
        assert sample_order_cola.estimated_production_hours == expected

    def test_order_default_values(self, sample_product_cola):
        order = Order(
            id="test_order",
            product=sample_product_cola,
            quantity=1000,
            due_date=24
        )
        assert order.priority == 1
        assert order.min_start_time == 0

    def test_order_quantity_validation(self, sample_product_cola):
        with pytest.raises(Exception):
            Order(id="test", product=sample_product_cola, quantity=0, due_date=24)


class TestTaskAssignment:
    def test_task_assignment_creation(self):
        task = TaskAssignment(
            order_id="order_001",
            machine_id="line_a",
            product_name="可乐",
            product_type="beverage",
            start_time=0.0,
            end_time=10.0,
            quantity=10000
        )
        assert task.status == TaskStatus.PLANNED
        assert task.is_on_time is True
        assert task.duration == 10.0

    def test_task_duration(self):
        task = TaskAssignment(
            order_id="test",
            machine_id="line_a",
            product_name="Test",
            product_type="beverage",
            start_time=5.0,
            end_time=15.0,
            quantity=100
        )
        assert task.duration == 10.0


class TestScheduleResult:
    def test_empty_schedule(self):
        result = ScheduleResult()
        assert result.task_count == 0
        assert result.on_time_count == 0
        assert result.delayed_count == 0

    def test_schedule_with_tasks(self):
        tasks = [
            TaskAssignment(
                order_id="order_001",
                machine_id="line_a",
                product_name="可乐",
                product_type="beverage",
                start_time=0.0,
                end_time=10.0,
                quantity=10000,
                is_on_time=True
            ),
            TaskAssignment(
                order_id="order_002",
                machine_id="line_b",
                product_name="牛奶",
                product_type="dairy",
                start_time=0.0,
                end_time=8.0,
                quantity=5000,
                is_on_time=False
            )
        ]
        result = ScheduleResult(assignments=tasks)
        assert result.task_count == 2
        assert result.on_time_count == 1
        assert result.delayed_count == 1

    def test_get_assignments_by_machine(self):
        tasks = [
            TaskAssignment(
                order_id="order_001",
                machine_id="line_a",
                product_name="可乐",
                product_type="beverage",
                start_time=0.0,
                end_time=10.0,
                quantity=10000
            ),
            TaskAssignment(
                order_id="order_002",
                machine_id="line_b",
                product_name="牛奶",
                product_type="dairy",
                start_time=0.0,
                end_time=8.0,
                quantity=5000
            )
        ]
        result = ScheduleResult(assignments=tasks)
        line_a_tasks = result.get_assignments_by_machine("line_a")
        assert len(line_a_tasks) == 1
        assert line_a_tasks[0].order_id == "order_001"

    def test_sorted_assignments(self):
        tasks = [
            TaskAssignment(
                order_id="order_002",
                machine_id="line_a",
                product_name="牛奶",
                product_type="dairy",
                start_time=10.0,
                end_time=18.0,
                quantity=5000
            ),
            TaskAssignment(
                order_id="order_001",
                machine_id="line_a",
                product_name="可乐",
                product_type="beverage",
                start_time=0.0,
                end_time=10.0,
                quantity=10000
            )
        ]
        result = ScheduleResult(assignments=tasks)
        sorted_tasks = result.get_sorted_assignments()
        assert sorted_tasks[0].start_time == 0.0
        assert sorted_tasks[1].start_time == 10.0


class TestOptimizationParams:
    def test_default_params(self):
        params = OptimizationParams()
        assert params.strategy == OptimizationStrategy.BALANCED
        assert params.time_limit_seconds == 60

    def test_custom_params(self):
        weights = ObjectiveWeights(on_time=0.5, utilization=0.3, profit=0.2)
        params = OptimizationParams(
            strategy=OptimizationStrategy.MAX_PROFIT,
            time_limit_seconds=120,
            weights=weights
        )
        assert params.strategy == OptimizationStrategy.MAX_PROFIT
        assert params.time_limit_seconds == 120
        assert params.weights.on_time == 0.5
