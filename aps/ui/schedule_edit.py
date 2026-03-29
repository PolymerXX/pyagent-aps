"""排程手工编辑：DataFrame 与 ScheduleResult 互转及指标重算（无 Streamlit 依赖）"""

from __future__ import annotations

import pandas as pd
from aps.engine.schedule_metrics import calculate_machine_utilization
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.order import Order
from aps.models.schedule import ScheduleResult, TaskAssignment


def schedule_edit_signature(result: ScheduleResult) -> tuple:
    """用于检测排程是否被新求解结果替换，以重置编辑器缓存。"""
    return tuple(
        (a.order_id, round(a.start_time, 6), round(a.end_time, 6), a.machine_id)
        for a in result.get_sorted_assignments()
    )


def assignments_to_editor_df(result: ScheduleResult) -> pd.DataFrame:
    rows = []
    for i, a in enumerate(result.get_sorted_assignments()):
        rows.append(
            {
                "_idx": i,
                "order_id": a.order_id,
                "product_name": a.product_name,
                "product_type": a.product_type,
                "machine_id": a.machine_id,
                "start_time": float(a.start_time),
                "end_time": float(a.end_time),
            }
        )
    return pd.DataFrame(rows)


def _recompute_changeover(
    assignments: list[TaskAssignment], constraints: ProductionConstraints
) -> float:
    total = 0.0
    by_machine: dict[str, list[TaskAssignment]] = {}
    for a in assignments:
        by_machine.setdefault(a.machine_id, []).append(a)
    for group in by_machine.values():
        seq = sorted(group, key=lambda x: x.start_time)
        for i in range(1, len(seq)):
            prev_t = seq[i - 1].product_type
            cur_t = seq[i].product_type
            total += constraints.get_changeover_time(prev_t, cur_t)
    return total


def apply_editor_df_to_schedule(
    df: pd.DataFrame,
    result: ScheduleResult,
    orders: list[Order],
    machines: list[ProductionLine],
    constraints: ProductionConstraints,
) -> tuple[ScheduleResult | None, list[str]]:
    """根据编辑后的 DataFrame 构建新 ScheduleResult；失败时返回 (None, errors)。"""
    errors: list[str] = []
    sorted_orig = result.get_sorted_assignments()
    if len(df) != len(sorted_orig):
        return None, [f"行数不匹配（期望 {len(sorted_orig)}，当前 {len(df)}），请勿增删行。"]

    order_by_id = {o.id: o for o in orders}
    machine_by_id = {m.id: m for m in machines}

    new_assignments: list[TaskAssignment] = []

    for row_pos, orig in enumerate(sorted_orig):
        row = df.iloc[row_pos]
        try:
            idx = int(row["_idx"])
        except (TypeError, ValueError, KeyError):
            idx = row_pos
        if idx != row_pos:
            errors.append(f"第 {row_pos + 1} 行序号异常，请刷新后重试。")
            continue

        order_id = str(row["order_id"])
        if order_id != orig.order_id:
            errors.append(f"第 {row_pos + 1} 行订单 ID 不可修改。")
            continue

        order = order_by_id.get(order_id)
        if order is None:
            errors.append(f"订单 {order_id} 在当前会话中不存在。")
            continue

        machine_id = str(row["machine_id"])
        machine = machine_by_id.get(machine_id)
        if machine is None:
            errors.append(f"第 {row_pos + 1} 行生产线「{machine_id}」无效。")
            continue

        pt = order.product.product_type
        if str(row["product_type"]) != pt.value:
            errors.append(f"第 {row_pos + 1} 行产品类型与订单不一致，请勿修改只读列。")
            continue

        if not machine.can_produce(pt):
            errors.append(f"第 {row_pos + 1} 行：生产线 {machine_id} 不支持产品类型 {pt.value}。")
            continue

        try:
            start_time = float(row["start_time"])
            end_time = float(row["end_time"])
        except (TypeError, ValueError):
            errors.append(f"第 {row_pos + 1} 行起止时间必须为数字。")
            continue

        if end_time <= start_time:
            errors.append(f"第 {row_pos + 1} 行：结束时间必须大于开始时间。")
            continue

        due = float(order.due_date)
        is_on_time = end_time <= due
        delay_hours = max(0.0, end_time - due)

        new_assignments.append(
            orig.model_copy(
                update={
                    "machine_id": machine_id,
                    "product_name": order.product.name,
                    "product_type": order.product.product_type.value,
                    "start_time": start_time,
                    "end_time": end_time,
                    "quantity": order.quantity,
                    "is_on_time": is_on_time,
                    "delay_hours": delay_hours,
                }
            )
        )

    if errors:
        return None, errors

    makespan = max(a.end_time for a in new_assignments) if new_assignments else 0.0
    on_time_count = sum(1 for a in new_assignments if a.is_on_time)
    on_time_rate = on_time_count / len(new_assignments) if new_assignments else 1.0
    utilization = calculate_machine_utilization(new_assignments, machines, makespan)
    changeover = _recompute_changeover(new_assignments, constraints)

    new_result = result.model_copy(
        update={
            "assignments": new_assignments,
            "total_makespan": makespan,
            "on_time_delivery_rate": on_time_rate,
            "total_changeover_time": changeover,
            "machine_utilization": utilization,
            "is_optimal": False,
        }
    )
    return new_result, []
