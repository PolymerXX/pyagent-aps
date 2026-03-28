"""生产线管理页面

管理生产线的状态和配置
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.utils import init_page
from ui.state import AppState

init_page("生产线管理", "🏭")

from aps.models.order import ProductType

st.title("🏭 生产线管理")
st.markdown("监控和管理所有生产线的运行状态")

col1, col2, col3, col4 = st.columns(4)

machines = AppState.get_machines()
running = sum(1 for m in machines if m.status.status == "running")
idle = sum(1 for m in machines if m.status.status == "idle")
maintenance = sum(1 for m in machines if m.status.status == "maintenance")
total_capacity = sum(m.capacity_per_hour for m in machines if m.status.status == "running")

with col1:
    st.metric("运行中", running, f"{running}/{len(machines)}")

with col2:
    st.metric("空闲", idle)

with col3:
    st.metric("维护中", maintenance)

with col4:
    st.metric("当前产能", f"{total_capacity:,}/h")

st.markdown("---")

st.markdown("### 生产线状态")

cols = st.columns(2)

status_colors = {"running": "#22c55e", "idle": "#f59e0b", "maintenance": "#ef4444"}

status_names = {"running": "运行中", "idle": "空闲", "maintenance": "维护中"}

for idx, machine in enumerate(machines):
    col = cols[idx % 2]

    with col:
        status_color = status_colors.get(machine.status.status, "#64748b")
        status_name = status_names.get(machine.status.status, machine.status.status)

        utilization = (
            (machine.status.uptime_hours / 200) * 100 if machine.status.uptime_hours else 0
        )
        utilization = min(utilization, 100)

        cap_class_map = {
            ProductType.BEVERAGE: "cap-beverage",
            ProductType.DAIRY: "cap-dairy",
            ProductType.JUICE: "cap-juice",
        }
        capability_html = " ".join(
            f'<span class="capability-tag {cap_class_map.get(pt, "")}">{pt.value}</span>'
            for pt in machine.supported_product_types
        )

        st.markdown(
            f"""
            <div class="machine-card">
                <div class="mc-header">
                    <h4 class="mc-title">{machine.name}</h4>
                    <span class="mc-status">
                        <span class="mc-status-dot mc-dot-{machine.status.status}"></span>
                        {status_name}
                    </span>
                </div>
                <div class="mc-capabilities">{capability_html}</div>
                <div class="mc-stats">
                    <div>
                        <div class="mc-stat-label">产能</div>
                        <div class="mc-stat-value">{machine.capacity_per_hour:,} <span class="mc-stat-unit">单位/h</span></div>
                    </div>
                    <div>
                        <div class="mc-stat-label">换产时间</div>
                        <div class="mc-stat-value">{machine.setup_time_hours} <span class="mc-stat-unit">小时</span></div>
                    </div>
                </div>
                <div class="mc-progress">
                    <div class="mc-progress-header">
                        <span class="mc-progress-label">利用率</span>
                        <span class="mc-progress-value">{utilization:.0f}%</span>
                    </div>
                    <div class="mc-progress-track">
                        <div class="mc-progress-fill" style="background:{status_color};width:{utilization:.1f}%;"></div>
                    </div>
                </div>
                <div class="mc-footer">
                    <span>当前任务: {machine.status.current_task or "-"}</span>
                    <span>已完成: {machine.status.completed_tasks} 批</span>
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("---")

st.markdown("### 产能分析")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig_capacity = go.Figure(
        data=[
            go.Bar(
                x=[m.name.split("-")[0].strip() for m in machines],
                y=[m.capacity_per_hour for m in machines],
                marker_color=[
                    "#0f766e" if m.status.status == "running" else "#d1d5db" for m in machines
                ],
                text=[f"{m.capacity_per_hour:,}" for m in machines],
                textposition="outside",
            )
        ]
    )

    fig_capacity.update_layout(
        title="各产线产能",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8fafc",
        font=dict(family="Inter, sans-serif", color="#171717"),
        height=350,
        showlegend=False,
        xaxis=dict(title="", showgrid=False, color="#525252"),
        yaxis=dict(title="单位/小时", showgrid=True, gridcolor="#e5e5e5", color="#525252"),
    )

    st.plotly_chart(fig_capacity, use_container_width=True)

with col_chart2:
    labels = [m.id for m in machines]
    values = [m.status.uptime_hours for m in machines]
    colors = [status_colors.get(m.status.status, "#64748b") for m in machines]

    fig_uptime = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.5,
                marker_colors=colors,
                textinfo="label+percent",
                textposition="outside",
            )
        ]
    )

    fig_uptime.update_layout(
        title="运行时间分布",
        paper_bgcolor="#ffffff",
        font=dict(family="Inter, sans-serif", color="#171717"),
        height=350,
        showlegend=False,
    )

    st.plotly_chart(fig_uptime, use_container_width=True)

st.markdown("---")

st.markdown("### 状态控制")

machine_ids = [m.id for m in machines]
machine_names = {m.id: m.name for m in machines}
machine_current_status = {m.id: m.status.status for m in machines}

col_select, col_status, col_action = st.columns([2, 2, 1])

with col_select:
    selected_machine = st.selectbox(
        "选择生产线",
        options=machine_ids,
        format_func=lambda x: f"{x} - {machine_names.get(x, '')}",
    )

with col_status:
    status_options = ["running", "idle", "maintenance"]
    status_labels = {"running": "运行中", "idle": "空闲", "maintenance": "维护中"}
    current_idx = status_options.index(machine_current_status.get(selected_machine, "idle"))
    new_status = st.selectbox(
        "新状态",
        options=status_options,
        format_func=lambda x: status_labels.get(x, x),
        index=current_idx,
    )

with col_action:
    st.write("")
    st.write("")
    if st.button("更新状态", type="primary", use_container_width=True):
        if AppState.update_machine_status(selected_machine, new_status):
            st.success(f"{selected_machine} 状态已更新为 {status_labels[new_status]}")
            st.rerun()
        else:
            st.error("更新失败")

st.markdown("### 详细数据")

machine_data = [
    {
        "生产线": m.id,
        "名称": m.name,
        "状态": status_names.get(m.status.status, m.status.status),
        "产能/h": f"{m.capacity_per_hour:,}",
        "换产时间": f"{m.setup_time_hours}h",
        "支持类型": ", ".join([pt.value for pt in m.supported_product_types]),
        "运行时长": f"{m.status.uptime_hours}h",
        "已完成任务": m.status.completed_tasks,
    }
    for m in machines
]

df = pd.DataFrame(machine_data)
st.dataframe(df, use_container_width=True, hide_index=True)
