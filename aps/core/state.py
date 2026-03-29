"""统一状态管理

MCP tools 和 Agent 系统共享的全局单例状态。
"""

from __future__ import annotations

import threading
from typing import Any, ClassVar

from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.order import Order
from aps.models.schedule import ScheduleResult


class APSState:
    """全局单例状态 — MCP 和 Agent 共享"""

    _instance: ClassVar[APSState | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._machines: dict[str, ProductionLine] = {}
        self._constraints: ProductionConstraints | None = None
        self._current_schedule: dict[str, Any] | None = None
        self._schedule_history: list[dict[str, Any]] = []
        self._internal_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> APSState:
        """获取单例实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = APSState()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（仅用于测试）"""
        with cls._lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def add_order(self, order: Order) -> None:
        with self._internal_lock:
            self._orders[order.id] = order

    def remove_order(self, order_id: str) -> bool:
        with self._internal_lock:
            if order_id in self._orders:
                del self._orders[order_id]
                return True
            return False

    def get_order(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)

    def get_orders_list(self) -> list[Order]:
        with self._internal_lock:
            return list(self._orders.values())

    def set_orders(self, orders: list[Order]) -> None:
        with self._internal_lock:
            self._orders = {o.id: o for o in orders}

    @property
    def orders(self) -> dict[str, Order]:
        return dict(self._orders)

    # ------------------------------------------------------------------
    # Machines
    # ------------------------------------------------------------------

    def add_machine(self, machine: ProductionLine) -> None:
        with self._internal_lock:
            self._machines[machine.id] = machine

    def remove_machine(self, machine_id: str) -> bool:
        with self._internal_lock:
            if machine_id in self._machines:
                del self._machines[machine_id]
                return True
            return False

    def get_machines_list(self) -> list[ProductionLine]:
        with self._internal_lock:
            return list(self._machines.values())

    def set_machines(self, machines: list[ProductionLine]) -> None:
        with self._internal_lock:
            self._machines = {m.id: m for m in machines}

    @property
    def machines(self) -> dict[str, ProductionLine]:
        return dict(self._machines)

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------

    def get_constraints(self) -> ProductionConstraints:
        if self._constraints is None:
            self._constraints = ProductionConstraints()
        return self._constraints

    def set_constraints(self, constraints: ProductionConstraints) -> None:
        self._constraints = constraints

    # ------------------------------------------------------------------
    # Schedule
    # ------------------------------------------------------------------

    def set_schedule(self, result: ScheduleResult, schedule_id: str) -> None:
        with self._internal_lock:
            result_dict = result.model_dump()
            result_dict["schedule_id"] = schedule_id
            self._current_schedule = result_dict
            self._schedule_history.append(result_dict)

    def get_current_schedule(self) -> dict[str, Any] | None:
        return self._current_schedule

    def get_schedule_by_id(self, schedule_id: str) -> dict[str, Any] | None:
        for schedule in self._schedule_history:
            if schedule.get("schedule_id") == schedule_id:
                return schedule
        return None

    @property
    def schedule_history(self) -> list[dict[str, Any]]:
        return list(self._schedule_history)

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def clear_all(self) -> None:
        with self._internal_lock:
            self._orders.clear()
            self._machines.clear()
            self._constraints = None
            self._current_schedule = None
            self._schedule_history.clear()
