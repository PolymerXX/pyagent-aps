"""监控Agent - 实时监控生产状态"""

from typing import Optional, List
 Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from aps.core.config import get_settings
from aps.agents.base import create_model_settings
from aps.models.schedule import ScheduleResult


class MonitorMetric(BaseModel):
    """监控指标"""

    name: str
    value: float
    unit: str
    status: str = "normal"
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str = ""


class MachineStatus(BaseModel):
    """机器状态"""

    machine_id: str
    status: str
    utilization: float
    current_task: Optional[str] = None
    alerts: List[str] = Field(default_factory=list)


class MonitorReport(BaseModel):
    """监控报告"""

    report_id: str = Field(
        default_factory=lambda: f"report_{datetime.now().strftime('%Y%m%d-%H%M')}"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    overall_status: str = "normal"
    metrics: List[MonitorMetric] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    machine_statuses: List[MachineStatus] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""


class MonitorAgent:
    """监控Agent"""

    def __init__(self):
        self.config = get_settings()
        self.settings = create_model_settings(temperature=0.2)

        self.agent = Agent(
            self.config.default_model,
            model_settings=self.settings,
            instructions=self._get_instructions(),
            output_type=MonitorReport,
        )

    def _get_instructions(self) -> str:
        return """你是APS系统的监控Agent。

你的职责是监控生产状态并生成报告。

**监控维度**：
1. 机器利用率（正常70-85%，警告>85%，危险>90%）
2. 准时交付率（正常>95%)
3. 换产频率（正常<20%）

**输出要求**：
- overall_status: 整体状态
- metrics: 关键指标列表
- alerts: 警报列表
 - machine_statuses: 各机器状态
- recommendations: 改进建议
- summary: 简要总结
"""

    async def run(
        self, result: ScheduleResult, context: Optional[dict] = None
    ) -> MonitorReport:
        """生成监控报告"""
        prompt = self._build_monitor_prompt(result)
        agent_result = await self.agent.run(prompt)
        return agent_result.data

    def _build_monitor_prompt(self, result: ScheduleResult) -> str:
        """构建监控提示"""
        lines = ["## 排程数据"]
        lines.append(f"- 任务数: {result.task_count}")
        lines.append(f"- 总完工时间: {result.total_makespan:.1f}小时")
        lines.append(f"- 准时率: {result.on_time_delivery_rate * 100:.1f}%")
        lines.append(f"- 换产时间: {result.total_changeover_time:.1f}小时")

        lines.append("\n## 机器利用率")
        for machine_id, util in result.machine_utilization.items():
            lines.append(f"- {machine_id}: {util * 100:.1f}%")

        lines.append("\n请生成监控报告。")

        return "\n".join(lines)

    def generate_report_sync(self, result: ScheduleResult) -> MonitorReport:
        """同步生成报告（不使用LLM）"""
        metrics = []
        alerts = []
        machine_statuses = []
        recommendations = []

        metrics.append(
            MonitorMetric(
                name="准时交付率",
                value=result.on_time_delivery_rate * 100,
                unit="%",
                status="normal" if result.on_time_delivery_rate >= 0.95 else "warning",
            )
        )

        metrics.append(
            MonitorMetric(
                name="总完工时间",
                value=result.total_makespan,
                unit="小时",
                status="normal",
            )
        )

        for machine_id, util in result.machine_utilization.items():
            status = "active"
            machine_alerts = []

            if util > 0.9:
                status = "warning"
                machine_alerts.append("利用率过高")
                alerts.append(f"机器 {machine_id} 利用率过高 ({util * 100:.1f}%)")
            elif util > 0.85:
                status = "active"
                machine_alerts.append("利用率较高")

            machine_statuses.append(
                MachineStatus(
                    machine_id=machine_id,
                    status=status,
                    utilization=util,
                    alerts=machine_alerts,
                )
            )

        if result.on_time_delivery_rate < 0.9:
            alerts.append(f"准时率较低 ({result.on_time_delivery_rate * 100:.1f}%)")
            recommendations.append("检查延期订单优先级")

        if result.delayed_count > 0:
            recommendations.append("建议调整生产序列或增加产能")

        if not recommendations:
            recommendations.append("生产状态正常")

        overall = "normal"
        if len(alerts) > 0:
            overall = "warning"

        return MonitorReport(
            overall_status=overall,
            metrics=metrics,
            alerts=alerts,
            machine_statuses=machine_statuses,
            recommendations=recommendations,
            summary=f"共{result.task_count}个任务，准时率{result.on_time_delivery_rate * 100:.1f}%",
        )
