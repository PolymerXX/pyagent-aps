"""排程Agent - 执行排产优化"""

from typing import List, Optional
from pydantic import BaseModel

from aps.core.config import get_settings
from aps.models.order import Order
from aps.models.machine import ProductionLine
from aps.models.constraint import ProductionConstraints
from aps.models.schedule import ScheduleResult, TaskAssignment
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.engine.solver import APSSolver


class SchedulerAgent:
    """排程Agent - 执行排产优化"""

    def __init__(
        self,
        orders: List[Order],
        machines: List[ProductionLine],
        constraints: Optional[ProductionConstraints] = None,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.settings = get_settings()

    def run_optimization(
        self, params: Optional[OptimizationParams] = None
    ) -> ScheduleResult:
        """运行排产优化"""
        if params is None:
            params = OptimizationParams()

        solver = APSSolver(
            orders=self.orders,
            machines=self.machines,
            constraints=self.constraints,
            params=params,
        )

        result = solver.solve()
        return result

    def quick_schedule(
        self, strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> ScheduleResult:
        """快速排产（使用默认参数）"""
        params = OptimizationParams(strategy=strategy)
        return self.run_optimization(params)

    def add_order(self, order: Order) -> None:
        """添加订单"""
        self.orders.append(order)

    def remove_order(self, order_id: str) -> bool:
        """移除订单"""
        for i, order in enumerate(self.orders):
            if order.id == order_id:
                self.orders.pop(i)
                return True
        return False

    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
