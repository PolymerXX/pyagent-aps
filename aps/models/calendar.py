"""生产日历模型

包含班次、维护窗口和生产日历定义。
Phase 2 渐进式：先支持维护窗口，班次拆分留到后续阶段。
"""

from pydantic import BaseModel, ConfigDict, Field


class Shift(BaseModel):
    """班次定义"""
    name: str = Field(..., description="班次名称，如 '早班'")
    start_hour: int = Field(..., ge=0, le=23, description="一天内的开始小时（0-23）")
    end_hour: int = Field(..., ge=0, le=24, description="一天内的结束小时（0-24）")
    days: list[int] = Field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5, 6],
        description="生效的星期几（0=周一..6=周日）",
    )

    model_config = ConfigDict()


class MaintenanceWindow(BaseModel):
    """维护窗口"""
    machine_id: str = Field(..., description="机器ID")
    start_hour: float = Field(..., ge=0.0, description="开始时间（相对小时数）")
    duration_hours: float = Field(..., gt=0.0, description="持续时长（小时）")
    recurring: bool = Field(default=False, description="是否周期性重复")
    recurring_interval_hours: float = Field(
        default=0.0, ge=0.0,
        description="重复间隔（小时），仅 recurring=True 时有效",
    )
    description: str = Field(default="", description="维护说明")

    @property
    def end_hour(self) -> float:
        return self.start_hour + self.duration_hours

    model_config = ConfigDict()


class ProductionCalendar(BaseModel):
    """生产日历 — 聚合班次、维护窗口、假日"""
    shifts: list[Shift] = Field(default_factory=list, description="班次列表")
    maintenance_windows: list[MaintenanceWindow] = Field(
        default_factory=list, description="维护窗口列表"
    )
    holidays: list[float] = Field(
        default_factory=list, description="假日（相对小时数列表）"
    )

    model_config = ConfigDict()

    def is_available(self, hour: float, machine_id: str) -> bool:
        """检查给定时间点机器是否可用（不在维护窗口内）"""
        for mw in self.maintenance_windows:
            if mw.machine_id != machine_id:
                continue
            if mw.recurring and mw.recurring_interval_hours > 0:
                cycle_start = mw.start_hour
                while cycle_start <= hour:
                    if cycle_start <= hour < cycle_start + mw.duration_hours:
                        return False
                    cycle_start += mw.recurring_interval_hours
            else:
                if mw.start_hour <= hour < mw.end_hour:
                    return False
        return True

    def next_available_time(self, after_hour: float, machine_id: str) -> float:
        """给定时间之后下一个可用时间点"""
        candidate = after_hour
        for _ in range(100):
            if self.is_available(candidate, machine_id):
                return candidate
            earliest_end = candidate
            for mw in self.maintenance_windows:
                if mw.machine_id != machine_id:
                    continue
                if mw.recurring and mw.recurring_interval_hours > 0:
                    cycle_start = mw.start_hour
                    while cycle_start <= candidate:
                        if cycle_start <= candidate < cycle_start + mw.duration_hours:
                            end = cycle_start + mw.duration_hours
                            if end > earliest_end:
                                earliest_end = end
                        cycle_start += mw.recurring_interval_hours
                else:
                    if mw.start_hour <= candidate < mw.end_hour:
                        if mw.end_hour > earliest_end:
                            earliest_end = mw.end_hour
            if earliest_end == candidate:
                break
            candidate = earliest_end
        return candidate

    def get_maintenance_intervals(
        self, machine_id: str, horizon: float
    ) -> list[tuple[float, float]]:
        """获取指定机器在 [0, horizon] 范围内的所有维护区间"""
        intervals: list[tuple[float, float]] = []
        for mw in self.maintenance_windows:
            if mw.machine_id != machine_id:
                continue
            if mw.recurring and mw.recurring_interval_hours > 0:
                start = mw.start_hour
                while start < horizon:
                    end = start + mw.duration_hours
                    if end > 0 and start < horizon:
                        intervals.append((max(0, start), min(horizon, end)))
                    start += mw.recurring_interval_hours
            else:
                if mw.end_hour > 0 and mw.start_hour < horizon:
                    intervals.append((max(0, mw.start_hour), min(horizon, mw.end_hour)))
        return sorted(intervals)
