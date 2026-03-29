"""APS MCP Server

独立的MCP服务入口，暴露APS系统所有工具
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mcp_stdio_patch

mcp_stdio_patch.patch()

from mcp.server.fastmcp import FastMCP
from datetime import datetime

from aps.mcp import tools

app = FastMCP(
    name="APS MCP Server",
    port=8800,
)


@app.tool()
def run_aps_schedule(
    strategy: str = "balanced",
    orders_filter: str = "",
    machines_filter: str = "",
    time_limit: int = 60,
    on_time_weight: float = 0.4,
    changeover_weight: float = 0.2,
    utilization_weight: float = 0.2,
    profit_weight: float = 0.2,
) -> str:
    """
    执行APS排程优化，根据策略和权重参数生成最优生产排程。

    Args:
        strategy: 优化策略 (balanced/on_time/min_changeover/max_profit/max_utilization)
        orders_filter: 订单ID过滤列表，逗号分隔（可选）
        machines_filter: 机器ID过滤列表，逗号分隔（可选）
        time_limit: 求解时间限制（秒）
        on_time_weight: 准时交付权重
        changeover_weight: 最小换产权重
        utilization_weight: 设备利用率权重
        profit_weight: 利润权重

    Returns:
        排程结果JSON字符串
    """
    import json

    orders_list = [x.strip() for x in orders_filter.split(",") if x.strip()] or None
    machines_list = [x.strip() for x in machines_filter.split(",") if x.strip()] or None

    result = tools.run_aps_schedule(
        strategy=strategy,
        orders_filter=orders_list,
        machines_filter=machines_list,
        time_limit=time_limit,
        on_time_weight=on_time_weight,
        changeover_weight=changeover_weight,
        utilization_weight=utilization_weight,
        profit_weight=profit_weight,
    )
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def get_schedule_status(schedule_id: str = "") -> str:
    """
    获取指定排程的状态信息。

    Args:
        schedule_id: 排程ID（可选，不提供则返回当前排程）

    Returns:
        排程状态JSON字符串
    """
    import json

    sid = schedule_id if schedule_id else None
    result = tools.get_schedule_status(sid)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def add_order(
    job_id: str,
    product: str,
    quantity: int,
    due_in_hours: int = 0,
    profit_priority: int = 50,
    allowed_machines: str = "",
) -> str:
    """
    添加新订单到排程系统。

    Args:
        job_id: 订单ID
        product: 产品名称 (cola/milk/orange_juice/water)
        quantity: 订单数量
        due_in_hours: 截止时间（小时），0表示无截止
        profit_priority: 利润优先级 (0-100)
        allowed_machines: 允许的机器ID列表，逗号分隔

    Returns:
        添加结果JSON字符串
    """
    import json

    machines_list = [
        x.strip() for x in allowed_machines.split(",") if x.strip()
    ] or None
    due = due_in_hours if due_in_hours > 0 else None
    priority = profit_priority if profit_priority > 0 else None

    result = tools.add_order(
        job_id=job_id,
        product=product,
        quantity=quantity,
        due_in_hours=due,
        profit_priority=priority,
        allowed_machines=machines_list,
    )
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def update_order(job_id: str, changes: str) -> str:
    """
    更新订单属性。

    Args:
        job_id: 订单ID
        changes: 要更新的属性，JSON格式字符串

    Returns:
        更新结果JSON字符串
    """
    import json

    try:
        changes_dict = json.loads(changes) if changes else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "无效的JSON格式", "status": "failed"})

    result = tools.update_order(job_id=job_id, **changes_dict)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def get_orders(filter_json: str = "") -> str:
    """
    查询订单列表。

    Args:
        filter_json: 过滤条件，JSON格式字符串（可选）

    Returns:
        订单列表JSON字符串
    """
    import json

    try:
        filter_dict = json.loads(filter_json) if filter_json else None
    except json.JSONDecodeError:
        filter_dict = None

    result = tools.get_orders(filter=filter_dict)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def remove_order(job_id: str) -> str:
    """
    删除订单。

    Args:
        job_id: 订单ID

    Returns:
        删除结果JSON字符串
    """
    import json

    result = tools.remove_order(job_id=job_id)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def add_machine(
    machine_id: str,
    capacity_per_hour: int,
    supported_products: str,
    name: str = "",
) -> str:
    """
    添加新机器到排程系统。

    Args:
        machine_id: 机器ID
        capacity_per_hour: 每小时产能
        supported_products: 支持的产品类型，逗号分隔 (cola/milk/orange_juice/water)
        name: 机器名称（可选）

    Returns:
        添加结果JSON字符串
    """
    import json

    products_list = [x.strip() for x in supported_products.split(",") if x.strip()]
    machine_name = name if name else None

    result = tools.add_machine(
        machine_id=machine_id,
        capacity_per_hour=capacity_per_hour,
        supported_products=products_list,
        name=machine_name,
    )
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def get_machines(status: str = "") -> str:
    """
    查询机器列表。

    Args:
        status: 状态过滤（可选）

    Returns:
        机器列表JSON字符串
    """
    import json

    status_filter = status if status else None
    result = tools.get_machines(status=status_filter)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def update_machine_status(machine_id: str, status: str) -> str:
    """
    更新机器状态。

    Args:
        machine_id: 机器ID
        status: 新状态 (active/maintenance/down)

    Returns:
        更新结果JSON字符串
    """
    import json

    result = tools.update_machine_status(machine_id=machine_id, status=status)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def set_constraints(constraints_json: str) -> str:
    """
    设置生产约束。

    Args:
        constraints_json: 约束列表，JSON格式字符串

    Returns:
        设置结果JSON字符串
    """
    import json

    try:
        constraints_list = json.loads(constraints_json) if constraints_json else []
    except json.JSONDecodeError:
        return json.dumps({"error": "无效的JSON格式", "status": "failed"})

    result = tools.set_constraints(constraints=constraints_list)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def get_constraints() -> str:
    """
    获取当前约束配置。

    Returns:
        约束配置JSON字符串
    """
    import json

    result = tools.get_constraints()
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def explain_schedule(schedule_id: str = "", format: str = "text") -> str:
    """
    生成排程解释报告。

    Args:
        schedule_id: 排程ID（可选）
        format: 输出格式 (text/json)

    Returns:
        解释报告JSON字符串
    """
    import json

    sid = schedule_id if schedule_id else None
    result = tools.explain_schedule(schedule_id=sid, format=format)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def validate_schedule(schedule_id: str = "") -> str:
    """
    验证排程可行性（约束检查+历史对比）。

    Args:
        schedule_id: 排程ID（可选）

    Returns:
        验证结果JSON字符串
    """
    import json

    sid = schedule_id if schedule_id else None
    result = tools.validate_schedule(schedule_id=sid)
    return json.dumps(result, ensure_ascii=False, default=str)


@app.tool()
def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.tool()
def init_demo_data() -> str:
    """
    初始化演示数据（订单和机器）。
    用于快速测试排程功能。

    Returns:
        初始化结果JSON字符串
    """
    import json

    tools.add_order(
        job_id="O-1001",
        product="cola",
        quantity=10000,
        due_in_hours=48,
        profit_priority=70,
        allowed_machines=["L1", "L2"],
    )
    tools.add_order(
        job_id="O-1002",
        product="milk",
        quantity=5000,
        due_in_hours=16,
        profit_priority=50,
        allowed_machines=["L2"],
    )
    tools.add_order(
        job_id="O-1003",
        product="orange_juice",
        quantity=8000,
        due_in_hours=24,
        profit_priority=60,
        allowed_machines=["L1"],
    )

    tools.add_machine(
        machine_id="L1",
        capacity_per_hour=2200,
        supported_products=["cola", "orange_juice"],
        name="产线1",
    )
    tools.add_machine(
        machine_id="L2",
        capacity_per_hour=1600,
        supported_products=["cola", "milk"],
        name="产线2",
    )

    return json.dumps(
        {
            "status": "success",
            "message": "演示数据已初始化",
            "orders": ["O-1001", "O-1002", "O-1003"],
            "machines": ["L1", "L2"],
        },
        ensure_ascii=False,
    )


if __name__ == "__main__":
    app.run()
