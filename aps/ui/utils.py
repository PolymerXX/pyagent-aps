"""UI工具模块

共享工具函数和常量
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar

_project_root = Path(__file__).resolve().parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
import streamlit as st


def init_project_path() -> None:
    for _p in (_project_root, _aps_parent):
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))


def init_page(title: str, icon: str, page_title: str | None = None) -> None:
    init_project_path()
    from ui.styles import apply_all_styles

    st.set_page_config(
        page_title=page_title or f"{title} - APS",
        page_icon=icon,
        layout="wide",
    )
    apply_all_styles()


STATUS_COLORS: Dict[str, str] = {
    "running": "#22c55e",
    "idle": "#f59e0b",
    "maintenance": "#ef4444",
    "planned": "#0ea5e9",
    "in_progress": "#22c55e",
    "completed": "#64748b",
    "delayed": "#ef4444",
}

STATUS_NAMES: Dict[str, str] = {
    "running": "运行中",
    "idle": "空闲",
    "maintenance": "维护中",
    "planned": "已计划",
    "in_progress": "进行中",
    "completed": "已完成",
    "delayed": "延期",
}

PRODUCT_TYPE_COLORS: Dict[Any, tuple] = {}


def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def generate_order_id(existing_orders: List) -> str:
    existing_ids = {o.id for o in existing_orders}
    base_num = 1001
    while f"O-{base_num}" in existing_ids:
        base_num += 1
    return f"O-{base_num}"


def generate_product_id(existing_orders: List) -> str:
    existing_product_ids = {o.product.id for o in existing_orders}
    base_num = 100
    while f"P-{base_num}" in existing_product_ids:
        base_num += 1
    return f"P-{base_num}"


def build_assignment_dataframe(result) -> pd.DataFrame:
    from aps.models.schedule import ScheduleResult

    if not result or not result.assignments:
        return pd.DataFrame()

    data = []
    for a in result.get_sorted_assignments():
        status_emoji = {
            "planned": "📋",
            "in_progress": "🔄",
            "completed": "✅",
            "delayed": "⚠️",
        }
        data.append(
            {
                "订单ID": a.order_id,
                "产品": a.product_name,
                "生产线": a.machine_id,
                "开始时间": f"{a.start_time:.1f}h",
                "结束时间": f"{a.end_time:.1f}h",
                "时长": f"{a.duration:.1f}h",
                "数量": f"{a.quantity:,}",
                "状态": f"{status_emoji.get(a.status.value, '📋')} {a.status.value}",
                "准时": "✅" if a.is_on_time else f"⚠️ 延期{a.delay_hours:.1f}h",
            }
        )

    return pd.DataFrame(data)


def get_due_color(due_date: float) -> str:
    if due_date <= 24:
        return "#ef4444"
    elif due_date <= 48:
        return "#f59e0b"
    return "#10b981"


def get_due_emoji(due_date: float) -> str:
    if due_date <= 24:
        return "🔴"
    elif due_date <= 48:
        return "🟡"
    return "🟢"


def calculate_avg_utilization(machine_utilization: Optional[Dict[str, float]]) -> float:
    if not machine_utilization or len(machine_utilization) == 0:
        return 1.0
    return sum(machine_utilization.values()) / len(machine_utilization)


def format_hours(hours: float) -> str:
    if hours < 1:
        return f"{hours * 60:.0f}分钟"
    return f"{hours:.1f}小时"


def truncate_text(text: str, max_length: int = 30) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
