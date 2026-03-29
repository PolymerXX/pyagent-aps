"""排程计划页面

核心功能页面 - 执行排程计算和展示甘特图
"""

# ruff: noqa: E402

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

from ui.schedule_merge import schedule_result_from_agent_response
from ui.state import AppState
from ui.utils import init_page, log_ui_event

init_page("排程计划", "📅")

from aps.agents.orchestrator import APSSystem
from aps.engine.solver import APSSolver
from aps.models.optimization import OptimizationParams, OptimizationStrategy

from ui.components.gantt_chart import create_gantt_chart
from ui.schedule_edit import (
    apply_editor_df_to_schedule,
    assignments_to_editor_df,
    schedule_edit_signature,
)

STRATEGY_LABEL_CN: dict[OptimizationStrategy, str] = {
    OptimizationStrategy.BALANCED: "均衡优化",
    OptimizationStrategy.ON_TIME_DELIVERY: "最大化准时交付",
    OptimizationStrategy.MINIMIZE_CHANGEOVER: "最小换产时间",
    OptimizationStrategy.MAXIMIZE_PROFIT: "最大化利润",
    OptimizationStrategy.MAX_UTILIZATION: "最大化利用率",
}


def _default_agent_request_text(
    strategy: OptimizationStrategy, allow_overtime: bool, time_limit: int
) -> str:
    return (
        f"请根据当前订单与生产线执行排产优化。"
        f"优化策略：{STRATEGY_LABEL_CN[strategy]}；"
        f"{'允许' if allow_overtime else '不允许'}加班；"
        f"求解时间上限约 {time_limit} 秒。"
    )

st.title("📅 排程计划")
st.markdown("执行智能排程计算，生成最优生产计划")

st.markdown("### 排程模式")
schedule_mode = st.radio(
    "选择排程方式",
    options=["快速排程（求解器直驱）", "多 Agent 协作（APSSystem）"],
    horizontal=True,
    help=(
        "快速模式仅调用 CP-SAT/启发式引擎；Agent 模式走 Orchestrator → Planner → "
        "Scheduler → Validator → Explainer → Monitor 全流程（可配合 LLM）。"
    ),
)

st.markdown("### 排程配置")

col_config1, col_config2, col_config3 = st.columns(3)

with col_config1:
    strategy = st.selectbox(
        "优化策略",
        options=list(OptimizationStrategy),
        format_func=lambda x: STRATEGY_LABEL_CN[x],
    )

with col_config2:
    time_limit = st.slider("求解时间限制 (秒)", min_value=5, max_value=300, value=30, step=5)

with col_config3:
    allow_overtime = st.checkbox("允许加班", value=True)

if schedule_mode == "多 Agent 协作（APSSystem）":
    st.caption(
        "完整 LLM 链路需要可用的 OpenRouter（或与 APS 默认模型匹配）的 API 密钥；"
        "未配置或调用失败时各 Agent 会降级为规则/启发式后备，意图与解释可能较简略。"
    )
    default_nl = _default_agent_request_text(strategy, allow_overtime, time_limit)
    _nl_key = "aps_agent_nl"
    if _nl_key not in st.session_state:
        st.session_state[_nl_key] = default_nl
    user_nl = st.text_area(
        "排产需求（自然语言）",
        height=120,
        key=_nl_key,
        help=(
            "将传给多 Agent 管线；下方策略与时间限制会作为 OptimizationParams 传入，"
            "不会被 Planner 覆盖。"
        ),
    )
else:
    user_nl = ""

col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 3])

with col_btn1:
    run_schedule = st.button("🚀 开始排程", type="primary", use_container_width=True)

with col_btn2:
    clear_schedule = st.button("🗑️ 清除结果", use_container_width=True)

with col_btn3:
    export_result = st.button("📥 导出结果", use_container_width=True)

if clear_schedule:
    AppState.set_schedule_result(None)
    AppState.clear_agent_trace()
    st.rerun()

if run_schedule:
    orders = AppState.get_orders()
    machines = AppState.get_machines()

    if not orders:
        st.error("没有订单数据，请先添加订单")
    elif not machines:
        st.error("没有生产线数据，请先配置生产线")
    else:
        base_constraints = AppState.get_constraints()
        constraints = base_constraints.model_copy(update={"allow_overtime": allow_overtime})
        params = OptimizationParams(strategy=strategy, time_limit_seconds=time_limit)

        if schedule_mode == "快速排程（求解器直驱）":
            spinner_msg = "正在计算最优排程方案（求解器）..."
            with st.spinner(spinner_msg):
                try:
                    solver = APSSolver(
                        orders=orders, machines=machines, constraints=constraints, params=params
                    )
                    result = solver.solve()
                    AppState.set_schedule_result(result)
                    AppState.clear_agent_trace()
                    log_ui_event(
                        "aps.ui.schedule.run",
                        mode="fast",
                        strategy=strategy.value,
                        ok=True,
                        assignment_count=result.task_count,
                    )
                    st.success(f"排程完成！耗时 {result.planning_time_seconds:.2f} 秒")
                    st.rerun()
                except Exception as e:
                    log_ui_event(
                        "aps.ui.schedule.run",
                        mode="fast",
                        strategy=strategy.value,
                        ok=False,
                        error=str(e)[:500],
                    )
                    st.error(f"排程计算失败: {str(e)}")
                    st.info("请检查订单和生产线配置是否正确")
        else:
            spinner_msg = "多 Agent 协作排程中（含 LLM 时可能较慢）..."
            with st.spinner(spinner_msg):
                try:
                    system = APSSystem(
                        orders=orders,
                        machines=machines,
                        constraints=constraints,
                    )
                    text = (
                        user_nl or _default_agent_request_text(strategy, allow_overtime, time_limit)
                    ).strip()
                    response = system.process_request_sync(text, params=params)
                    result = schedule_result_from_agent_response(response)
                    AppState.set_schedule_result(result)
                    AppState.set_agent_trace(
                        {
                            "intent": response["intent"],
                            "optimization_params": response["optimization_params"],
                            "validation": response["validation"],
                            "monitor_report": response["monitor_report"],
                        }
                    )
                    log_ui_event(
                        "aps.ui.schedule.run",
                        mode="agent",
                        strategy=strategy.value,
                        ok=True,
                        assignment_count=result.task_count,
                    )
                    st.success(f"Agent 排程完成！求解耗时 {result.planning_time_seconds:.2f} 秒")
                    st.rerun()
                except Exception as e:
                    log_ui_event(
                        "aps.ui.schedule.run",
                        mode="agent",
                        strategy=strategy.value,
                        ok=False,
                        error=str(e)[:500],
                    )
                    st.error(f"Agent 排程失败: {str(e)}")
                    st.info("请检查订单、生产线、网络与 API 密钥配置是否正确")

