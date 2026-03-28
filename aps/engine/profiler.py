"""性能分析工具

提供求解器性能监控和分析
"""

import time
import functools
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Generator

from aps.models.schedule import ScheduleResult


@dataclass
class PerformanceMetrics:
    """性能指标"""
    solve_count: int = 0
    total_solve_time: float = 0.0
    avg_solve_time: float = 0.0
    min_solve_time: float = float("inf")
    max_solve_time: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    
    recent_solve_times: list[float] = field(default_factory=list)
    max_recent_count: int = 100

    def record_solve(self, solve_time: float) -> None:
        """记录一次求解"""
        self.solve_count += 1
        self.total_solve_time += solve_time
        self.avg_solve_time = self.total_solve_time / self.solve_count
        self.min_solve_time = min(self.min_solve_time, solve_time)
        self.max_solve_time = max(self.max_solve_time, solve_time)
        
        self.recent_solve_times.append(solve_time)
        if len(self.recent_solve_times) > self.max_recent_count:
            self.recent_solve_times.pop(0)

    def record_cache_hit(self) -> None:
        """记录缓存命中"""
        self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """记录缓存未命中"""
        self.cache_misses += 1

    @property
    def cache_hit_rate(self) -> float:
        """缓存命中率"""
        total = self.cache_hits + self.cache_misses
        return self.cache_hits / total if total > 0 else 0.0

    @property
    def recent_avg_time(self) -> float:
        """最近平均求解时间"""
        if not self.recent_solve_times:
            return 0.0
        return sum(self.recent_solve_times) / len(self.recent_solve_times)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "solve_count": self.solve_count,
            "total_solve_time": round(self.total_solve_time, 4),
            "avg_solve_time": round(self.avg_solve_time, 4),
            "min_solve_time": round(self.min_solve_time, 4) if self.min_solve_time != float("inf") else 0,
            "max_solve_time": round(self.max_solve_time, 4),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": round(self.cache_hit_rate, 2),
            "recent_avg_time": round(self.recent_avg_time, 4),
        }


class Profiler:
    """性能分析器"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._start_time: Optional[float] = None

    @contextmanager
    def measure(self, operation: str = "solve") -> Generator[None, None, None]:
        """测量执行时间"""
        start = time.time()
        try:
            yield None
        finally:
            elapsed = time.time() - start
            if operation == "solve":
                self.metrics.record_solve(elapsed)

    def record_result(self, result: ScheduleResult, from_cache: bool = False) -> None:
        """记录求解结果"""
        if from_cache:
            self.metrics.record_cache_hit()
        else:
            self.metrics.record_cache_miss()

    def get_report(self) -> dict:
        """获取性能报告"""
        return {
            "performance": self.metrics.to_dict(),
            "timestamp": time.time(),
        }

    def reset(self) -> None:
        """重置统计"""
        self.metrics = PerformanceMetrics()


_global_profiler: Optional[Profiler] = None


def get_profiler() -> Profiler:
    """获取全局分析器实例"""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = Profiler()
    return _global_profiler


def reset_profiler() -> None:
    """重置全局分析器"""
    global _global_profiler
    if _global_profiler is not None:
        _global_profiler.reset()
