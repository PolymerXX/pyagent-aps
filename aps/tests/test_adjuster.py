"""AdjusterAgent 单元测试 - 不依赖LLM"""


from aps.agents.adjuster import AdjusterAgent, Adjustment, AdjustmentType


class TestAdjustment:
    def test_creation(self):
        adj = Adjustment(
            action_type=AdjustmentType.NEW_ORDER,
            affected_orders=["O001"],
            reason="新订单加入",
            new_schedule_id=None,
        )
        assert adj.action_type == AdjustmentType.NEW_ORDER
        assert adj.affected_orders == ["O001"]
        assert adj.reason == "新订单加入"
        assert adj.new_schedule_id is None
        assert adj.changes == {}

    def test_all_types(self):
        assert AdjustmentType.NEW_ORDER.value == "new_order"
        assert AdjustmentType.MACHINE_DOWN.value == "machine_down"
        assert AdjustmentType.ORDER_CHANGE.value == "order_change"
        assert AdjustmentType.PRIORITY_CHANGE.value == "priority_change"

    def test_with_changes(self):
        adj = Adjustment(
            action_type=AdjustmentType.ORDER_CHANGE,
            affected_orders=["O001", "O002"],
            reason="订单变更",
            new_schedule_id=None,
            changes={"quantity": 2000, "due_date": 48},
        )
        assert len(adj.affected_orders) == 2
        assert adj.changes["quantity"] == 2000

    def test_with_schedule_id(self):
        adj = Adjustment(
            action_type=AdjustmentType.NEW_ORDER,
            affected_orders=["O003"],
            reason="新订单",
            new_schedule_id="sched-001",
        )
        assert adj.new_schedule_id == "sched-001"


class TestAdjusterAgentInit:
    def test_init(self):
        agent = AdjusterAgent()
        assert agent.config is not None
        assert agent.settings is not None
        assert agent.agent is not None
