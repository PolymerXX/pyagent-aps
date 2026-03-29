"""Agent单元测试"""

from aps.models.optimization import OptimizationStrategy


class TestAgentContext:
    """AgentContext测试"""

    def test_context_creation(self):
        from aps.agents.base import AgentContext

        context = AgentContext(user_input="测试输入")
        assert context.user_input == "测试输入"
        assert context.orders_info == ""
        assert context.machines_info == ""

    def test_context_with_data(self):
        from aps.agents.base import AgentContext

        context = AgentContext(
            user_input="排产",
            orders_info="订单1: 产品A, 1000件",
            machines_info="机器1: 产线A",
        )
        assert context.orders_info == "订单1: 产品A, 1000件"
        assert context.machines_info == "机器1: 产线A"


class TestPlannerOutput:
    """PlannerOutput测试"""

    def test_planner_output_defaults(self):
        from aps.agents.planner import PlannerOutput

        output = PlannerOutput()
        assert output.strategy == OptimizationStrategy.BALANCED
        assert output.time_limit_seconds == 60
        assert output.on_time == 0.4
        assert output.weights.on_time == 0.4

    def test_planner_output_custom_strategy(self):
        from aps.agents.planner import PlannerOutput

        output = PlannerOutput(strategy=OptimizationStrategy.ON_TIME_DELIVERY)
        assert output.strategy == OptimizationStrategy.ON_TIME_DELIVERY

    def test_planner_output_flat_weights(self):
        from aps.agents.planner import PlannerOutput

        out = PlannerOutput(
            on_time=0.7,
            changeover=0.1,
            utilization=0.1,
            profit=0.1,
        )
        assert out.weights.on_time == 0.7
        assert out.weights.changeover == 0.1

    def test_planner_output_weights_json_string_from_llm(self):
        """模型若把 weights 打成 JSON 字符串，应展平为顶层字段（避免 tool 校验失败）。"""
        from aps.agents.planner import PlannerOutput

        blob = '{"on_time": 0.6, "changeover": 0.15, "utilization": 0.15, "profit": 0.1}'
        out = PlannerOutput.model_validate(
            {"strategy": "balanced", "weights": blob, "explanation": "x"}
        )
        assert out.on_time == 0.6
        assert out.changeover == 0.15
        assert out.utilization == 0.15
        assert out.profit == 0.1

    def test_planner_output_weights_dict_from_llm(self):
        from aps.agents.planner import PlannerOutput

        out = PlannerOutput.model_validate(
            {
                "weights": {
                    "on_time": 0.5,
                    "changeover": 0.2,
                    "utilization": 0.2,
                    "profit": 0.1,
                }
            }
        )
        assert out.on_time == 0.5
        assert out.profit == 0.1

    def test_planner_output_to_optimization_params(self):
        from aps.agents.planner import PlannerOutput

        output = PlannerOutput(
            strategy=OptimizationStrategy.MINIMIZE_CHANGEOVER,
            time_limit_seconds=120,
        )
        params = output.to_optimization_params()
        assert params.strategy == OptimizationStrategy.MINIMIZE_CHANGEOVER
        assert params.time_limit_seconds == 120


class TestAdjustment:
    """Adjustment测试"""

    def test_adjustment_creation(self):
        from aps.agents.adjuster import Adjustment, AdjustmentType

        adjustment = Adjustment(
            action_type=AdjustmentType.NEW_ORDER,
            affected_orders=["O001"],
            reason="新订单加入",
            new_schedule_id=None,
        )
        assert adjustment.action_type == AdjustmentType.NEW_ORDER
        assert len(adjustment.affected_orders) == 1

    def test_adjustment_type_new_order(self):
        from aps.agents.adjuster import AdjustmentType

        assert AdjustmentType.NEW_ORDER.value == "new_order"

    def test_adjustment_type_machine_down(self):
        from aps.agents.adjuster import AdjustmentType

        assert AdjustmentType.MACHINE_DOWN.value == "machine_down"
