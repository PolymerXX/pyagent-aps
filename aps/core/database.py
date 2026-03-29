"""SQLite 数据库管理

提供连接管理和基础操作。
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Generator


class DatabaseManager:
    """SQLite 数据库管理器 — 线程安全的连接池"""

    def __init__(self, db_path: str = ":memory:"):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._local = threading.local()

    @property
    def connection(self) -> sqlite3.Connection:
        """获取线程局部连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        """事务上下文管理器"""
        conn = self.connection
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """执行 SQL"""
        with self._lock:
            return self.connection.execute(sql, params)

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """批量执行"""
        with self._lock:
            self.connection.executemany(sql, params_list)
            self.connection.commit()

    def fetch_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        """查询单行"""
        row = self.connection.execute(sql, params).fetchone()
        if row is None:
            return None
        return dict(row)

    def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """查询多行"""
        rows = self.connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """关闭连接"""
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    @property
    def db_path(self) -> str:
        return self._db_path


_global_db: DatabaseManager | None = None
_db_lock = threading.Lock()


def get_database(db_path: str = ":memory:") -> DatabaseManager:
    """获取全局 DatabaseManager 实例"""
    global _global_db
    if _global_db is None:
        with _db_lock:
            if _global_db is None:
                _global_db = DatabaseManager(db_path)
    return _global_db


def reset_database() -> None:
    """重置全局 DatabaseManager（测试用）"""
    global _global_db
    with _db_lock:
        if _global_db is not None:
            _global_db.close()
        _global_db = None
