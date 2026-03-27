import pytest
from unittest.mock import patch, MagicMock
from aps.mcp.tools import (
    _global_state,
    run_aps_schedule,
    add_order,
    add_machine,
    get_schedule,
    list_orders,
    list_machines,
    clear_state,
)


class TestMCPTools:
    def setup_method(self):
        _global_state["orders"] = {}
        _global_state["machines"] = {}
        _global_state["current_schedule"] = None
        _global_state["schedule_history"] = []

    @pytest.mark.asyncio
    async def test_add_order(self, sample_product_cola):
        result = await add_order(
            order_id="test_001",
            product_id="cola",
            product_name="可乐",
            product_type="beverage",
            production_rate=1000.0,
            quantity=5000,
            due_date=48,
            priority=5
        )
        assert "成功" in result
        assert "test_001" in _global_state["orders"]

    @pytest.mark.asyncio
    async def test_add_order_duplicate(self, sample_product_cola):
        await add_order(
            order_id="test_001",
            product_id="cola",
            product_name="可乐",
            product_type="beverage",
            production_rate=1000.0,
            quantity=5000,
            due_date=48,
            priority=5
        )
        result = await add_order(
            order_id="test_001",
            product_id="cola",
            product_name="可乐",
            product_type="beverage",
            production_rate=1000.0,
            quantity=5000,
            due_date=48,
            priority=5
        )
        assert "已存在" in result or "错误" in result

    @pytest.mark.asyncio
    async def test_add_machine(self):
        result = await add_machine(
            machine_id="line_test",
            name="测试生产线",
            capacity=1000,
            supported_types=["beverage", "dairy"]
        )
        assert "成功" in result
        assert "line_test" in _global_state["machines"]

    @pytest.mark.asyncio
    async def test_list_orders_empty(self):
        result = await list_orders()
        assert "无订单" in result or "[]" in result or "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_list_orders_with_data(self):
        await add_order(
            order_id="test_001",
            product_id="cola",
            product_name="可乐",
            product_type="beverage",
            production_rate=1000.0,
            quantity=5000,
            due_date=48,
            priority=5
        )
        result = await list_orders()
        assert "test_001" in result

    @pytest.mark.asyncio
    async def test_list_machines_empty(self):
        result = await list_machines()
        assert "无机器" in result or "[]" in result or "empty" in result.lower()

    @pytest.mark.asyncio
    async def test_list_machines_with_data(self):
        await add_machine(
            machine_id="line_test",
            name="测试生产线",
            capacity=1000,
            supported_types=["beverage", "dairy"]
        )
        result = await list_machines()
        assert "line_test" in result

    @pytest.mark.asyncio
    async def test_clear_state(self):
        await add_order(
            order_id="test_001",
            product_id="cola",
            product_name="可乐",
            product_type="beverage",
            production_rate=1000.0,
            quantity=5000,
            due_date=48,
            priority=5
        )
        await clear_state()
        assert len(_global_state["orders"]) == 0

    @pytest.mark.asyncio
    async def test_get_schedule_empty(self):
        result = await get_schedule()
        assert "无排程" in result or "empty" in result.lower() or "none" in result.lower()

    @pytest.mark.asyncio
    async def test_run_aps_schedule_no_orders(self):
        result = await run_aps_schedule()
        assert "无订单" in result or "错误" in result or "error" in result.lower()
