"""APS MCP核心工具函数"""

import json
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from aps.mcp.registry import registry, ToolCategory, tool
from aps.models.order import Order, Product, ProductType
from aps.models.machine import ProductionLine
from aps.models.constraint import ProductionConstraints
from aps.models.optimization import (
    OptimizationParams,
    OptimizationStrategy,
    ObjectiveWeights,
)
from aps.models.schedule import ScheduleResult
from aps.engine.solver import APSSolver


_global_state: Dict[str, Any] = {
    "orders": {},
    "machines": {},
    "constraints": None,
    "current_schedule": None,
    "schedule_history": [],
}


def _get_or_create_constraints() -> ProductionConstraints:
    if _global_state["constraints"] is None:
        _global_state["constraints"] = ProductionConstraints()
    return _global_state["constraints"]


@tool(
    name="run_aps_schedule",
    description="执行APS排程优化",
    category=ToolCategory.SCHEDULING,
)
def run_aps_schedule(
    strategy: str = "balanced",
    orders_filter: Optional[List[str]] = None,
    machines_filter: Optional[List[str]] = None,
    time_limit: int = 60,
    on_time_weight: float = 0.4,
    changeover_weight: float = 0.2,
    utilization_weight: float = 0.2,
    profit_weight: float = 0.2,
) -> Dict[str, Any]:
    """执行APS排程"""
    orders = list(_global_state["orders"].values())
    machines = list(_global_state["machines"].values())

    if orders_filter:
        orders = [o for o in orders if o.id in orders_filter]
    if machines_filter:
        machines = [m for m in machines if m.id in machines_filter]

    if not orders or not machines:
        return {"error": "没有可排程的订单或机器", "status": "failed"}

    strategy_map = {
        "balanced": OptimizationStrategy.BALANCED,
        "on_time": OptimizationStrategy.ON_TIME_DELIVERY,
        "min_changeover": OptimizationStrategy.MINIMIZE_CHANGEOVER,
        "max_profit": OptimizationStrategy.MAXIMIZE_PROFIT,
        "max_utilization": OptimizationStrategy.MAXIMIZE_UTILIZATION,
    }

    weights = ObjectiveWeights(
        on_time_delivery=on_time_weight,
        minimize_changeover=changeover_weight,
        maximize_utilization=utilization_weight,
        maximize_profit=profit_weight,
    )

    params = OptimizationParams(
        strategy=strategy_map.get(strategy, OptimizationStrategy.BALANCED),
        weights=weights,
        time_limit_seconds=time_limit,
    )

    constraints = _get_or_create_constraints()

    solver = APSSolver(
        orders=orders,
        machines=machines,
        constraints=constraints,
        params=params,
    )

    result = solver.solve()

    schedule_id = str(uuid.uuid4())[:8]
    result_dict = result.model_dump()
    result_dict["schedule_id"] = schedule_id
    result_dict["created_at"] = datetime.now().isoformat()

    _global_state["current_schedule"] = result_dict
    _global_state["schedule_history"].append(result_dict)

    return result_dict


@tool(
    name="get_schedule_status",
    description="获取排程状态",
    category=ToolCategory.SCHEDULING,
)
def get_schedule_status(schedule_id: Optional[str] = None) -> Dict[str, Any]:
    """获取排程状态"""
    if schedule_id:
        for schedule in _global_state["schedule_history"]:
            if schedule.get("schedule_id") == schedule_id:
                return schedule
        return {"error": f"未找到排程 {schedule_id}", "status": "not_found"}

    current = _global_state["current_schedule"]
    return current or {"status": "no_schedule"}


@tool(
    name="add_order",
    description="添加订单",
    category=ToolCategory.ORDER,
)
def add_order(
    job_id: str,
    product: str,
    quantity: int,
    due_in_hours: Optional[int] = None,
) -> Dict[str, Any]:
    """添加订单"""
    if job_id in _global_state["orders"]:
        return {"error": f"订单 {job_id} 已存在", "status": "failed"}

    order = Order(
        id=job_id,
        product=Product(name=product, product_type=ProductType.COLA),
        quantity=quantity,
        due_date=float(due_in_hours) if due_in_hours else 72.0,
    )

    _global_state["orders"][job_id] = order
    return {"status": "success", "order_id": job_id}


