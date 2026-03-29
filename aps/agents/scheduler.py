"""排程Agent - 执行排产优化"""



from aps.core.config import get_settings
from aps.engine.solver import APSSolver
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order
from aps.models.schedule import ScheduleResult


class SchedulerAgent:
    """排程Agent - 执行排产优化"""

    def __init__(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints | None = None,
    ):
        self.orders = orders
        self.machines = machines
        self.constraints = constraints or ProductionConstraints()
        self.settings = get_settings()

    def run_optimization(
        self, params: OptimizationParams | None = None
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
        from aps.core.state import APSState

        APSState.get_instance().add_order(order)

    def remove_order(self, order_id: str) -> bool:
        """移除订单"""
        for i, order in enumerate(self.orders):
            if order.id == order_id:
                self.orders.pop(i)
                from aps.core.state import APSState

                APSState.get_instance().remove_order(order_id)
                return True
        return False

    def get_order(self, order_id: str) -> Order | None:
        """获取订单"""
        for order in self.orders:
            if order.id == order_id:
                return order
        return None
