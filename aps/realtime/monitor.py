"""实时监控处理器"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from aps.models.schedule import ScheduleResult


class MonitorAlert(BaseModel):
    """监控告警"""

    alert_id: str
    alert_type: str
    severity: str = "info"
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: dict[str, Any] = Field(default_factory=dict)


class RealtimeMonitor:
    """实时监控处理器"""

    def __init__(self):
        self._alerts: list[MonitorAlert] = []
        self._last_result: ScheduleResult | None = None

    def monitor(self, result: ScheduleResult) -> list[MonitorAlert]:
        """监控排程结果"""
        self._alerts = []
        self._last_result = result

        self._check_utilization(result)
        self._check_delays(result)
        self._check_changeover(result)

        return self._alerts

    def _check_utilization(self, result: ScheduleResult) -> None:
        """检查利用率"""
        for machine_id, util in result.machine_utilization.items():
            if util > 0.95:
                self._alerts.append(
                    MonitorAlert(
                        alert_id=f"util_{machine_id}_{datetime.now().strftime('%H%M%S')}",
                        alert_type="utilization",
                        severity="warning" if util < 0.98 else "critical",
                        message=f"机器 {machine_id} 利用率过高: {util * 100:.1f}%",
                        details={"machine_id": machine_id, "utilization": util},
                    )
                )

    def _check_delays(self, result: ScheduleResult) -> None:
        """检查延期"""
        if result.on_time_delivery_rate < 0.9:
            self._alerts.append(
                MonitorAlert(
                    alert_id=f"delay_{datetime.now().strftime('%H%M%S')}",
                    alert_type="delay",
                    severity="warning"
                    if result.on_time_delivery_rate > 0.8
                    else "critical",
                    message=f"准时率偏低: {result.on_time_delivery_rate * 100:.1f}%",
                    details={"on_time_rate": result.on_time_delivery_rate},
                )
            )

    def _check_changeover(self, result: ScheduleResult) -> None:
        """检查换产"""
        if result.total_makespan > 0:
            ratio = result.total_changeover_time / result.total_makespan
            if ratio > 0.25:
                self._alerts.append(
                    MonitorAlert(
                        alert_id=f"changeover_{datetime.now().strftime('%H%M%S')}",
                        alert_type="changeover",
                        severity="info",
                        message=f"换产时间占比较高: {ratio * 100:.1f}%",
                        details={"changeover_ratio": ratio},
                    )
                )

    def get_active_alerts(self, severity: str | None = None) -> list[MonitorAlert]:
        """获取活跃告警"""
        if severity:
            return [a for a in self._alerts if a.severity == severity]
        return self._alerts
