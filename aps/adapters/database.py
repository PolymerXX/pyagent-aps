"""数据库适配器"""

from typing import List, Optional, Dict, Any
import sqlite3
import json

from aps.adapters.base import BaseAdapter, DataConfig
from aps.models.order import Order, Product, ProductType
from aps.models.machine import ProductionLine
from aps.models.schedule import ScheduleResult


class DatabaseAdapter(BaseAdapter):
    """数据库适配器"""

    def __init__(self, config: DataConfig):
        super().__init__(config)
        self.connection = self._init_connection()

    def _init_connection(self):
        conn_str = self.config.connection_string or ""

        if conn_str.startswith("sqlite"):
            db_path = conn_str.replace("sqlite:///", "").replace("sqlite://", "")
            return sqlite3.connect(db_path, check_same_thread=False)
        else:
            return sqlite3.connect(":memory:", check_same_thread=False)

    def get_orders(self, filter: Optional[Dict[str, Any]] = None) -> List[Order]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT * FROM orders")
            rows = cursor.fetchall()
            return [self._parse_order(row) for row in rows]
        except sqlite3.OperationalError:
            return []

    def get_machines(
        self, filter: Optional[Dict[str, Any]] = None
    ) -> List[ProductionLine]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT * FROM machines")
            rows = cursor.fetchall()
            return [self._parse_machine(row) for row in rows]
        except sqlite3.OperationalError:
            return []

    def push_schedule(self, result: ScheduleResult) -> bool:
        cursor = self.connection.cursor()
        cursor.execute(
            "INSERT INTO schedules (id, data) VALUES (?, ?)",
            (
                result.model_dump().get("schedule_id", "1"),
                json.dumps(result.model_dump()),
            ),
        )
        self.connection.commit()
        return True

    def _parse_order(self, row: tuple) -> Order:
        return Order(
            id=row[0],
            product=Product(name=row[1], product_type=ProductType.COLA),
            quantity=row[3] if len(row) > 3 else 0,
            due_date=row[4] if len(row) > 4 else 72.0,
        )

    def _parse_machine(self, row: tuple) -> ProductionLine:
        return ProductionLine(
            id=row[0],
            name=row[1] if len(row) > 1 else row[0],
            capacity_per_hour=row[2] if len(row) > 2 else 1000,
        )

    def __del__(self):
        if self.connection:
            self.connection.close()
