"""实时调整处理器"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aps.engine.solver import APSSolver
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams
from aps.models.order import Order
from aps.models.schedule import ScheduleResult


class AdjustmentEvent(BaseModel):
    """调整事件"""

    event_type: str
    event_time: datetime = Field(default_factory=datetime.now)
    affected_orders: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class RealtimeAdjuster:
    """实时调整处理器"""

    def __init__(self, orders: list[Order], machines: list[ProductionLine]):
        self.orders = orders
        self.machines = machines
        self._event_history: list[AdjustmentEvent] = []

    def handle_new_order(self, order: Order) -> AdjustmentEvent:
        """处理新订单"""
        self.orders.append(order)

        event = AdjustmentEvent(
            event_type="new_order",
            affected_orders=[order.id],
            details={"order_id": order.id, "quantity": order.quantity},
        )

        self._event_history.append(event)
        return event

    def handle_machine_down(self, machine_id: str) -> AdjustmentEvent:
        """处理机器故障"""
        affected = []
        for m in self.machines:
            if m.id == machine_id:
                m.status = "down"

        event = AdjustmentEvent(
            event_type="machine_down",
            affected_orders=affected,
            details={"machine_id": machine_id},
        )

        self._event_history.append(event)
        return event

    def handle_order_change(
        self, order_id: str, changes: dict[str, Any]
    ) -> AdjustmentEvent:
        """处理订单变更"""
        for order in self.orders:
            if order.id == order_id:
                if "quantity" in changes:
                    order.quantity = changes["quantity"]
                if "due_date" in changes:
                    order.due_date = changes["due_date"]
                break

        event = AdjustmentEvent(
            event_type="order_change", affected_orders=[order_id], details=changes
        )

        self._event_history.append(event)
        return event

    def reschedule(self, params: OptimizationParams | None = None) -> ScheduleResult:
        """重新排程"""
        solver = APSSolver(
            orders=self.orders,
            machines=self.machines,
            params=params or OptimizationParams(),
        )
        return solver.solve()
