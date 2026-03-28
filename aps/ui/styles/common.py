"""公共样式模块

抽取公共CSS样式，确保UI一致性
"""

ALL_STYLES = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Design Tokens ── */
    :root {
        --primary: #0f766e;
        --primary-light: #14b8a6;
        --primary-dark: #0d5d58;
        --accent: #f59e0b;
        --success: #10b981;
        --warning: #f59e0b;
        --danger: #ef4444;
        --neutral-50: #fafafa;
        --neutral-100: #f5f5f5;
        --neutral-200: #e5e5e5;
        --neutral-300: #d4d4d4;
        --neutral-600: #525252;
        --neutral-700: #404040;
        --neutral-800: #262626;
        --neutral-900: #171717;
        --card-bg: #ffffff;
        --card-border: #e5e5e5;
        --card-shadow: 0 1px 3px rgba(0,0,0,0.06);
        --card-shadow-hover: 0 4px 12px rgba(0,0,0,0.08);
        --text-primary: #171717;
        --text-secondary: #525252;
        --text-muted: #737373;
        --surface-bg: #f8fafc;
    }

    /* ── Streamlit Overrides ── */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: var(--surface-bg);
    }
    .stApp > header { background-color: transparent; }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: var(--surface-bg);
    }
    div[data-testid="stToolbar"] { display: none; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #134e4a 0%, #0f766e 100%) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    section[data-testid="stSidebar"] label {
        color: rgba(255,255,255,0.95) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown { color: rgba(255,255,255,0.95); }
    [data-testid="stSidebarNav"] { background: transparent; }
    [data-testid="stSidebarNav"] ul { gap: 4px; }
    [data-testid="stSidebarNav"] li a {
        border-radius: 8px; padding: 12px 16px; margin: 2px 8px;
        color: rgba(255,255,255,0.85) !important; font-weight: 500;
        transition: all 0.2s ease;
    }
    [data-testid="stSidebarNav"] li a:hover {
        background: rgba(255,255,255,0.1); color: white !important;
    }
    [data-testid="stSidebarNav"] li a.active {
        background: rgba(255,255,255,0.2); color: white !important; font-weight: 600;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255,255,255,0.15); color: white;
        border: 1px solid rgba(255,255,255,0.2);
    }
    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255,255,255,0.25);
    }

    .stButton > button {
        background: var(--primary); color: white; border: none;
        border-radius: 8px; padding: 10px 20px; font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: var(--primary-dark); transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15,118,110,0.3);
    }
    .stButton > button:active { transform: translateY(0); }

    [data-testid="stMetric"] {
        background: var(--card-bg); border-radius: 12px; padding: 1rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
    }
    [data-testid="stMetric"] label {
        font-size: 0.75rem; color: var(--text-muted); font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.75rem; font-weight: 700; color: var(--text-primary);
    }
    [data-testid="stMetric"] [data-testid="stMetricDelta"] { color: var(--text-secondary); }

    .stDataFrame { border-radius: 12px; overflow: hidden; border: 1px solid var(--card-border); }
    .stAlert { border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; padding: 10px 20px; }

    /* ── Header / Layout ── */
    .aps-header {
        font-size: 2.5rem; font-weight: 700; color: var(--text-primary);
        margin-bottom: 0.5rem; letter-spacing: -0.02em;
    }
    .aps-subtitle {
        font-size: 1.1rem; color: var(--text-secondary); font-weight: 400;
    }
    .aps-divider {
        border: none; height: 1px; background: var(--card-border);
        margin: 0.5rem 0 1.5rem 0;
    }

    /* ── Status Row (app.py system status list) ── */
    .status-row {
        display: flex; justify-content: space-between;
        padding: 8px 0; border-bottom: 1px solid var(--card-border);
        color: var(--text-primary);
    }
    .status-row-value { color: var(--text-secondary); }

    /* ── Due Item (app.py deadline orders) ── */
    .due-item {
        display: flex; justify-content: space-between;
        padding: 6px 0; font-size: 0.875rem; color: var(--text-primary);
    }
    .due-id { font-weight: 500; }
    .due-product { color: var(--text-secondary); }
    .due-time { font-weight: 600; }

    /* ── Generic Card ── */
    .card {
        background: var(--card-bg); border-radius: 12px; padding: 1.25rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        transition: all 0.2s ease;
    }
    .card:hover { box-shadow: var(--card-shadow-hover); }

    /* ── Status Badge ── */
    .status-badge {
        display: inline-flex; align-items: center; padding: 4px 12px;
        border-radius: 20px; font-size: 0.75rem; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    .status-running  { background: #d1fae5; color: #065f46; }
    .status-idle     { background: #fef3c7; color: #92400e; }
    .status-maintenance { background: #fee2e2; color: #991b1b; }
    .status-planned  { background: #e0e7ff; color: #3730a3; }
    .status-delayed  { background: #fee2e2; color: #991b1b; }

    /* ── Machine Card (生产线) ── */
    .machine-card {
        background: var(--card-bg); border-radius: 16px; padding: 1.5rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        color: var(--text-primary); transition: all 0.2s ease;
    }
    .machine-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
    .mc-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 12px;
    }
    .mc-title { margin: 0; font-size: 1.1rem; font-weight: 600; color: var(--text-primary); }
    .mc-status {
        display: flex; align-items: center; font-size: 0.875rem;
        font-weight: 500; color: var(--text-secondary);
    }
    .mc-status-dot {
        width: 10px; height: 10px; border-radius: 50%;
        display: inline-block; margin-right: 8px;
    }
    .mc-dot-running  { background-color: #22c55e; }
    .mc-dot-idle     { background-color: #f59e0b; }
    .mc-dot-maintenance { background-color: #ef4444; }
    .mc-capabilities { margin-bottom: 12px; }
    .capability-tag {
        display: inline-block; padding: 4px 10px; border-radius: 6px;
        font-size: 0.75rem; font-weight: 500; margin-right: 6px; margin-bottom: 6px;
    }
    .cap-beverage { background: #d1fae5; color: #065f46; }
    .cap-dairy    { background: #fef3c7; color: #92400e; }
    .cap-juice    { background: #fce7f3; color: #9d174d; }
    .mc-stats {
        display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;
    }
    .mc-stat-label {
        font-size: 0.75rem; color: var(--text-muted); margin-bottom: 4px;
    }
    .mc-stat-value {
        font-size: 1.25rem; font-weight: 600; color: var(--text-primary);
    }
    .mc-stat-unit { font-size: 0.75rem; color: var(--text-muted); }
    .mc-progress { margin-bottom: 8px; }
    .mc-progress-header {
        display: flex; justify-content: space-between;
        font-size: 0.75rem; margin-bottom: 4px;
    }
    .mc-progress-label { color: var(--text-muted); }
    .mc-progress-value { font-weight: 600; color: var(--text-primary); }
    .mc-progress-track {
        background: var(--neutral-200); border-radius: 4px;
        height: 8px; overflow: hidden;
    }
    .mc-progress-fill {
        height: 100%; border-radius: 4px; transition: width 0.3s ease;
    }
    .mc-footer {
        display: flex; justify-content: space-between;
        font-size: 0.875rem; color: var(--text-secondary);
        padding-top: 8px; border-top: 1px solid var(--neutral-100);
    }

    /* ── Schedule Metric ── */
    .schedule-metric {
        background: var(--card-bg); border-radius: 12px; padding: 1.25rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        text-align: center; color: var(--text-primary);
    }

    /* ── Constraint Card ── */
    .constraint-card {
        background: var(--card-bg); border-radius: 12px; padding: 1.5rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        margin-bottom: 1rem;
    }

    /* ── Metric Card Component ── */
    .metric-card {
        background: var(--card-bg); border-radius: 12px; padding: 1.25rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        color: var(--text-primary);
    }
    .metric-label {
        font-size: 0.75rem; color: var(--text-muted); font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;
    }
    .metric-value {
        font-size: 1.75rem; font-weight: 700; color: var(--text-primary);
        letter-spacing: -0.02em;
    }
    .metric-icon { font-size: 1.5rem; margin-right: 8px; }
    .metric-delta { font-size: 0.875rem; font-weight: 600; margin-top: 4px; }
    .metric-delta-positive { color: var(--success); }
    .metric-delta-negative { color: var(--danger); }
    .metric-delta-neutral  { color: var(--text-muted); }

    /* ── Progress Card Component ── */
    .progress-card {
        background: var(--card-bg); border-radius: 12px; padding: 1rem;
        border: 1px solid var(--card-border); box-shadow: var(--card-shadow);
        color: var(--text-primary);
    }
    .progress-header {
        display: flex; justify-content: space-between; margin-bottom: 8px;
    }
    .progress-label { font-size: 0.875rem; font-weight: 500; color: var(--text-secondary); }
    .progress-count { font-size: 0.875rem; font-weight: 600; color: var(--text-primary); }
    .progress-track {
        background: var(--neutral-200); border-radius: 4px;
        height: 8px; overflow: hidden;
    }
    .progress-fill {
        height: 100%; border-radius: 4px; transition: width 0.3s ease;
    }

    /* ── KPI Card ── */
    .kpi-card { border-radius: 16px; padding: 1.5rem; text-align: center; color: white; }
    .kpi-value { font-size: 2.5rem; font-weight: 700; margin-bottom: 4px; }
    .kpi-label { font-size: 0.875rem; opacity: 0.9; }
    .kpi-primary  { background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%); }
    .kpi-secondary { background: linear-gradient(135deg, #0891b2 0%, #06b6d4 100%); }
    .kpi-accent   { background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%); }
    .kpi-warning  { background: linear-gradient(135deg, #db2777 0%, #ec4899 100%); }

    /* ── Insight / Risk ── */
    .insight-card {
        background: var(--card-bg); border-radius: 12px; padding: 1rem;
        border-left: 4px solid #0f766e; margin-bottom: 1rem;
        color: var(--text-primary); box-shadow: var(--card-shadow);
    }
    .risk-warning {
        background: #fef3c7; border-radius: 8px;
        padding: 12px 16px; margin-bottom: 8px; color: #92400e;
    }
    .risk-item { padding: 12px 16px; border-radius: 8px; margin-bottom: 8px; }
    .risk-high   { background: #fee2e2; color: #991b1b; }
    .risk-medium { background: #fef3c7; color: #92400e; }
    .risk-low    { background: #d1fae5; color: #065f46; }
</style>
"""


def apply_all_styles() -> None:
    import streamlit as st

    st.markdown(ALL_STYLES, unsafe_allow_html=True)


def get_status_badge(status: str, label: str | None = None) -> str:
    labels: dict[str, str] = {
        "running": "运行中",
        "idle": "空闲",
        "maintenance": "维护中",
        "planned": "已计划",
        "completed": "已完成",
        "delayed": "延期",
    }
    display_label = label or labels.get(status, status)
    return f'<span class="status-badge status-{status}">{display_label}</span>'


def get_kpi_card(value: str, label: str, variant: str = "primary") -> str:
    return f"""
    <div class="kpi-card kpi-{variant}">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>
    """