result = AppState.get_schedule_result()
agent_trace = AppState.get_agent_trace()

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

    if agent_trace:
        with st.expander("多 Agent 管线摘要", expanded=False):
            st.markdown("**用户意图（Orchestrator）**")
            st.write(agent_trace.get("intent", "—"))

            st.markdown("**本次优化参数**")
            st.json(agent_trace.get("optimization_params", {}))

            st.markdown("**验证结果**")
            val = agent_trace.get("validation") or {}
            st.write(
                f"是否通过: **{'是' if val.get('is_valid') else '否'}**  ·  "
                f"质量分: {val.get('quality_score', '—')}  ·  "
                f"置信度: {val.get('confidence_score', '—')}"
            )
            warns = val.get("warnings") or []
            if warns:
                st.markdown("**警告**")
                for w in warns:
                    st.markdown(f"- {w}")
            violations = val.get("constraint_violations") or []
            if violations:
                st.markdown("**约束违反**")
                for v in violations:
                    st.markdown(f"- {v.get('description', v)}")

            st.markdown("**监控摘要**")
            mon = agent_trace.get("monitor_report") or {}
            st.write(f"总览状态: **{mon.get('overall_status', '—')}**  ·  {mon.get('summary', '')}")
            alerts = mon.get("alerts") or []
            if alerts:
                st.markdown("**告警**")
                for a in alerts:
                    st.markdown(f"- {a}")
            recs = mon.get("recommendations") or []
            if recs:
                st.markdown("**建议**")
                for r in recs:
                    st.markdown(f"- {r}")

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

    if result.assignments:
        with st.expander("手动调整排程", expanded=False):
            st.caption(
                "在表格中修改生产线或起止时间（小时）后点击「应用修改」；"
                "准时性、利用率、换产与完工时间将重算，最优标记会取消。请勿增删行。"
            )
            _fp = schedule_edit_signature(result)
            if st.session_state.get("schedule_edit_fp") != _fp:
                st.session_state["schedule_edit_fp"] = _fp
                st.session_state.pop("schedule_manual_editor", None)

            _m_ids = [m.id for m in AppState.get_machines()]
            _edited_df = st.data_editor(
                assignments_to_editor_df(result),
                column_config={
                    "_idx": st.column_config.NumberColumn("序号", disabled=True, format="%d"),
                    "order_id": st.column_config.TextColumn("订单ID", disabled=True),
                    "product_name": st.column_config.TextColumn("产品", disabled=True),
                    "product_type": st.column_config.TextColumn("类型", disabled=True),
                    "machine_id": st.column_config.SelectboxColumn(
                        "生产线",
                        options=_m_ids,
                        required=True,
                    ),
                    "start_time": st.column_config.NumberColumn(
                        "开始(h)", format="%.2f", min_value=0.0, step=0.5
                    ),
                    "end_time": st.column_config.NumberColumn(
                        "结束(h)", format="%.2f", min_value=0.0, step=0.5
                    ),
                },
                hide_index=True,
                num_rows="fixed",
                use_container_width=True,
                key="schedule_manual_editor",
            )

            if st.button("应用修改", key="apply_manual_schedule", type="secondary"):
                _orders = AppState.get_orders()
                _machines = AppState.get_machines()
                _cons = AppState.get_constraints()
                _new_r, _errs = apply_editor_df_to_schedule(
                    _edited_df, result, _orders, _machines, _cons
                )
                if _errs:
                    log_ui_event(
                        "aps.ui.schedule.manual_edit",
                        ok=False,
                        error_count=len(_errs),
                    )
                    for _e in _errs:
                        st.error(_e)
                else:
                    assert _new_r is not None
                    AppState.set_schedule_result(_new_r)
                    log_ui_event(
                        "aps.ui.schedule.manual_edit",
                        ok=True,
                        assignment_count=_new_r.task_count,
                    )
                    st.success("已应用手动调整并重算指标。")
                    st.rerun()

    st.markdown("#### 甘特图")

    if result.assignments:
        gantt_tasks = []
        for assignment in result.get_sorted_assignments():
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
