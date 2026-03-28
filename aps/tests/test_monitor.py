"""MonitorAgent 单元测试 - 不依赖LLM"""

import pytest

from aps.agents.monitor import MachineStatus, MonitorAgent, MonitorMetric, MonitorReport
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


@pytest.fixture
def monitor():
    return MonitorAgent()


@pytest.fixture
def good_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0,
                end_time=10,
                quantity=1000,
                status=TaskStatus.PLANNED,
                is_on_time=True,
            ),
        ],
        total_makespan=10.0,
        on_time_delivery_rate=1.0,
        total_changeover_time=0.0,
        machine_utilization={"M001": 0.8},
    )


@pytest.fixture
def warning_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0,
                end_time=10,
                quantity=1000,
                status=TaskStatus.PLANNED,
                is_on_time=True,
            ),
            TaskAssignment(
                order_id="O002",
                machine_id="M001",
                product_name="牛奶",
                product_type="dairy",
                start_time=10.5,
                end_time=18,
                quantity=500,
                status=TaskStatus.PLANNED,
                is_on_time=False,
                delay_hours=6.0,
            ),
        ],
        total_makespan=18.0,
        on_time_delivery_rate=0.5,
        total_changeover_time=3.0,
        machine_utilization={"M001": 0.95},
    )


class TestGenerateReportSync:
    def test_good_report(self, monitor, good_result):
        report = monitor.generate_report_sync(good_result)
        assert isinstance(report, MonitorReport)
        assert report.overall_status == "normal"
        assert len(report.metrics) >= 2

    def test_warning_report(self, monitor, warning_result):
        report = monitor.generate_report_sync(warning_result)
        assert report.overall_status == "warning"
        assert len(report.alerts) > 0

    def test_report_metrics(self, monitor, good_result):
        report = monitor.generate_report_sync(good_result)
        metric_names = [m.name for m in report.metrics]
        assert "准时交付率" in metric_names
        assert "总完工时间" in metric_names

    def test_report_machine_statuses(self, monitor, good_result):
        report = monitor.generate_report_sync(good_result)
        assert len(report.machine_statuses) == 1
        assert report.machine_statuses[0].machine_id == "M001"

    def test_report_summary(self, monitor, good_result):
        report = monitor.generate_report_sync(good_result)
        assert "1" in report.summary
        assert "100.0%" in report.summary

    def test_delayed_recommendations(self, monitor, warning_result):
        report = monitor.generate_report_sync(warning_result)
        assert len(report.recommendations) > 0

    def test_normal_recommendations(self, monitor, good_result):
        report = monitor.generate_report_sync(good_result)
        assert any("正常" in r for r in report.recommendations)


class TestMonitorMetric:
    def test_creation(self):
        metric = MonitorMetric(name="测试指标", value=95.0, unit="%")
        assert metric.name == "测试指标"
        assert metric.value == 95.0
        assert metric.unit == "%"
        assert metric.status == "normal"

    def test_with_description(self):
        metric = MonitorMetric(name="利用率", value=85.0, unit="%", description="机器利用率")
        assert metric.description == "机器利用率"


class TestMachineStatus:
    def test_creation(self):
        status = MachineStatus(machine_id="M001", status="running", utilization=0.85)
        assert status.machine_id == "M001"
        assert status.status == "running"
        assert status.utilization == 0.85
        assert status.current_task is None
        assert status.alerts == []


class TestMonitorReport:
    def test_defaults(self):
        report = MonitorReport()
        assert report.overall_status == "normal"
        assert report.metrics == []
        assert report.alerts == []
        assert report.machine_statuses == []
        assert report.recommendations == []
        assert report.summary == ""
