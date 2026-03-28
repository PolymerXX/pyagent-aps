"""甘特图组件

使用Plotly创建交互式排程甘特图
"""

from datetime import datetime, timedelta

import plotly.express as px
import plotly.graph_objects as go

_BG = "#f8fafc"
_PAPER = "#ffffff"
_GRID = "#e5e5e5"
_TEXT = "#171717"
_TEXT2 = "#525252"
_FONT = "Inter, -apple-system, BlinkMacSystemFont, sans-serif"


def create_gantt_chart(
    tasks: list[dict],
    title: str = "生产排程甘特图",
    show_today: bool = True,
    height: int = 500,
) -> go.Figure:

    colors = {
        "planned": "#0ea5e9",
        "in_progress": "#22c55e",
        "completed": "#64748b",
        "delayed": "#ef4444",
        "default": "#0f766e",
    }

    if not tasks:
        fig = go.Figure()
        fig.add_annotation(
            text="暂无排程数据",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=18, color="#94a3b8"),
        )
        fig.update_layout(
            title=title,
            height=height,
            paper_bgcolor=_PAPER,
            plot_bgcolor=_BG,
            font=dict(family=_FONT, color=_TEXT),
        )
        return fig

    formatted_tasks = []
    for task in tasks:
        task_copy = task.copy()

        if isinstance(task["start"], (int, float)):
            base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
            task_copy["start"] = base_time + timedelta(hours=task["start"])
            task_copy["finish"] = base_time + timedelta(hours=task["finish"])

        formatted_tasks.append(task_copy)

    fig = px.timeline(
        formatted_tasks,
        x_start="start",
        x_end="finish",
        y="resource",
        color="status" if "status" in tasks[0] else None,
        color_discrete_map=colors,
        hover_name="task",
        hover_data={
            "start": True,
            "finish": True,
            "resource": True,
            "status": True,
        },
    )

    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        title=dict(text=title, font=dict(size=18, weight="bold", color=_TEXT), x=0.01),
        height=height,
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        font=dict(family=_FONT, size=12, color=_TEXT),
        margin=dict(l=20, r=20, t=60, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=_TEXT),
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor=_GRID,
            tickformat="%m/%d %H:%M",
            tickangle=-45,
            color=_TEXT2,
        ),
        yaxis=dict(title="", showgrid=True, gridcolor=_GRID, color=_TEXT2),
    )

    fig.update_traces(
        marker_line_width=1,
        marker_line_color="white",
        opacity=0.9,
    )

    if show_today and formatted_tasks:
        fig.add_vline(
            x=datetime.now(),
            line_dash="dash",
            line_color="#f59e0b",
            line_width=2,
            annotation_text="现在",
            annotation_position="top",
        )

    return fig


def create_machine_timeline(
    machine_data: dict,
    time_range: tuple = (0, 72),
    height: int = 400,
) -> go.Figure:
    fig = go.Figure()

    machine_colors = [
        "#0f766e",
        "#0891b2",
        "#7c3aed",
        "#db2777",
        "#ea580c",
    ]

    for idx, (machine_id, tasks) in enumerate(machine_data.items()):
        color = machine_colors[idx % len(machine_colors)]

        for task in tasks:
            fig.add_trace(
                go.Bar(
                    x=[task["end"] - task["start"]],
                    y=[machine_id],
                    base=[task["start"]],
                    orientation="h",
                    name=machine_id,
                    marker_color=color if task.get("status") != "delayed" else "#ef4444",
                    marker_line_width=1,
                    marker_line_color="white",
                    opacity=0.9,
                    hovertemplate=(
                        f"<b>{task.get('product', 'Unknown')}</b><br>"
                        + "开始: %{base:.1f}h<br>"
                        + "时长: %{x:.1f}h<br>"
                        + "<extra></extra>"
                    ),
                    showlegend=False,
                )
            )

    fig.update_layout(
        title=dict(
            text="生产线时间线",
            font=dict(size=16, weight="bold", color=_TEXT),
            x=0.01,
        ),
        barmode="overlay",
        height=height,
        paper_bgcolor=_PAPER,
        plot_bgcolor=_BG,
        font=dict(family=_FONT, color=_TEXT),
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(
            title="时间 (小时)",
            showgrid=True,
            gridcolor=_GRID,
            range=time_range,
            color=_TEXT2,
        ),
        yaxis=dict(title="", showgrid=True, gridcolor=_GRID, color=_TEXT2),
    )

    return fig
