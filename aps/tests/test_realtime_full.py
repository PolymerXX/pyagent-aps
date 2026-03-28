"""Realtime模块完整测试"""

from datetime import datetime

import pytest

from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus
from aps.realtime.adjuster import AdjustmentEvent, RealtimeAdjuster
from aps.realtime.monitor import MonitorAlert, RealtimeMonitor


@pytest.fixture
def realtime_product():
    return Product(
        id="P_RT", name="实时产品", product_type=ProductType.BEVERAGE, production_rate=100.0
    )


@pytest.fixture
def realtime_order(realtime_product):
    return Order(id="RT001", product=realtime_product, quantity=1000, due_date=24)


@pytest.fixture
def realtime_orders(realtime_product):
    return [
        Order(id="RT001", product=realtime_product, quantity=1000, due_date=24),
        Order(id="RT002", product=realtime_product, quantity=500, due_date=12),
    ]


@pytest.fixture
def realtime_machine():
    return ProductionLine(
        id="RM001",
        name="实时产线1",
        supported_product_types=[ProductType.BEVERAGE],
        capacity_per_hour=100.0,
        setup_time_hours=0.0,
        status=MachineStatus(machine_id="RM001", status="active"),
    )


@pytest.fixture
def realtime_machines(realtime_machine):
    return [realtime_machine]


@pytest.fixture
def realtime_params():
    return OptimizationParams(strategy=OptimizationStrategy.BALANCED)


