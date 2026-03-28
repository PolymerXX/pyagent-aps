"""指标卡片组件"""

from typing import Literal

import streamlit as st

from ui.styles.common import get_status_badge


def render_metric_card(
    label: str,
    value: str,
    delta: str | None = None,
    delta_color: Literal["normal", "inverse", "off"] = "normal",
    icon: str | None = None,
) -> None:
    delta_html = ""
    if delta:
        color_map = {
            "normal": ("metric-delta-positive", "metric-delta-negative"),
            "inverse": ("metric-delta-negative", "metric-delta-positive"),
            "off": ("metric-delta-neutral", "metric-delta-neutral"),
        }
        positive_cls, negative_cls = color_map[delta_color]
        cls = positive_cls if delta.startswith("+") or delta.startswith("↑") else negative_cls
        delta_html = f'<div class="metric-delta {cls}">{delta}</div>'

    icon_html = f'<span class="metric-icon">{icon}</span>' if icon else ""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{icon_html}{label}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
        </div>
    """,
        unsafe_allow_html=True,
    )


def render_status_badge(status: str, label: str | None = None) -> str:
    return get_status_badge(status, label)


def render_progress_card(
    label: str,
    current: int,
    total: int,
    color: str = "#0f766e",
) -> None:
    percentage = (current / total * 100) if total > 0 else 0

    st.markdown(
        f"""
        <div class="progress-card">
            <div class="progress-header">
                <span class="progress-label">{label}</span>
                <span class="progress-count">{current}/{total}</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill" style="background:{color};width:{percentage:.1f}%;"></div>
            </div>
        </div>
    """,
        unsafe_allow_html=True,
    )
