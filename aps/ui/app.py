"""APS 智能排程系统 - 主入口

现代SaaS风格的制造排程系统UI
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from aps.core.logfire_setup import init_logfire

init_logfire()

import pandas as pd
import streamlit as st

from ui.state import AppState
from ui.styles import apply_all_styles

st.set_page_config(
    page_title="APS 智能排程系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "APS Multi-Agent Advanced Planning & Scheduling System",
    },
)

apply_all_styles()

st.markdown(
    """
<div style="padding: 1rem 0 2rem 0;">
    <p class="aps-header">APS 智能排程系统</p>
    <p class="aps-subtitle">Multi-Agent Advanced Planning & Scheduling</p>
</div>
<hr class="aps-divider">
""",
    unsafe_allow_html=True,
)

orders = AppState.get_orders()
machines = AppState.get_machines()
schedule_result = AppState.get_schedule_result()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("待排程订单", len(orders), f"{sum(o.quantity for o in orders):,} 单位")

with col2:
    running_machines = [m for m in machines if m.status.status == "running"]
    utilization_pct = len(running_machines) / len(machines) * 100 if machines else 0
    st.metric(
        "生产线运行",
        f"{len(running_machines)}/{len(machines)}",
        f"{utilization_pct:.0f}% 利用",
    )

with col3:
    if schedule_result:
        st.metric(
            "准时交付率",
            f"{schedule_result.on_time_delivery_rate * 100:.1f}%",
            f"{schedule_result.on_time_count}/{schedule_result.task_count} 准时",
        )
    else:
        st.metric("准时交付率", "-", "暂无数据")

with col4:
    if schedule_result:
        st.metric(
            "本周完工", schedule_result.task_count, f"{schedule_result.total_makespan:.1f}h 完工"
        )
    else:
        st.metric("本周完工", "-", "暂无数据")

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 快速操作")

    c1, c2, c3 = st.columns(3)

    with c1:
        if st.button("📋 新建订单", use_container_width=True):
            st.switch_page("pages/1_订单管理.py")

    with c2:
        if st.button("🚀 开始排程", use_container_width=True, type="primary"):
            st.switch_page("pages/3_排程计划.py")

    with c3:
        if st.button("📊 查看报表", use_container_width=True):
            st.switch_page("pages/4_分析看板.py")

    st.markdown("#### 订单概览")

    order_preview = [
        {
            "订单ID": o.id,
            "产品": o.product.name,
            "数量": f"{o.quantity:,}",
            "截止时间": f"{o.due_date}h",
            "状态": "待排程",
        }
        for o in orders[:5]
    ]

    if order_preview:
        df_orders = pd.DataFrame(order_preview)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.info("暂无订单数据")

with col_right:
    st.markdown("### 系统状态")

    status_items = [
        ("🟢", "排程引擎", "运行正常"),
        ("🟢", "数据同步", "实时同步"),
    ]

    for m in machines:
        if m.status.status == "running":
            status_items.append(("🟢", m.id, "运行中"))
        elif m.status.status == "idle":
            status_items.append(("🟡", m.id, "空闲"))
        else:
            status_items.append(("🔴", m.id, "维护中"))

    for icon, name, status in status_items[:6]:
        st.markdown(
            f"""
            <div class="status-row">
                <span>{icon} {name}</span>
                <span class="status-row-value">{status}</span>
            </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.markdown("#### 即将到期订单")

    sorted_orders = sorted(orders, key=lambda o: o.due_date)[:3]

    for o in sorted_orders:
        if o.due_date <= 24:
            due_color = "#ef4444"
            due_status = "🔴"
        elif o.due_date <= 48:
            due_color = "#f59e0b"
            due_status = "🟡"
        else:
            due_color = "#10b981"
            due_status = "🟢"

        st.markdown(
            f"""
            <div class="due-item">
                <span class="due-id">{o.id}</span>
                <span class="due-product">{o.product.name}</span>
                <span class="due-time" style="color:{due_color};">
                    {due_status} {o.due_date}h
                </span>
            </div>
        """,
            unsafe_allow_html=True,
        )
