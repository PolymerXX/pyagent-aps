"""统一状态管理模块

集中管理 APS 系统的 session_state，确保数据在页面间同步
"""

# ruff: noqa: E402

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_aps_parent = _project_root.parent
for _p in (_project_root, _aps_parent):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import streamlit as st


def get_sample_orders() -> list:
    from aps.models.order import Order, Product, ProductType

    return [
        Order(
            id="O-1001",
            product=Product(
                id="P001",
                name="可乐 500ml",
                product_type=ProductType.BEVERAGE,
                production_rate=2000,
                unit_profit=0.5,
            ),
            quantity=10000,
            due_date=24,
            priority=8,
            min_start_time=0,
        ),
        Order(
            id="O-1002",
            product=Product(
                id="P002",
                name="橙汁 1L",
                product_type=ProductType.JUICE,
                production_rate=1500,
                unit_profit=0.8,
            ),
            quantity=5000,
            due_date=36,
            priority=6,
            min_start_time=0,
        ),
        Order(
            id="O-1003",
            product=Product(
                id="P003",
                name="纯牛奶 250ml",
                product_type=ProductType.DAIRY,
                production_rate=1800,
                unit_profit=0.6,
            ),
            quantity=8000,
            due_date=48,
            priority=5,
            min_start_time=0,
        ),
        Order(
            id="O-1004",
            product=Product(
                id="P004",
                name="矿泉水 550ml",
                product_type=ProductType.BEVERAGE,
                production_rate=3000,
                unit_profit=0.3,
            ),
            quantity=15000,
            due_date=72,
            priority=3,
            min_start_time=0,
        ),
        Order(
            id="O-1005",
            product=Product(
                id="P005",
                name="苹果汁 500ml",
                product_type=ProductType.JUICE,
                production_rate=1600,
                unit_profit=0.7,
            ),
            quantity=6000,
            due_date=60,
            priority=4,
            min_start_time=0,
        ),
    ]


def get_sample_machines() -> list:
    from aps.models.machine import MachineStatus, ProductionLine
    from aps.models.order import ProductType

    return [
        ProductionLine(
            id="LINE-A",
            name="生产线 A - 饮料专线",
            supported_product_types=[ProductType.BEVERAGE, ProductType.JUICE],
            capacity_per_hour=2000,
            setup_time_hours=0.5,
            status=MachineStatus(
                machine_id="LINE-A",
                status="running",
                current_task="可乐 500ml",
                completed_tasks=12,
                uptime_hours=156.5,
            ),
        ),
        ProductionLine(
            id="LINE-B",
            name="生产线 B - 乳制品专线",
            supported_product_types=[ProductType.DAIRY, ProductType.BEVERAGE],
            capacity_per_hour=1800,
            setup_time_hours=1.0,
            status=MachineStatus(
                machine_id="LINE-B",
                status="running",
                current_task="纯牛奶 250ml",
                completed_tasks=8,
                uptime_hours=142.0,
            ),
        ),
        ProductionLine(
            id="LINE-C",
            name="生产线 C - 通用线",
            supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY, ProductType.JUICE],
            capacity_per_hour=1500,
            setup_time_hours=1.5,
            status=MachineStatus(
                machine_id="LINE-C",
                status="idle",
                current_task=None,
                completed_tasks=5,
                uptime_hours=89.0,
            ),
        ),
        ProductionLine(
            id="LINE-D",
            name="生产线 D - 高速线",
            supported_product_types=[ProductType.BEVERAGE],
            capacity_per_hour=3500,
            setup_time_hours=0.3,
            status=MachineStatus(
                machine_id="LINE-D",
                status="maintenance",
                current_task=None,
                completed_tasks=15,
                uptime_hours=200.0,
                last_maintenance="2024-01-15",
            ),
        ),
    ]


