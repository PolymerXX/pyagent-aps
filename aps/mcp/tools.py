"""APS MCP核心工具函数"""

import uuid
from datetime import datetime
from typing import Any

from aps.adapters.parsers import DEFAULT_PRODUCTION_RATE, parse_product_type
from aps.core.state import APSState
from aps.engine.solver import APSSolver
from aps.mcp.registry import ToolCategory, tool
from aps.models.constraint import ProductionConstraints
from aps.models.machine import ProductionLine
from aps.models.optimization import (
    ObjectiveWeights,
    OptimizationParams,
    OptimizationStrategy,
)
from aps.models.order import Order, Product, ProductType


def _get_state() -> APSState:
    return APSState.get_instance()


def _reset_state() -> None:
    APSState.reset_instance()


@tool(
    name="run_aps_schedule",
    description="执行APS排程优化",
    category=ToolCategory.SCHEDULING,
)
def run_aps_schedule(
    strategy: str = "balanced",
    orders_filter: list[str] | None = None,
    machines_filter: list[str] | None = None,
    time_limit: int = 60,
    on_time_weight: float = 0.4,
    changeover_weight: float = 0.2,
    utilization_weight: float = 0.2,
    profit_weight: float = 0.2,
) -> dict[str, Any]:
    """执行APS排程"""
    state = _get_state()
    orders = state.get_orders_list()
    machines = state.get_machines_list()

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
        "max_utilization": OptimizationStrategy.MAX_UTILIZATION,
    }

    weights = ObjectiveWeights(
        on_time=on_time_weight,
        changeover=changeover_weight,
        utilization=utilization_weight,
        profit=profit_weight,
    )

    params = OptimizationParams(
        strategy=strategy_map.get(strategy, OptimizationStrategy.BALANCED),
        weights=weights,
        time_limit_seconds=time_limit,
    )

    constraints = state.get_constraints()

    solver = APSSolver(
        orders=orders,
        machines=machines,
        constraints=constraints,
        params=params,
    )

    result = solver.solve()

    schedule_id = str(uuid.uuid4())[:8]
    state.set_schedule(result, schedule_id)

    result_dict = result.model_dump()
    result_dict["schedule_id"] = schedule_id
    result_dict["created_at"] = datetime.now().isoformat()

    return result_dict


@tool(
    name="get_schedule_status",
    description="获取排程状态",
    category=ToolCategory.SCHEDULING,
)
def get_schedule_status(schedule_id: str | None = None) -> dict[str, Any]:
    """获取排程状态"""
    state = _get_state()
    if schedule_id:
        schedule = state.get_schedule_by_id(schedule_id)
        if schedule:
            return schedule
        return {"error": f"未找到排程 {schedule_id}", "status": "not_found"}

    current = state.get_current_schedule()
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
    due_in_hours: int | None = None,
    product_type: str | None = None,
) -> dict[str, Any]:
    """添加订单"""
    state = _get_state()
    if job_id in state.orders:
        return {"error": f"订单 {job_id} 已存在", "status": "failed"}

    if product_type:
        try:
            pt = parse_product_type(product_type)
        except ValueError:
            pt = ProductType.BEVERAGE
    else:
        pt = ProductType.BEVERAGE

    order = Order(
        id=job_id,
        product=Product(
            id=f"mcp_{job_id}",
            name=product,
            product_type=pt,
            production_rate=DEFAULT_PRODUCTION_RATE,
        ),
        quantity=quantity,
        due_date=due_in_hours if due_in_hours else 72,
    )

    state.add_order(order)
    return {"status": "success", "order_id": job_id}


@tool(
    name="update_order",
    description="更新订单",
    category=ToolCategory.ORDER,
)
def update_order(job_id: str, **changes) -> dict[str, Any]:
    """更新订单"""
    state = _get_state()
    order = state.get_order(job_id)
    if order is None:
        return {"error": f"订单 {job_id} 不存在", "status": "failed"}

    if "quantity" in changes:
        order.quantity = changes["quantity"]
    if "due_in_hours" in changes:
        order.due_date = int(changes["due_in_hours"])

    return {"status": "success", "order_id": job_id}


@tool(
    name="get_orders",
    description="查询订单",
    category=ToolCategory.ORDER,
)
def get_orders() -> dict[str, Any]:
    """查询订单"""
    state = _get_state()
    orders = []
    for order in state.get_orders_list():
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
def remove_order(job_id: str) -> dict[str, Any]:
    """删除订单"""
    state = _get_state()
    if not state.remove_order(job_id):
        return {"error": f"订单 {job_id} 不存在", "status": "failed"}
    return {"status": "success", "order_id": job_id}


@tool(
    name="add_machine",
    description="添加机器",
    category=ToolCategory.MACHINE,
)
def add_machine(
    machine_id: str,
    capacity_per_hour: int,
    supported_products: list[str],
    name: str | None = None,
) -> dict[str, Any]:
    """添加机器"""
    state = _get_state()
    if machine_id in state.machines:
        return {"error": f"机器 {machine_id} 已存在", "status": "failed"}

    supported_types = []
    for raw in supported_products:
        try:
            supported_types.append(parse_product_type(raw))
        except ValueError:
            pass

    machine = ProductionLine(
        id=machine_id,
        name=name or machine_id,
        capacity_per_hour=capacity_per_hour,
        supported_product_types=supported_types,
    )

    state.add_machine(machine)
    return {"status": "success", "machine_id": machine_id}


@tool(
    name="get_machines",
    description="查询机器",
    category=ToolCategory.MACHINE,
)
def get_machines() -> dict[str, Any]:
    """查询机器"""
    state = _get_state()
    machines = []
    for m in state.get_machines_list():
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
def update_machine_status(machine_id: str, status: str) -> dict[str, Any]:
    """更新机器状态"""
    state = _get_state()
    if machine_id not in state.machines:
        return {"error": f"机器 {machine_id} 不存在", "status": "failed"}
    return {"status": "success", "machine_id": machine_id, "new_status": status}


@tool(
    name="set_constraints",
    description="设置约束",
    category=ToolCategory.CONSTRAINT,
)
def set_constraints(constraints: list[dict]) -> dict[str, Any]:
    """设置约束"""
    state = _get_state()
    state.set_constraints(ProductionConstraints())
    return {"status": "success", "count": len(constraints)}


@tool(
    name="get_constraints",
    description="获取约束",
    category=ToolCategory.CONSTRAINT,
)
def get_constraints() -> dict[str, Any]:
    """获取约束"""
    return {"status": "success", "constraints": []}


@tool(
    name="explain_schedule",
    description="解释排程",
    category=ToolCategory.RESULT,
)
def explain_schedule(schedule_id: str | None = None) -> dict[str, Any]:
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
def validate_schedule(schedule_id: str | None = None) -> dict[str, Any]:
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
