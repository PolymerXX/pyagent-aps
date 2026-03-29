"""Orchestrator/APSSystem 单元测试 - 不依赖LLM"""

import pytest

from aps.models.optimization import OptimizationStrategy
from aps.models.schedule import ScheduleExplanation, ScheduleResult, TaskAssignment, TaskStatus
from aps.tests.sample_scenario import get_sample_machines, get_sample_orders


@pytest.fixture
def sample_orders():
    return get_sample_orders()


@pytest.fixture
def sample_machines():
    return get_sample_machines()


@pytest.fixture
def delayed_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0.0,
                end_time=10.0,
                quantity=1000,
                status=TaskStatus.PLANNED,
                is_on_time=True,
                delay_hours=0.0,
            ),
            TaskAssignment(
                order_id="O002",
                machine_id="M001",
                product_name="牛奶",
                product_type="dairy",
                start_time=10.5,
                end_time=18.0,
                quantity=500,
                status=TaskStatus.PLANNED,
                is_on_time=False,
                delay_hours=6.0,
            ),
        ],
        total_makespan=18.0,
        on_time_delivery_rate=0.5,
        total_changeover_time=4.0,
        machine_utilization={"M001": 1.0, "M002": 0.0},
        planning_time_seconds=0.1,
        is_optimal=False,
    )


class TestGenerateSimpleExplanation:
    def test_basic_explanation(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        result = system.quick_schedule()
        explanation = system._generate_simple_explanation(result)
        assert isinstance(explanation, ScheduleExplanation)
        assert "排产完成" in explanation.summary
        assert len(explanation.key_decisions) > 0

    def test_explanation_with_delay(self, sample_orders, sample_machines, delayed_result):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        explanation = system._generate_simple_explanation(delayed_result)
        assert any("延期" in d for d in explanation.key_decisions)

        assert len(explanation.risks) > 0


class TestGenerateRecommendations:
    def test_delayed_orders(self, sample_orders, sample_machines, delayed_result):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        recs = system._generate_recommendations(delayed_result)
        assert any("产能" in r or "交期" in r for r in recs)

    def test_high_utilization(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        high_util_result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=10,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                ),
            ],
            total_makespan=10.0,
            machine_utilization={"M001": 0.95, "M002": 0.95},
        )
        recs = system._generate_recommendations(high_util_result)
        assert any("产能" in r for r in recs)

    def test_low_utilization(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        low_util_result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=1,
                    quantity=100,
                    status=TaskStatus.PLANNED,
                ),
            ],
            total_makespan=10.0,
            machine_utilization={"M001": 0.1, "M002": 0.2},
        )
        recs = system._generate_recommendations(low_util_result)
        assert any("订单" in r for r in recs)

    def test_good_result(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        good_result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=10,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                    is_on_time=True,
                ),
            ],
            total_makespan=10.0,
            on_time_delivery_rate=1.0,
            total_changeover_time=0.5,
            machine_utilization={"M001": 0.7, "M002": 0.6},
        )
        recs = system._generate_recommendations(good_result)
        assert any("合理" in r for r in recs)


class TestInferParamsFromInput:
    def test_on_time_keyword(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("请确保交期准时")
        assert params.strategy == OptimizationStrategy.ON_TIME_DELIVERY

    def test_changeover_keyword(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("减少换产时间")
        assert params.strategy == OptimizationStrategy.MINIMIZE_CHANGEOVER

    def test_profit_keyword(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("最大化利润收益")
        assert params.strategy == OptimizationStrategy.MAXIMIZE_PROFIT

    def test_balanced_default(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("正常排程")
        assert params.strategy == OptimizationStrategy.BALANCED

    def test_not_delay_keyword(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("确保不延误")
        assert params.strategy == OptimizationStrategy.ON_TIME_DELIVERY

    def test_deadline_keyword(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        params = system._infer_params_from_input("关注截止时间")
        assert params.strategy == OptimizationStrategy.ON_TIME_DELIVERY


class TestFormatHelpers:
    def test_format_orders(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        formatted = system._format_orders()
        assert "O001" in formatted
        assert "可乐" in formatted
        assert "1000" in formatted

    def test_format_orders_multiple(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        formatted = system._format_orders()
        lines = formatted.split("\n")
        assert len(lines) == len(sample_orders)

    def test_format_machines(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        formatted = system._format_machines()
        assert "M001" in formatted
        assert "产线A" in formatted
        assert "beverage" in formatted

    def test_format_empty_orders(self, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=[], machines=sample_machines)
        formatted = system._format_orders()
        assert formatted == ""

    def test_format_empty_machines(self, sample_orders):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=[])
        formatted = system._format_machines()
        assert formatted == ""


class TestQuickSchedule:
    def test_basic_schedule(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        result = system.quick_schedule()
        assert isinstance(result, ScheduleResult)
        assert result.task_count > 0

    def test_schedule_with_strategy(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        result = system.quick_schedule(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        assert isinstance(result, ScheduleResult)

    def test_schedule_balanced(self, sample_orders, sample_machines):
        from aps.agents.orchestrator import APSSystem

        system = APSSystem(orders=sample_orders, machines=sample_machines)
        result = system.quick_schedule(strategy=OptimizationStrategy.BALANCED)
        assert result.task_count == len(sample_orders)
