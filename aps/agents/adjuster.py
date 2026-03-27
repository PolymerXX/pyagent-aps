"""调整Agent - 处理实时变更"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.core.config import get_settings
from aps.agents.base import create_model_settings
from aps.models.order import Order
from aps.models.machine import ProductionLine
from aps.models.schedule import ScheduleResult
from aps.models.optimization import OptimizationParams
from aps.engine.solver import APSSolver
from aps.agents.validator import ValidationResult


class AdjustmentType(str, Enum):
    NEW_ORDER = "new_order"
    MACHINE_DOWN = "machine_down"
    ORDER_CHANGE = "order_change"
    PRIORITY_CHANGE = "priority_change"


class Adjustment(BaseModel):
    """调整动作"""

    action_type: AdjustmentType = Field(..., description="调整类型")
    affected_orders: List[str] = Field(
        default_factory=list, description="受影响的订单ID"
    )
    reason: str = Field(..., description="调整原因")
    new_schedule_id: Optional[str] = Field(None, description="新排程ID")
    changes: Dict[str, Any] = Field(default_factory=dict, description="变更详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class AdjusterAgent:
    """调整Agent"""

    def __init__(self):
        self.config = get_settings()
        self.settings = create_model_settings(temperature=0.3)

        self.agent = Agent(
            self.config.default_model,
            model_settings=self.settings,
            instructions=self._get_instructions(),
            output_type=Adjustment,
        )

    def _get_instructions(self) -> str:
        return """你是APS系统的方案调整Agent。

你的职责是处理实时变更并生成调整后的排程方案。

**处理场景**：
1. 新订单接入 - 增量添加
2. 设备故障 - 临时排除机器
3. 订单变更 - 更新属性

**调整策略**：
- 增量调整: 仅处理变更部分
- 局部调整: 最小化影响
- 优先级调整: 根据新情况重排
"""

    async def handle_new_order(
        self,
        order: Order,
        machines: List[ProductionLine],
        existing_result: Optional[ScheduleResult] = None,
    ) -> Adjustment:
        """处理新订单"""
        params = OptimizationParams()

        orders = [order]
        if existing_result:
            orders = list(existing_result.assignments) + [order]

        result = await self._run_solver(orders, machines, params)

        adjustment = Adjustment(
            action_type=AdjustmentType.NEW_ORDER,
            affected_orders=[order.id],
            reason=f"新订单 {order.id} 加入",
            new_schedule_id=result.get("schedule_id"),
            changes={"added_order": order.id},
            timestamp=datetime.now(),
        )
        return adjustment

    async def handle_machine_down(
        self, machine_id: str, orders: List[Order], machines: List[ProductionLine]
    ) -> Adjustment:
        """处理机器故障"""
        available_machines = [m for m in machines if m.id != machine_id]

        params = OptimizationParams()
        result = await self._run_solver(orders, available_machines, params)

        affected = [a.order_id for a in result.get("assignments", [])]

        adjustment = Adjustment(
            action_type=AdjustmentType.MACHINE_DOWN,
            affected_orders=affected,
            reason=f"机器 {machine_id} 故障",
            new_schedule_id=result.get("schedule_id"),
            changes={"disabled_machine": machine_id},
            timestamp=datetime.now(),
        )
        return adjustment

    async def handle_order_change(
        self,
        order_id: str,
        changes: dict,
        orders: List[Order],
        machines: List[ProductionLine],
    ) -> Adjustment:
        """处理订单变更"""
        params = OptimizationParams()
        result = await self._run_solver(orders, machines, params)

        adjustment = Adjustment(
            action_type=AdjustmentType.ORDER_CHANGE,
            affected_orders=[order_id],
            reason=f"订单 {order_id} 属性变更",
            new_schedule_id=result.get("schedule_id"),
            changes=changes,
            timestamp=datetime.now(),
        )
        return adjustment

    async def _run_solver(
        self,
        orders: List[Order],
        machines: List[ProductionLine],
        params: OptimizationParams,
    ) -> dict:
        """运行求解器"""
        solver = APSSolver(
            orders=orders,
            machines=machines,
            params=params,
        )
        result = solver.solve()

        schedule_id = f"adj-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        result_dict = result.model_dump()
        result_dict["schedule_id"] = schedule_id

        return result_dict

    async def analyze_and_adjust(
        self,
        result: ScheduleResult,
        validation: ValidationResult,
        orders: List[Order],
        machines: List[ProductionLine],
    ) -> Optional[Adjustment]:
        """分析验证结果并调整"""
        if validation.is_valid:
            return None

        for violation in validation.constraint_violations:
            if violation.type == "due_date":
                return await self.handle_order_change(
                    order_id=violation.order_id or "",
                    changes={"priority": "high"},
                    orders=orders,
                    machines=machines,
                )

        return None
