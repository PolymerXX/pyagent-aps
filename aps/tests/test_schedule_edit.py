"""ui.schedule_edit：手工编辑 DataFrame 与指标重算（无 Streamlit）"""

from __future__ import annotations

import pandas as pd

from aps.models.constraint import ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus
from ui.schedule_edit import (
    apply_editor_df_to_schedule,
    assignments_to_editor_df,
    schedule_edit_signature,
)


def _sample_order(due: int = 24) -> Order:
    return Order(
        id="O001",
        product=Product(
            id="P001",
            name="测试产品A",
            product_type=ProductType.BEVERAGE,
            unit_profit=1.5,
            production_rate=100.0,
        ),
        quantity=1000,
        due_date=due,
        min_start_time=0,
    )


def _sample_machine() -> ProductionLine:
    return ProductionLine(
        id="M001",
        name="测试产线1",
        supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY],
        capacity_per_hour=100.0,
        setup_time_hours=0.5,
        status=MachineStatus(machine_id="M001", status="active"),
    )


def test_schedule_edit_signature_stable() -> None:
    order = _sample_order()
    m = _sample_machine()
    a = TaskAssignment(
        order_id=order.id,
        machine_id=m.id,
        product_name=order.product.name,
        product_type=order.product.product_type.value,
        start_time=0.0,
        end_time=10.0,
        quantity=order.quantity,
        status=TaskStatus.PLANNED,
        is_on_time=True,
        delay_hours=0.0,
    )
    r = ScheduleResult(assignments=[a], total_makespan=10.0)
    assert schedule_edit_signature(r) == schedule_edit_signature(r)


def test_apply_editor_marks_late_when_end_after_due() -> None:
    order = _sample_order(due=24)
    m = _sample_machine()
    a = TaskAssignment(
        order_id=order.id,
        machine_id=m.id,
        product_name=order.product.name,
        product_type=order.product.product_type.value,
        start_time=0.0,
        end_time=10.0,
        quantity=order.quantity,
        status=TaskStatus.PLANNED,
        is_on_time=True,
        delay_hours=0.0,
    )
    result = ScheduleResult(
        assignments=[a],
        total_makespan=10.0,
        on_time_delivery_rate=1.0,
        is_optimal=True,
    )
    df = assignments_to_editor_df(result)
    df.loc[0, "end_time"] = 30.0

    new_r, errs = apply_editor_df_to_schedule(df, result, [order], [m], ProductionConstraints())
    assert errs == []
    assert new_r is not None
    assert new_r.assignments[0].is_on_time is False
    assert new_r.assignments[0].delay_hours == 6.0
    assert new_r.is_optimal is False


def test_apply_editor_invalid_machine() -> None:
    order = _sample_order()
    m = _sample_machine()
    a = TaskAssignment(
        order_id=order.id,
        machine_id=m.id,
        product_name=order.product.name,
        product_type=order.product.product_type.value,
        start_time=0.0,
        end_time=10.0,
        quantity=order.quantity,
        status=TaskStatus.PLANNED,
        is_on_time=True,
        delay_hours=0.0,
    )
    result = ScheduleResult(assignments=[a], total_makespan=10.0)
    df = assignments_to_editor_df(result)
    df.loc[0, "machine_id"] = "UNKNOWN"

    new_r, errs = apply_editor_df_to_schedule(df, result, [order], [m], ProductionConstraints())
    assert new_r is None
    assert errs


def test_apply_editor_row_count_mismatch() -> None:
    order = _sample_order()
    m = _sample_machine()
    a = TaskAssignment(
        order_id=order.id,
        machine_id=m.id,
        product_name=order.product.name,
        product_type=order.product.product_type.value,
        start_time=0.0,
        end_time=10.0,
        quantity=order.quantity,
        status=TaskStatus.PLANNED,
        is_on_time=True,
        delay_hours=0.0,
    )
    result = ScheduleResult(assignments=[a], total_makespan=10.0)
    df = assignments_to_editor_df(result)
    df = pd.concat([df, df], ignore_index=True)

    new_r, errs = apply_editor_df_to_schedule(df, result, [order], [m], ProductionConstraints())
    assert new_r is None
    assert any("行数不匹配" in e for e in errs)
