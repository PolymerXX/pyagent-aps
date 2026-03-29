"""排程汇总指标（供求解器与 UI 手工编辑复用）"""

from __future__ import annotations

from aps.models.machine import ProductionLine
from aps.models.schedule import TaskAssignment


def calculate_machine_utilization(
    assignments: list[TaskAssignment],
    machines: list[ProductionLine],
    makespan: float,
) -> dict[str, float]:
    utilization: dict[str, float] = {}
    for machine in machines:
        machine_assignments = [a for a in assignments if a.machine_id == machine.id]
        if not machine_assignments or makespan == 0:
            utilization[machine.id] = 0.0
            continue
        total_work = sum(a.duration for a in machine_assignments)
        utilization[machine.id] = total_work / makespan
    return utilization
