"""缓存机制

提供求解结果的缓存，避免重复计算
"""

import hashlib
import threading
import time
from functools import lru_cache
from typing import Optional

from aps.models.order import Order
from aps.models.machine import ProductionLine
from aps.models.constraint import ProductionConstraints
from aps.models.optimization import OptimizationParams
from aps.models.schedule import ScheduleResult


class SolverCache:
    """求解器缓存"""

    def __init__(self, max_size: int = 100, ttl_seconds: float = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[ScheduleResult, float]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _compute_key(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints,
        params: OptimizationParams,
        solver_type: str = "cp_sat",
    ) -> str:
        """计算缓存键"""
        orders_hash = hashlib.md5(
            "".join(
                f"{o.id}:{o.quantity}:{o.due_date}:{o.priority}:{o.min_start_time}:{o.product.product_type.value}"
                for o in sorted(orders, key=lambda x: x.id)
            ).encode()
        ).hexdigest()

        machines_hash = hashlib.md5(
            "".join(
                f"{m.id}:{m.capacity_per_hour}:{','.join(sorted(str(t) for t in m.supported_product_types))}"
                for m in sorted(machines, key=lambda x: x.id)
            ).encode()
        ).hexdigest()

        constraints_hash = hashlib.md5(
            f"{constraints.max_daily_hours}:{constraints.allow_overtime}:{constraints.max_overtime_hours}:{len(constraints.changeover_rules)}".encode()
        ).hexdigest()

        params_hash = hashlib.md5(
            f"{params.strategy.value}:{params.time_limit_seconds}:{params.weights.on_time}:{params.weights.changeover}:{params.weights.utilization}:{params.weights.profit}".encode()
        ).hexdigest()

        return f"{orders_hash}:{machines_hash}:{constraints_hash}:{params_hash}:{solver_type}"

    def get(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints,
        params: OptimizationParams,
        solver_type: str = "cp_sat",
    ) -> Optional[ScheduleResult]:
        """获取缓存结果"""
        key = self._compute_key(orders, machines, constraints, params, solver_type)
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    self._hits += 1
                    return result
                else:
                    del self._cache[key]
            self._misses += 1
        return None

    def set(
        self,
        orders: list[Order],
        machines: list[ProductionLine],
        constraints: ProductionConstraints,
        params: OptimizationParams,
        result: ScheduleResult,
        solver_type: str = "cp_sat",
    ) -> None:
        """设置缓存结果"""
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]
            key = self._compute_key(orders, machines, constraints, params, solver_type)
            self._cache[key] = (result, time.time())

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        """缓存统计"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


_global_cache: Optional[SolverCache] = None


def get_solver_cache() -> SolverCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SolverCache()
    return _global_cache


def clear_solver_cache() -> None:
    """清空全局缓存"""
    global _global_cache
    if _global_cache is not None:
        _global_cache.clear()


@lru_cache(maxsize=128)
def compute_order_hash(order_id: str, quantity: int, due_date: float) -> str:
    """计算订单哈希（带缓存）"""
    return hashlib.md5(f"{order_id}:{quantity}:{due_date}".encode()).hexdigest()
