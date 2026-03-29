"""Notebook / 脚本可调用的示例订单与产线（非 pytest fixture）。"""

from aps.models.machine import MachineStatus, ProductionLine
from aps.models.order import Order, Product, ProductType


def get_sample_orders() -> list[Order]:
    return [
        Order(
            id="O001",
            product=Product(
                id="P001", name="可乐", product_type=ProductType.BEVERAGE, production_rate=100
            ),
            quantity=1000,
            due_date=24,
        ),
        Order(
            id="O002",
            product=Product(
                id="P002", name="牛奶", product_type=ProductType.DAIRY, production_rate=80
            ),
            quantity=500,
            due_date=12,
        ),
        Order(
            id="O003",
            product=Product(
                id="P003", name="橙汁", product_type=ProductType.JUICE, production_rate=120
            ),
            quantity=800,
            due_date=36,
        ),
    ]


def get_sample_machines() -> list[ProductionLine]:
    return [
        ProductionLine(
            id="M001",
            name="产线A",
            supported_product_types=[ProductType.BEVERAGE, ProductType.DAIRY],
            capacity_per_hour=100,
            setup_time_hours=0.5,
            status=MachineStatus(machine_id="M001", status="running"),
        ),
        ProductionLine(
            id="M002",
            name="产线B",
            supported_product_types=[ProductType.BEVERAGE, ProductType.JUICE],
            capacity_per_hour=150,
            setup_time_hours=0.3,
            status=MachineStatus(machine_id="M002", status="running"),
        ),
    ]