class TestRealtimeAdjuster:
    def test_init(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)
        assert adjuster.orders == realtime_orders
        assert adjuster.machines == realtime_machines
        assert adjuster._event_history == []

    def test_handle_new_order(self, realtime_orders, realtime_machines, realtime_product):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        new_order = Order(
            id="RT_NEW",
            product=realtime_product,
            quantity=2000,
            due_date=48,
        )

        event = adjuster.handle_new_order(new_order)

        assert event.event_type == "new_order"
        assert "RT_NEW" in event.affected_orders
        assert len(adjuster.orders) == 3
        assert len(adjuster._event_history) == 1

    def test_handle_machine_down(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        event = adjuster.handle_machine_down("RM001")

        assert event.event_type == "machine_down"
        assert event.details["machine_id"] == "RM001"
        assert len(adjuster._event_history) == 1

    def test_handle_order_change_quantity(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        event = adjuster.handle_order_change("RT001", {"quantity": 2000})

        assert event.event_type == "order_change"
        assert event.affected_orders == ["RT001"]
        assert event.details == {"quantity": 2000}

    def test_handle_order_change_due_date(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        event = adjuster.handle_order_change("RT001", {"due_date": 48})

        assert event.event_type == "order_change"
        assert event.affected_orders == ["RT001"]

    def test_handle_order_change_multiple(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        event = adjuster.handle_order_change("RT001", {"quantity": 2000, "due_date": 48})

        assert event.details["quantity"] == 2000
        assert event.details["due_date"] == 48

    def test_reschedule_default(self, realtime_orders, realtime_machines):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        result = adjuster.reschedule()

        assert isinstance(result, ScheduleResult)
        assert result.planning_time_seconds >= 0

    def test_reschedule_with_params(self, realtime_orders, realtime_machines, realtime_params):
        adjuster = RealtimeAdjuster(realtime_orders, realtime_machines)

        result = adjuster.reschedule(realtime_params)

        assert isinstance(result, ScheduleResult)


class TestAdjustmentEvent:
    def test_event_defaults(self):
        event = AdjustmentEvent(event_type="test")

        assert event.event_type == "test"
        assert isinstance(event.event_time, datetime)
        assert event.affected_orders == []
        assert event.details == {}

    def test_event_with_data(self):
        custom_time = datetime(2024, 1, 1, 10, 0, 0)
        event = AdjustmentEvent(
            event_type="custom_event",
            event_time=custom_time,
            affected_orders=["O001", "O002"],
            details={"key": "value"},
        )

        assert event.event_time == custom_time
        assert len(event.affected_orders) == 2
        assert event.details["key"] == "value"


class TestRealtimeMonitor:
    @pytest.fixture
    def monitor(self):
        return RealtimeMonitor()

    @pytest.fixture
    def sample_result_for_monitor(self):
        return ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="产品A",
                    product_type="beverage",
                    start_time=0.0,
                    end_time=10.0,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                )
            ],
            total_makespan=10.0,
            on_time_delivery_rate=0.0,
            total_changeover_time=2.0,
            machine_utilization={"M001": 0.0},
            planning_time_seconds=1.0,
        )

    def test_init(self, monitor):
        assert monitor._alerts == []
        assert monitor._last_result is None

    def test_monitor_returns_alerts(self, monitor, sample_result_for_monitor):
        alerts = monitor.monitor(sample_result_for_monitor)

        assert isinstance(alerts, list)

    def test_monitor_stores_result(self, monitor, sample_result_for_monitor):
        monitor.monitor(sample_result_for_monitor)

        assert monitor._last_result == sample_result_for_monitor

    def test_get_active_alerts_all(self, monitor, sample_result_for_monitor):
        monitor.monitor(sample_result_for_monitor)

        all_alerts = monitor.get_active_alerts()

        assert isinstance(all_alerts, list)

    def test_get_active_alerts_by_severity(self, monitor):
        monitor._alerts = [
            MonitorAlert(alert_id="1", alert_type="test", severity="warning", message="Test 1"),
            MonitorAlert(alert_id="2", alert_type="test", severity="critical", message="Test 2"),
            MonitorAlert(alert_id="3", alert_type="test", severity="warning", message="Test 3"),
        ]

        warnings = monitor.get_active_alerts("warning")
        critical = monitor.get_active_alerts("critical")

        assert len(warnings) == 2
        assert len(critical) == 1

    def test_check_utilization_warning(self, monitor):
        result = ScheduleResult(
            assignments=[],
            total_makespan=10.0,
            on_time_delivery_rate=1.0,
            total_changeover_time=0.0,
            machine_utilization={"M001": 0.96},
            planning_time_seconds=1.0,
        )

        alerts = monitor.monitor(result)

        utilization_alerts = [a for a in alerts if a.alert_type == "utilization"]
        assert len(utilization_alerts) == 1
        assert utilization_alerts[0].severity == "warning"

    def test_check_utilization_critical(self, monitor):
        result = ScheduleResult(
            assignments=[],
            total_makespan=10.0,
            on_time_delivery_rate=1.0,
            total_changeover_time=0.0,
            machine_utilization={"M001": 1.0},
            planning_time_seconds=1.0,
        )

        alerts = monitor.monitor(result)

        utilization_alerts = [a for a in alerts if a.alert_type == "utilization"]
        assert len(utilization_alerts) == 1
        assert utilization_alerts[0].severity == "critical"

    def test_check_delays_warning(self, monitor):
        result = ScheduleResult(
            assignments=[],
            total_makespan=10.0,
            on_time_delivery_rate=0.85,
            total_changeover_time=0.0,
            machine_utilization={},
            planning_time_seconds=1.0,
        )

        alerts = monitor.monitor(result)

        delay_alerts = [a for a in alerts if a.alert_type == "delay"]
        assert len(delay_alerts) == 1
        assert delay_alerts[0].severity == "warning"

    def test_check_delays_critical(self, monitor):
        result = ScheduleResult(
            assignments=[],
            total_makespan=10.0,
            on_time_delivery_rate=0.75,
            total_changeover_time=0.0,
            machine_utilization={},
            planning_time_seconds=1.0,
        )

        alerts = monitor.monitor(result)

        delay_alerts = [a for a in alerts if a.alert_type == "delay"]
        assert len(delay_alerts) == 1
        assert delay_alerts[0].severity == "critical"

    def test_check_changeover(self, monitor):
        result = ScheduleResult(
            assignments=[],
            total_makespan=10.0,
            on_time_delivery_rate=1.0,
            total_changeover_time=5.0,
            machine_utilization={},
            planning_time_seconds=1.0,
        )

        alerts = monitor.monitor(result)

        changeover_alerts = [a for a in alerts if a.alert_type == "changeover"]
        assert len(changeover_alerts) == 1


class TestMonitorAlert:
    def test_alert_defaults(self):
        alert = MonitorAlert(
            alert_id="test_1",
            alert_type="test",
            message="Test alert",
        )

        assert alert.alert_id == "test_1"
        assert alert.alert_type == "test"
        assert alert.severity == "info"
        assert alert.message == "Test alert"
        assert isinstance(alert.timestamp, datetime)
        assert alert.details == {}

    def test_alert_with_details(self):
        alert = MonitorAlert(
            alert_id="test_2",
            alert_type="utilization",
            severity="warning",
            message="High utilization",
            details={"machine_id": "M001", "utilization": 0.96},
        )

        assert alert.severity == "warning"
        assert alert.details["machine_id"] == "M001"
