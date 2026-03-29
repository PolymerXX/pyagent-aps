"""持久化 Repository

提供排程结果的持久化存储接口和 SQLite 实现。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

from aps.models.schedule import ScheduleResult
from aps.models.order import Order


class ScheduleRecord(BaseModel):
    """排程记录"""
    schedule_id: str = Field(..., description="排程ID")
    result: ScheduleResult = Field(..., description="排程结果")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    params_snapshot: dict[str, Any] = Field(default_factory=dict, description="参数快照")
    tags: list[str] = Field(default_factory=list, description="标签")


class OrderRecord(BaseModel):
    """订单记录"""
    order: Order = Field(..., description="订单")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ScheduleRepository(Protocol):
    """排程持久化接口"""

    def save_schedule(self, record: ScheduleRecord) -> str:
        """保存排程结果，返回 schedule_id"""
        ...

    def load_schedule(self, schedule_id: str) -> ScheduleRecord | None:
        """加载排程结果"""
        ...

    def list_schedules(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        """列出排程历史（摘要）"""
        ...

    def delete_schedule(self, schedule_id: str) -> bool:
        """删除排程记录"""
        ...

    def save_orders(self, orders: list[Order]) -> None:
        """保存订单列表"""
        ...

    def load_orders(self) -> list[Order]:
        """加载订单列表"""
        ...


class SQLiteScheduleRepository:
    """基于 SQLite 的排程持久化实现"""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()
        self._ensure_schema()

    @property
    def _conn(self) -> sqlite3.Connection:
        """线程局部连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self._db_path, check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _ensure_schema(self) -> None:
        """确保数据库表存在"""
        conn = self._conn
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS schedules (
                schedule_id TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                params_json TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders_store (
                order_id TEXT PRIMARY KEY,
                order_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_schedules_created
                ON schedules(created_at DESC);
        """)
        conn.commit()

    def save_schedule(self, record: ScheduleRecord) -> str:
        with self._lock:
            self._conn.execute(
                """INSERT OR REPLACE INTO schedules
                   (schedule_id, result_json, params_json, tags, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    record.schedule_id,
                    record.result.model_dump_json(),
                    json.dumps(record.params_snapshot),
                    json.dumps(record.tags),
                    record.created_at,
                ),
            )
            self._conn.commit()
        return record.schedule_id

    def load_schedule(self, schedule_id: str) -> ScheduleRecord | None:
        row = self._conn.execute(
            "SELECT * FROM schedules WHERE schedule_id = ?",
            (schedule_id,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def list_schedules(self, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """SELECT schedule_id, created_at, tags
               FROM schedules ORDER BY created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "schedule_id": row["schedule_id"],
                "created_at": row["created_at"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "task_count": 0,
            })
        return result

    def delete_schedule(self, schedule_id: str) -> bool:
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM schedules WHERE schedule_id = ?",
                (schedule_id,),
            )
            self._conn.commit()
            return cursor.rowcount > 0

    def save_orders(self, orders: list[Order]) -> None:
        with self._lock:
            now = datetime.now().isoformat()
            for order in orders:
                self._conn.execute(
                    """INSERT OR REPLACE INTO orders_store
                       (order_id, order_json, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (order.id, order.model_dump_json(), now, now),
                )
            self._conn.commit()

    def load_orders(self) -> list[Order]:
        rows = self._conn.execute(
            "SELECT order_json FROM orders_store ORDER BY created_at"
        ).fetchall()
        orders = []
        for row in rows:
            try:
                data = json.loads(row["order_json"])
                orders.append(Order.model_validate(data))
            except Exception:
                continue
        return orders

    def _row_to_record(self, row: sqlite3.Row) -> ScheduleRecord:
        result = ScheduleResult.model_validate_json(row["result_json"])
        return ScheduleRecord(
            schedule_id=row["schedule_id"],
            result=result,
            created_at=row["created_at"],
            params_snapshot=json.loads(row["params_json"]) if row["params_json"] else {},
            tags=json.loads(row["tags"]) if row["tags"] else [],
        )

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None


_global_repo: SQLiteScheduleRepository | None = None
_repo_lock = threading.Lock()


def get_repository(db_path: str = ":memory:") -> SQLiteScheduleRepository:
    """获取全局 Repository 实例"""
    global _global_repo
    if _global_repo is None:
        with _repo_lock:
            if _global_repo is None:
                _global_repo = SQLiteScheduleRepository(db_path)
    return _global_repo


def reset_repository() -> None:
    """重置全局 Repository（测试用）"""
    global _global_repo
    with _repo_lock:
        if _global_repo is not None:
            _global_repo.close()
        _global_repo = None
