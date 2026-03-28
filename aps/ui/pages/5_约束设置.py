"""约束设置页面

配置生产约束和换产规则
"""

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pandas as pd
import streamlit as st

from ui.utils import init_page
from ui.state import AppState

init_page("约束设置", "⚙️")

from aps.models.constraint import ChangeoverRule, DEFAULT_CHANGEOVER_RULES, ProductionConstraints

st.title("⚙️ 约束设置")
st.markdown("配置生产约束规则和换产参数")

st.markdown("### 📅 时间约束")

constraints = AppState.get_constraints()

col_time1, col_time2, col_time3 = st.columns(3)

with col_time1:
    max_daily = st.number_input(
        "每日最大生产时间 (小时)",
        min_value=8.0,
        max_value=24.0,
        value=constraints.max_daily_hours,
        step=0.5,
        help="每条生产线每日最大运行时间",
    )

with col_time2:
    max_consecutive = st.number_input(
        "最大连续工作时间 (小时)",
        min_value=4.0,
        max_value=12.0,
        value=constraints.max_consecutive_hours,
        step=0.5,
        help="连续生产后需要休息的最大时长",
    )

with col_time3:
    min_break = st.number_input(
        "最小休息时间 (小时)",
        min_value=0.0,
        max_value=4.0,
        value=constraints.min_break_hours,
        step=0.25,
        help="连续工作后的最小休息时长",
    )

st.markdown("### ⏰ 加班设置")

col_ot1, col_ot2 = st.columns(2)

with col_ot1:
    allow_overtime = st.checkbox("允许加班", value=constraints.allow_overtime)

with col_ot2:
    if allow_overtime:
        max_overtime = st.number_input(
            "最大加班时长 (小时)",
            min_value=0.0,
            max_value=8.0,
            value=constraints.max_overtime_hours,
            step=0.5,
        )
    else:
        max_overtime = 0.0

st.markdown("---")

st.markdown("### 🔄 换产规则")

changeover_rules = AppState.get_changeover_rules()

unique_types = list(
    set([r.from_type for r in changeover_rules] + [r.to_type for r in changeover_rules])
)

if not unique_types:
    unique_types = ["beverage", "dairy", "juice"]

st.markdown("#### 换产时间矩阵")

matrix_dict = {}
for rule in changeover_rules:
    key = (rule.from_type, rule.to_type)
    matrix_dict[key] = rule.setup_hours

matrix_data = []
for from_type in sorted(unique_types):
    row = {"从\\到": from_type}
    for to_type in sorted(unique_types):
        if from_type == to_type:
            row[to_type] = "-"
        else:
            hours = matrix_dict.get((from_type, to_type), 1.0)
            row[to_type] = f"{hours}h"
    matrix_data.append(row)

if matrix_data:
    df_matrix = pd.DataFrame(matrix_data)
    st.dataframe(df_matrix, use_container_width=True, hide_index=True)

st.markdown("#### 换产规则列表")

rule_changes = {}
for idx, rule in enumerate(changeover_rules):
    col_rule1, col_rule2, col_rule3, col_rule4 = st.columns([2, 2, 1, 1])

    with col_rule1:
        st.markdown(f"**{rule.from_type}** → **{rule.to_type}**")

    with col_rule2:
        new_hours = st.number_input(
            "换产时间",
            min_value=0.0,
            max_value=24.0,
            value=rule.setup_hours,
            step=0.5,
            key=f"rule_hours_{idx}",
            label_visibility="collapsed",
        )

    with col_rule3:
        new_priority = st.selectbox(
            "优先级",
            options=range(1, 11),
            index=rule.priority - 1,
            key=f"rule_priority_{idx}",
            label_visibility="collapsed",
        )

    with col_rule4:
        enabled = st.checkbox("启用", value=rule.enabled, key=f"rule_enabled_{idx}")

    rule_changes[idx] = {"hours": new_hours, "priority": new_priority, "enabled": enabled}

col_apply, _ = st.columns([1, 3])
with col_apply:
    if st.button("应用规则更改", use_container_width=True):
        for idx, changes in rule_changes.items():
            changeover_rules[idx].setup_hours = changes["hours"]
            changeover_rules[idx].priority = changes["priority"]
            changeover_rules[idx].enabled = changes["enabled"]
        AppState.set_changeover_rules(changeover_rules)
        st.success("规则已更新")
        st.rerun()

st.markdown("#### 添加新规则")

with st.form("new_rule_form"):
    col_new1, col_new2, col_new3 = st.columns(3)

    with col_new1:
        new_from = st.selectbox("源产品类型", options=sorted(unique_types), key="new_from")

    with col_new2:
        new_to = st.selectbox("目标产品类型", options=sorted(unique_types), key="new_to")

    with col_new3:
        new_setup_hours = st.number_input(
            "换产时间 (小时)", min_value=0.0, max_value=24.0, value=1.0, step=0.5
        )

    submitted = st.form_submit_button("添加规则", type="primary")

    if submitted and new_from != new_to:
        existing = any(r.from_type == new_from and r.to_type == new_to for r in changeover_rules)

        if not existing:
            new_rule = ChangeoverRule(
                from_type=new_from,
                to_type=new_to,
                setup_hours=new_setup_hours,
                priority=5,
                enabled=True,
            )
            changeover_rules.append(new_rule)
            AppState.set_changeover_rules(changeover_rules)
            st.success(f"已添加规则: {new_from} → {new_to}")
            st.rerun()
        else:
            st.warning("该规则已存在")

st.markdown("---")

st.markdown("### 💾 保存配置")

col_save1, col_save2, col_save3 = st.columns([1, 1, 2])

with col_save1:
    if st.button("💾 保存配置", type="primary", use_container_width=True):
        new_constraints = ProductionConstraints(
            max_daily_hours=max_daily,
            min_break_hours=min_break,
            max_consecutive_hours=max_consecutive,
            allow_overtime=allow_overtime,
            max_overtime_hours=max_overtime,
            changeover_rules=changeover_rules,
        )
        AppState.set_constraints(new_constraints)
        AppState.set_changeover_rules(changeover_rules)
        st.success("配置已保存!")
        st.rerun()

with col_save2:
    if st.button("🔄 重置默认", use_container_width=True):
        AppState.set_constraints(ProductionConstraints())
        AppState.set_changeover_rules(DEFAULT_CHANGEOVER_RULES.copy())
        st.success("已重置为默认配置")
        st.rerun()

st.markdown("---")

st.markdown("### 📋 当前配置摘要")

enabled_rules_count = len([r for r in changeover_rules if r.enabled])

summary_data = {
    "配置项": [
        "每日最大生产时间",
        "最大连续工作时间",
        "最小休息时间",
        "允许加班",
        "最大加班时长",
        "换产规则数量",
    ],
    "当前值": [
        f"{max_daily}h",
        f"{max_consecutive}h",
        f"{min_break}h",
        "是" if allow_overtime else "否",
        f"{max_overtime}h" if allow_overtime else "-",
        f"{enabled_rules_count} 条",
    ],
}

df_summary = pd.DataFrame(summary_data)
st.table(df_summary)
