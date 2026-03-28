"""分析看板页面

生产数据分析和可视化报表
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import io
from datetime import datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.utils import init_page
from ui.state import AppState
from ui.styles import get_kpi_card

init_page("分析看板", "📈")

st.title("📈 分析看板")
st.markdown("生产数据分析和智能洞察")

date_range = st.date_input(
    "选择时间范围",
    value=(datetime.now() - timedelta(days=7), datetime.now()),
    max_value=datetime.now(),
)

schedule_result = AppState.get_schedule_result()

col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

kpi_data = [
    ("primary", str(schedule_result.task_count) if schedule_result else "-", "任务数量"),
    (
        "secondary",
        f"{schedule_result.on_time_delivery_rate * 100:.1f}%" if schedule_result else "-",
        "准时交付率",
    ),
    (
        "accent",
        f"{sum(schedule_result.machine_utilization.values()) / len(schedule_result.machine_utilization) * 100:.1f}%"
        if schedule_result and schedule_result.machine_utilization
        else "-",
        "平均利用率",
    ),
    (
        "warning",
        f"{schedule_result.total_changeover_time:.1f}h" if schedule_result else "-",
        "换产时间",
    ),
]

for col, (variant, value, label) in zip([col_kpi1, col_kpi2, col_kpi3, col_kpi4], kpi_data):
    with col:
        st.markdown(get_kpi_card(value, label, variant), unsafe_allow_html=True)

st.markdown("---")

if schedule_result:
    col_trend, col_pie = st.columns(2)

    with col_trend:
        st.markdown("### 📊 生产线效能分析")

        if schedule_result.machine_utilization:
            machines = list(schedule_result.machine_utilization.keys())
            utilization = [v * 100 for v in schedule_result.machine_utilization.values()]

            fig_efficiency = go.Figure(
                data=[
                    go.Bar(
                        name="利用率",
                        x=machines,
                        y=utilization,
                        marker_color="#0f766e",
                        text=[f"{v:.1f}%" for v in utilization],
                        textposition="outside",
                    )
                ]
            )

            fig_efficiency.update_layout(
                height=350,
                paper_bgcolor="#ffffff",
                plot_bgcolor="#f8fafc",
                font=dict(family="Inter, sans-serif", color="#171717"),
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(
                    title="利用率 (%)",
                    range=[0, 100],
                    showgrid=True,
                    gridcolor="#e5e5e5",
                    color="#525252",
                ),
                xaxis=dict(title="", color="#525252"),
            )

            st.plotly_chart(fig_efficiency, use_container_width=True)

    with col_pie:
        st.markdown("### 🥧 产品类型分布")

        if schedule_result.assignments:
            type_counts = {}
            for a in schedule_result.assignments:
                type_counts[a.product_type] = type_counts.get(a.product_type, 0) + 1

            labels = list(type_counts.keys())
            values = list(type_counts.values())
            colors = ["#0f766e", "#0891b2", "#7c3aed", "#db2777"]

            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.5,
                        marker_colors=colors[: len(labels)],
                        textinfo="label+percent",
                        textposition="outside",
                    )
                ]
            )

            fig_pie.update_layout(
                height=350,
                paper_bgcolor="#ffffff",
                font=dict(family="Inter, sans-serif", color="#171717"),
                showlegend=False,
                margin=dict(l=20, r=20, t=20, b=20),
            )

            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    col_insight, col_risk = st.columns(2)

    with col_insight:
        st.markdown("### 💡 智能洞察")

        if schedule_result.explanation:
            for decision in schedule_result.explanation.key_decisions[:3]:
                st.markdown(
                    f"""
                    <div class="insight-card">
                        📈 {decision}
                    </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("完成排程后将显示智能洞察")

    with col_risk:
        st.markdown("### ⚠️ 风险预警")

        if schedule_result.explanation and schedule_result.explanation.risks:
            for risk in schedule_result.explanation.risks:
                st.markdown(
                    f"""
                    <div class="risk-warning">
                        ⚠️ {risk}
                    </div>
                """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("暂无风险预警")

    st.markdown("---")

    st.markdown("### 📋 详细数据报表")

    if schedule_result.assignments:
        export_data = []
        for a in schedule_result.get_sorted_assignments():
            export_data.append(
                {
                    "订单ID": a.order_id,
                    "产品": a.product_name,
                    "类型": a.product_type,
                    "生产线": a.machine_id,
                    "开始时间": f"{a.start_time:.1f}h",
                    "结束时间": f"{a.end_time:.1f}h",
                    "时长": f"{a.duration:.1f}h",
                    "数量": f"{a.quantity:,}",
                    "状态": a.status.value,
                    "准时": "是" if a.is_on_time else "否",
                }
            )

        df_report = pd.DataFrame(export_data)
        st.dataframe(df_report, use_container_width=True, hide_index=True)

        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            csv_buffer = io.StringIO()
            df_report.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 导出CSV",
                data=csv_buffer.getvalue(),
                file_name=f"aps_report_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with col_exp2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df_report.to_excel(writer, index=False, sheet_name="排程结果")
            excel_buffer.seek(0)
            st.download_button(
                label="📊 导出Excel",
                data=excel_buffer,
                file_name=f"aps_report_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

else:
    st.info("暂无排程数据，请先执行排程计算")

    st.markdown("### 📋 待排程数据概览")

    orders = AppState.get_orders()
    machines = AppState.get_machines()

    col_overview1, col_overview2 = st.columns(2)

    with col_overview1:
        st.markdown("#### 订单概览")
        order_data = [
            {
                "订单ID": o.id,
                "产品": o.product.name,
                "数量": f"{o.quantity:,}",
                "截止时间": f"{o.due_date}h",
            }
            for o in orders
        ]
        df_orders = pd.DataFrame(order_data)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)

    with col_overview2:
        st.markdown("#### 生产线概览")
        machine_data = [
            {"生产线": m.id, "产能/h": f"{m.capacity_per_hour:,}", "状态": m.status.status}
            for m in machines
        ]
        df_machines = pd.DataFrame(machine_data)
        st.dataframe(df_machines, use_container_width=True, hide_index=True)

    if st.button("🚀 前往排程", type="primary", use_container_width=True):
        st.switch_page("pages/3_排程计划.py")
