"""将 APSSystem.process_request 响应合并为带 explanation 的 ScheduleResult。

无 Streamlit 依赖，便于单测。
"""

from __future__ import annotations

from typing import Any

from aps.models.schedule import ScheduleExplanation, ScheduleResult


def schedule_result_from_agent_response(response: dict[str, Any]) -> ScheduleResult:
    """从 Agent 返回的 dict 构建 ScheduleResult，并把顶层 explanation 写入 result.explanation。"""
    result = ScheduleResult.model_validate(response["schedule"])
    expl = response.get("explanation")
    if expl is not None:
        result.explanation = ScheduleExplanation.model_validate(expl)
    return result
