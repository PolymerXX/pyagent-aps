"""ExceptionAgent 单元测试 - 不依赖LLM"""


from aps.agents.exception_handler import ExceptionAnalysis, ExceptionType


class TestExceptionAnalysis:
    def test_defaults(self):
        analysis = ExceptionAnalysis()
        assert analysis.exception_type == ExceptionType.UNKNOWN
        assert analysis.root_cause == ""
        assert analysis.affected_orders == []
        assert analysis.suggestions == []
        assert analysis.severity == 1

    def test_custom(self):
        analysis = ExceptionAnalysis(
            exception_type=ExceptionType.INFEASIBLE,
            root_cause="约束太严格",
            affected_orders=["O001", "O002"],
            suggestions=["放宽约束", "增加产能"],
            severity=3,
        )
        assert analysis.exception_type == ExceptionType.INFEASIBLE
        assert analysis.root_cause == "约束太严格"
        assert len(analysis.affected_orders) == 2
        assert len(analysis.suggestions) == 2
        assert analysis.severity == 3


class TestExceptionType:
    def test_all_types(self):
        assert ExceptionType.INFEASIBLE.value == "infeasible"
        assert ExceptionType.TIMEOUT.value == "timeout"
        assert ExceptionType.NO_MACHINE.value == "no_machine"
        assert ExceptionType.CAPACITY_EXCEEDED.value == "capacity"
        assert ExceptionType.CONSTRAINT_CONFLICT.value == "conflict"
        assert ExceptionType.UNKNOWN.value == "unknown"