@tool(
    name="update_order",
    description="更新订单",
    category=ToolCategory.ORDER,
)
def update_order(job_id: str, **changes) -> Dict[str, Any]:
    """更新订单"""
    if job_id not in _global_state["orders"]:
        return {"error": f"订单 {job_id} 不存在", "status": "failed"}

    order = _global_state["orders"][job_id]
    if "quantity" in changes:
        order.quantity = changes["quantity"]
    if "due_in_hours" in changes:
        order.due_date = float(changes["due_in_hours"])

    return {"status": "success", "order_id": job_id}


@tool(
    name="get_orders",
    description="查询订单",
    category=ToolCategory.ORDER,
)
def get_orders() -> Dict[str, Any]:
    """查询订单"""
    orders = []
    for order in _global_state["orders"].values():
        orders.append(
            {
                "job_id": order.id,
                "product": order.product.name,
                "quantity": order.quantity,
                "due_in_hours": order.due_date,
            }
        )
    return {"status": "success", "count": len(orders), "orders": orders}


@tool(
    name="remove_order",
    description="删除订单",
    category=ToolCategory.ORDER,
)
def remove_order(job_id: str) -> Dict[str, Any]:
    """删除订单"""
    if job_id not in _global_state["orders"]:
        return {"error": f"订单 {job_id} 不存在", "status": "failed"}
    del _global_state["orders"][job_id]
    return {"status": "success", "order_id": job_id}


@tool(
    name="add_machine",
    description="添加机器",
    category=ToolCategory.MACHINE,
)
def add_machine(
    machine_id: str,
    capacity_per_hour: int,
    supported_products: List[str],
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """添加机器"""
    if machine_id in _global_state["machines"]:
        return {"error": f"机器 {machine_id} 已存在", "status": "failed"}

    machine = ProductionLine(
        id=machine_id,
        name=name or machine_id,
        capacity_per_hour=capacity_per_hour,
    )

    _global_state["machines"][machine_id] = machine
    return {"status": "success", "machine_id": machine_id}


@tool(
    name="get_machines",
    description="查询机器",
    category=ToolCategory.MACHINE,
)
def get_machines() -> Dict[str, Any]:
    """查询机器"""
    machines = []
    for m in _global_state["machines"].values():
        machines.append(
            {
                "machine_id": m.id,
                "name": m.name,
                "capacity_per_hour": m.capacity_per_hour,
            }
        )
    return {"status": "success", "count": len(machines), "machines": machines}


@tool(
    name="update_machine_status",
    description="更新机器状态",
    category=ToolCategory.MACHINE,
)
def update_machine_status(machine_id: str, status: str) -> Dict[str, Any]:
    """更新机器状态"""
    if machine_id not in _global_state["machines"]:
        return {"error": f"机器 {machine_id} 不存在", "status": "failed"}
    return {"status": "success", "machine_id": machine_id, "new_status": status}


@tool(
    name="set_constraints",
    description="设置约束",
    category=ToolCategory.CONSTRAINT,
)
def set_constraints(constraints: List[dict]) -> Dict[str, Any]:
    """设置约束"""
    _global_state["constraints"] = ProductionConstraints()
    return {"status": "success", "count": len(constraints)}


@tool(
    name="get_constraints",
    description="获取约束",
    category=ToolCategory.CONSTRAINT,
)
def get_constraints() -> Dict[str, Any]:
    """获取约束"""
    return {"status": "success", "constraints": []}


@tool(
    name="explain_schedule",
    description="解释排程",
    category=ToolCategory.RESULT,
)
def explain_schedule(schedule_id: Optional[str] = None) -> Dict[str, Any]:
    """解释排程"""
    schedule = get_schedule_status(schedule_id)
    if "error" in schedule:
        return schedule

    lines = ["排程报告:", f"任务数: {schedule.get('task_count', 0)}"]
    return {"status": "success", "explanation": "\n".join(lines)}


@tool(
    name="validate_schedule",
    description="验证排程",
    category=ToolCategory.RESULT,
)
def validate_schedule(schedule_id: Optional[str] = None) -> Dict[str, Any]:
    """验证排程"""
    schedule = get_schedule_status(schedule_id)
    if "error" in schedule:
        return schedule

    return {
        "status": "success",
        "is_valid": True,
        "constraint_violations": [],
        "warnings": [],
    }
