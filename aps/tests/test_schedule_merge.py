"""ui.schedule_merge：Agent 响应合并为 ScheduleResult（无 LLM）"""

from __future__ import annotations

from aps.models.optimization import OptimizationStrategy
from aps.models.schedule import TaskAssignment, TaskStatus
from ui.schedule_merge import schedule_result_from_agent_response


def test_schedule_result_from_agent_response_merges_explanation() -> None:
    schedule_dict = {
        "assignments": [
            {
                "order_id": "O001",
                "machine_id": "M001",
                "product_name": "产品A",
                "product_type": "beverage",
                "start_time": 0.0,
                "end_time": 5.0,
                "quantity": 100,
                "status": "planned",
                "is_on_time": True,
                "delay_hours": 0.0,
            }
        ],
        "total_makespan": 5.0,
        "on_time_delivery_rate": 1.0,
        "total_changeover_time": 0.0,
        "machine_utilization": {"M001": 0.5},
        "planning_time_seconds": 0.2,
        "is_optimal": True,
        "explanation": None,
    }
    explanation_dict = {
        "summary": "测试摘要",
        "key_decisions": ["先排 O001"],
        "risks": ["无"],
        "alternatives": ["维持现状"],
    }
    response = {
        "schedule": schedule_dict,
        "explanation": explanation_dict,
        "intent": "测试",
        "optimization_params": {"strategy": OptimizationStrategy.BALANCED.value},
        "validation": {"is_valid": True},
        "monitor_report": {"overall_status": "normal"},
    }

    result = schedule_result_from_agent_response(response)

    assert result.total_makespan == 5.0
    assert len(result.assignments) == 1
    assert isinstance(result.assignments[0], TaskAssignment)
    assert result.assignments[0].order_id == "O001"
    assert result.explanation is not None
    assert result.explanation.summary == "测试摘要"
    assert result.explanation.key_decisions == ["先排 O001"]


def test_schedule_result_from_agent_response_without_explanation_key() -> None:
    assignment = TaskAssignment(
        order_id="O001",
        machine_id="M001",
        product_name="产品A",
        product_type="beverage",
        start_time=0.0,
        end_time=1.0,
        quantity=10,
        status=TaskStatus.PLANNED,
    )
    schedule_dict = {
        "assignments": [assignment.model_dump()],
        "total_makespan": 1.0,
        "on_time_delivery_rate": 1.0,
        "total_changeover_time": 0.0,
        "machine_utilization": {},
        "planning_time_seconds": 0.1,
        "is_optimal": False,
    }
    response = {"schedule": schedule_dict}

    result = schedule_result_from_agent_response(response)

    assert result.explanation is None
