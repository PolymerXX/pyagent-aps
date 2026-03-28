"""排程计划页面

核心功能页面 - 执行排程计算和展示甘特图
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import io
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.utils import init_page
from ui.state import AppState

init_page("排程计划", "📅")

from aps.engine.solver import APSSolver
from aps.models.constraint import ProductionConstraints
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from ui.components.gantt_chart import create_gantt_chart

st.title("📅 排程计划")
st.markdown("执行智能排程计算，生成最优生产计划")

st.markdown("### 排程配置")

col_config1, col_config2, col_config3 = st.columns(3)

with col_config1:
    strategy = st.selectbox(
        "优化策略",
        options=list(OptimizationStrategy),
        format_func=lambda x: {
            "balanced": "均衡优化",
            "on_time": "最大化准时交付",
            "min_changeover": "最小换产时间",
            "max_profit": "最大化利润",
            "max_utilization": "最大化利用率",
        }.get(x.value, x.value),
    )

with col_config2:
    time_limit = st.slider("求解时间限制 (秒)", min_value=5, max_value=300, value=30, step=5)

with col_config3:
    allow_overtime = st.checkbox("允许加班", value=True)

col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])

with col_btn1:
    run_schedule = st.button("🚀 开始排程", type="primary", use_container_width=True)

with col_btn2:
    clear_schedule = st.button("🗑️ 清除结果", use_container_width=True)

with col_btn3:
    export_result = st.button("📥 导出结果", use_container_width=True)

if clear_schedule:
    AppState.set_schedule_result(None)
    st.rerun()

if run_schedule:
    orders = AppState.get_orders()
    machines = AppState.get_machines()

    if not orders:
        st.error("没有订单数据，请先添加订单")
    elif not machines:
        st.error("没有生产线数据，请先配置生产线")
    else:
        constraints = ProductionConstraints(allow_overtime=allow_overtime)
        params = OptimizationParams(strategy=strategy, time_limit_seconds=time_limit)

        with st.spinner("正在计算最优排程方案..."):
            try:
                solver = APSSolver(
                    orders=orders, machines=machines, constraints=constraints, params=params
                )
                result = solver.solve()
                AppState.set_schedule_result(result)
                st.success(f"排程完成！耗时 {result.planning_time_seconds:.2f} 秒")
                st.rerun()
            except Exception as e:
                st.error(f"排程计算失败: {str(e)}")
                st.info("请检查订单和生产线配置是否正确")

result = AppState.get_schedule_result()

if export_result and result:
    export_data = []
    for a in result.get_sorted_assignments():
        export_data.append(
            {
                "订单ID": a.order_id,
                "产品": a.product_name,
                "生产线": a.machine_id,
                "开始时间(h)": a.start_time,
                "结束时间(h)": a.end_time,
                "时长(h)": a.duration,
                "数量": a.quantity,
                "状态": a.status.value,
                "是否准时": "是" if a.is_on_time else "否",
                "延期时长(h)": a.delay_hours,
            }
        )
    df_export = pd.DataFrame(export_data)
    csv_buffer = io.StringIO()
    df_export.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 下载CSV",
        data=csv_buffer.getvalue(),
        file_name=f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

if result:
    st.markdown("---")
    st.markdown("### 排程结果")

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    with col_m1:
        st.metric("总完工时间", f"{result.total_makespan:.1f}h")

    with col_m2:
        st.metric("准时交付率", f"{result.on_time_delivery_rate * 100:.1f}%")

    with col_m3:
        st.metric("换产时间", f"{result.total_changeover_time:.1f}h")

    with col_m4:
        st.metric("任务数量", result.task_count)

    with col_m5:
        is_optimal = "✅ 是" if result.is_optimal else "⚠️ 否"
        st.metric("最优解", is_optimal)

    st.markdown("#### 甘特图")

    if result.assignments:
        gantt_tasks = []
        for assignment in result.assignments:
            gantt_tasks.append(
                {
                    "task": f"{assignment.product_name} ({assignment.order_id})",
                    "start": assignment.start_time,
                    "finish": assignment.end_time,
                    "resource": assignment.machine_id,
                    "status": assignment.status.value,
                }
            )

        fig = create_gantt_chart(
            tasks=gantt_tasks,
            title="",
            show_today=False,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 详细排程表")

    assignment_data = []
    for a in result.get_sorted_assignments():
        status_emoji = {"planned": "📋", "in_progress": "🔄", "completed": "✅", "delayed": "⚠️"}
        assignment_data.append(
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

    df = pd.DataFrame(assignment_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("#### 机器利用率")

    if result.machine_utilization:
        util_fig = go.Figure(
            data=[
                go.Bar(
                    x=list(result.machine_utilization.keys()),
                    y=[v * 100 for v in result.machine_utilization.values()],
                    marker_color="#0f766e",
                    text=[f"{v * 100:.1f}%" for v in result.machine_utilization.values()],
                    textposition="outside",
                )
            ]
        )

        util_fig.update_layout(
            height=300,
            paper_bgcolor="#ffffff",
            plot_bgcolor="#f8fafc",
            font=dict(family="Inter, sans-serif", color="#171717"),
            yaxis=dict(
                title="利用率 (%)",
                range=[0, 100],
                showgrid=True,
                gridcolor="#e5e5e5",
                color="#525252",
            ),
            xaxis=dict(title="", color="#525252"),
        )

        st.plotly_chart(util_fig, use_container_width=True)

    if result.explanation:
        st.markdown("#### 排程分析")

        col_exp1, col_exp2 = st.columns(2)

        with col_exp1:
            st.markdown("**关键决策**")
            for decision in result.explanation.key_decisions:
                st.markdown(f"- {decision}")

        with col_exp2:
            if result.explanation.risks:
                st.markdown("**风险提示**")
                for risk in result.explanation.risks:
                    st.markdown(f"- ⚠️ {risk}")

else:
    st.info("请点击「开始排程」按钮执行排程计算")

    st.markdown("### 待排程订单预览")

    orders = AppState.get_orders()
    preview_data = [
        {
            "订单ID": o.id,
            "产品": o.product.name,
            "类型": o.product.product_type.value,
            "数量": f"{o.quantity:,}",
            "截止时间": f"{o.due_date}h",
            "预估工时": f"{o.estimated_production_hours:.1f}h",
        }
        for o in orders
    ]

    df = pd.DataFrame(preview_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