class AppState:
    """应用状态管理类"""

    ORDERS_KEY = "aps_orders"
    MACHINES_KEY = "aps_machines"
    CONSTRAINTS_KEY = "aps_constraints"
    SCHEDULE_RESULT_KEY = "aps_schedule_result"
    CHANGEOVER_RULES_KEY = "aps_changeover_rules"
    AGENT_TRACE_KEY = "aps_agent_trace"

    @classmethod
    def init_state(cls) -> None:
        from aps.models.constraint import DEFAULT_CHANGEOVER_RULES, ProductionConstraints

        if cls.ORDERS_KEY not in st.session_state:
            st.session_state[cls.ORDERS_KEY] = get_sample_orders()

        if cls.MACHINES_KEY not in st.session_state:
            st.session_state[cls.MACHINES_KEY] = get_sample_machines()

        if cls.CONSTRAINTS_KEY not in st.session_state:
            st.session_state[cls.CONSTRAINTS_KEY] = ProductionConstraints()

        if cls.SCHEDULE_RESULT_KEY not in st.session_state:
            st.session_state[cls.SCHEDULE_RESULT_KEY] = None

        if cls.CHANGEOVER_RULES_KEY not in st.session_state:
            st.session_state[cls.CHANGEOVER_RULES_KEY] = DEFAULT_CHANGEOVER_RULES.copy()

        if cls.AGENT_TRACE_KEY not in st.session_state:
            st.session_state[cls.AGENT_TRACE_KEY] = None

    @classmethod
    def get_orders(cls) -> list:
        cls.init_state()
        return st.session_state[cls.ORDERS_KEY]

    @classmethod
    def set_orders(cls, orders: list) -> None:
        st.session_state[cls.ORDERS_KEY] = orders

    @classmethod
    def add_order(cls, order) -> None:
        cls.init_state()
        st.session_state[cls.ORDERS_KEY].append(order)

    @classmethod
    def add_orders(cls, orders: list) -> int:
        cls.init_state()
        existing_ids = {o.id for o in st.session_state[cls.ORDERS_KEY]}
        added = 0
        for order in orders:
            if order.id not in existing_ids:
                st.session_state[cls.ORDERS_KEY].append(order)
                added += 1
        return added

    @classmethod
    def remove_order(cls, order_id: str) -> bool:
        cls.init_state()
        orders = st.session_state[cls.ORDERS_KEY]
        for i, o in enumerate(orders):
            if o.id == order_id:
                orders.pop(i)
                return True
        return False

    @classmethod
    def update_order(cls, order_id: str, updated_order) -> bool:
        cls.init_state()
        orders = st.session_state[cls.ORDERS_KEY]
        for i, o in enumerate(orders):
            if o.id == order_id:
                orders[i] = updated_order
                return True
        return False

    @classmethod
    def get_order_by_id(cls, order_id: str):
        cls.init_state()
        for o in st.session_state[cls.ORDERS_KEY]:
            if o.id == order_id:
                return o
        return None

    @classmethod
    def get_machines(cls) -> list:
        cls.init_state()
        return st.session_state[cls.MACHINES_KEY]

    @classmethod
    def set_machines(cls, machines: list) -> None:
        st.session_state[cls.MACHINES_KEY] = machines

    @classmethod
    def update_machine_status(cls, machine_id: str, status: str) -> bool:
        cls.init_state()
        machines = st.session_state[cls.MACHINES_KEY]
        for m in machines:
            if m.id == machine_id:
                m.status.status = status
                if status != "running":
                    m.status.current_task = None
                return True
        return False

    @classmethod
    def get_machine_by_id(cls, machine_id: str):
        cls.init_state()
        for m in st.session_state[cls.MACHINES_KEY]:
            if m.id == machine_id:
                return m
        return None

    @classmethod
    def get_constraints(cls):
        cls.init_state()
        return st.session_state[cls.CONSTRAINTS_KEY]

    @classmethod
    def set_constraints(cls, constraints) -> None:
        st.session_state[cls.CONSTRAINTS_KEY] = constraints

    @classmethod
    def get_schedule_result(cls):
        cls.init_state()
        return st.session_state[cls.SCHEDULE_RESULT_KEY]

    @classmethod
    def set_schedule_result(cls, result) -> None:
        st.session_state[cls.SCHEDULE_RESULT_KEY] = result

    @classmethod
    def get_agent_trace(cls) -> dict | None:
        cls.init_state()
        return st.session_state.get(cls.AGENT_TRACE_KEY)

    @classmethod
    def set_agent_trace(cls, trace: dict | None) -> None:
        cls.init_state()
        st.session_state[cls.AGENT_TRACE_KEY] = trace

    @classmethod
    def clear_agent_trace(cls) -> None:
        cls.init_state()
        st.session_state[cls.AGENT_TRACE_KEY] = None

    @classmethod
    def get_changeover_rules(cls):
        cls.init_state()
        return st.session_state[cls.CHANGEOVER_RULES_KEY]

    @classmethod
    def set_changeover_rules(cls, rules) -> None:
        st.session_state[cls.CHANGEOVER_RULES_KEY] = rules

    @classmethod
    def reset_all(cls) -> None:
        from aps.models.constraint import DEFAULT_CHANGEOVER_RULES, ProductionConstraints

        st.session_state[cls.ORDERS_KEY] = get_sample_orders()
        st.session_state[cls.MACHINES_KEY] = get_sample_machines()
        st.session_state[cls.CONSTRAINTS_KEY] = ProductionConstraints()
        st.session_state[cls.SCHEDULE_RESULT_KEY] = None
        st.session_state[cls.CHANGEOVER_RULES_KEY] = DEFAULT_CHANGEOVER_RULES.copy()
        st.session_state[cls.AGENT_TRACE_KEY] = None
