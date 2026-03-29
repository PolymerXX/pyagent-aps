"""数据库适配器"""

import json
import sqlite3
from typing import Any

from aps.adapters.base import BaseAdapter, DataConfig
from aps.adapters.parsers import DEFAULT_PRODUCTION_RATE, parse_product_type
from aps.models.machine import ProductionLine
from aps.models.order import Order, Product
from aps.models.schedule import ScheduleResult


class DatabaseAdapter(BaseAdapter):
    """数据库适配器"""

    def __init__(self, config: DataConfig):
        super().__init__(config)
        self.connection = self._init_connection()
        self._ensure_tables()

    def _init_connection(self):
        conn_str = self.config.connection_string or ""

        if conn_str.startswith("sqlite"):
            db_path = conn_str.replace("sqlite:///", "").replace("sqlite://", "")
            return sqlite3.connect(db_path, check_same_thread=False)
        else:
            return sqlite3.connect(":memory:", check_same_thread=False)

    def _ensure_tables(self) -> None:
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                product_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                due_date REAL NOT NULL,
                priority INTEGER DEFAULT 1,
                min_start_time INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                capacity_per_hour REAL NOT NULL DEFAULT 1000,
                supported_product_types TEXT DEFAULT '',
                setup_time_hours REAL DEFAULT 0.0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)
        self.connection.commit()

    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT * FROM orders")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [self._parse_order(row, columns) for row in rows]
        except sqlite3.OperationalError:
            return []

    def get_machines(self, filter: dict[str, Any] | None = None) -> list[ProductionLine]:
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT * FROM machines")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [self._parse_machine(row, columns) for row in rows]
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

    def _parse_order(self, row: tuple, columns: list[str] | None = None) -> Order:
        if columns:
            row_dict = dict(zip(columns, row))
            product_type = parse_product_type(row_dict.get("product_type"))
            return Order(
                id=str(row_dict.get("id", "")),
                product=Product(
                    id=f"prod_{row_dict.get('id', '')}",
                    name=str(row_dict.get("product_name", "")),
                    product_type=product_type,
                    production_rate=float(row_dict.get("production_rate", DEFAULT_PRODUCTION_RATE)),
                ),
                quantity=int(row_dict.get("quantity", 0)),
                due_date=int(row_dict.get("due_date", 72)),
                priority=int(row_dict.get("priority", 1)),
                min_start_time=int(row_dict.get("min_start_time", 0)),
            )
        return Order(
            id=str(row[0]),
            product=Product(
                id=f"prod_{row[0]}",
                name=str(row[1]) if len(row) > 1 else "",
                product_type=parse_product_type(row[2] if len(row) > 2 else None),
                production_rate=DEFAULT_PRODUCTION_RATE,
            ),
            quantity=int(row[3]) if len(row) > 3 else 0,
            due_date=int(row[4]) if len(row) > 4 else 72,
            priority=int(row[5]) if len(row) > 5 else 1,
            min_start_time=int(row[6]) if len(row) > 6 else 0,
        )

    def _parse_machine(self, row: tuple, columns: list[str] | None = None) -> ProductionLine:
        if columns:
            row_dict = dict(zip(columns, row))
            types_str = str(row_dict.get("supported_product_types", ""))
            supported_types = []
            if types_str:
                for t in types_str.split(","):
                    t = t.strip()
                    if t:
                        try:
                            supported_types.append(parse_product_type(t))
                        except ValueError:
                            pass
            return ProductionLine(
                id=str(row_dict.get("id", "")),
                name=str(row_dict.get("name", "")),
                capacity_per_hour=float(row_dict.get("capacity_per_hour", 1000)),
                supported_product_types=supported_types,
                setup_time_hours=float(row_dict.get("setup_time_hours", 0.0)),
            )
        return ProductionLine(
            id=str(row[0]),
            name=str(row[1]) if len(row) > 1 else str(row[0]),
            capacity_per_hour=float(row[2]) if len(row) > 2 else 1000,
        )

    def __del__(self):
        if hasattr(self, "connection") and self.connection:
            self.connection.close()
