"""MCP Registry 和工具注册 单元测试"""


from aps.mcp.registry import MCPToolRegistry, ToolCategory, ToolMetadata, registry


class TestToolCategory:
    def test_values(self):
        assert ToolCategory.SCHEDULING.value == "scheduling"
        assert ToolCategory.ORDER.value == "order"
        assert ToolCategory.MACHINE.value == "machine"
        assert ToolCategory.CONSTRAINT.value == "constraint"
        assert ToolCategory.RESULT.value == "result"


class TestToolMetadata:
    def test_creation(self):
        meta = ToolMetadata(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.SCHEDULING,
        )
        assert meta.name == "test_tool"
        assert meta.description == "测试工具"
        assert meta.category == ToolCategory.SCHEDULING
        assert meta.version == "1.0.0"
        assert meta.requires == []
        assert meta.provides == []
        assert meta.examples == []

    def test_with_extras(self):
        meta = ToolMetadata(
            name="test",
            description="test",
            category=ToolCategory.ORDER,
            version="2.0.0",
            requires=["order_exists"],
            provides=["schedule_created"],
            examples=[{"input": "test"}],
        )
        assert meta.version == "2.0.0"
        assert len(meta.requires) == 1
        assert len(meta.provides) == 1


class TestMCPToolRegistry:
    def test_singleton(self):
        r1 = MCPToolRegistry()
        r2 = MCPToolRegistry()
        assert r1 is r2

    def _make_fresh_registry(self):
        r = object.__new__(MCPToolRegistry)
        r._tools = {}
        r._handlers = {}
        return r

    def test_register_and_get_handler(self):
        r = self._make_fresh_registry()

        def dummy_handler():
            return "ok"

        r.register(
            name="dummy",
            description="测试",
            category=ToolCategory.SCHEDULING,
            handler=dummy_handler,
        )
        assert r.get_handler("dummy") is dummy_handler
        assert r.get_handler("nonexistent") is None

    def test_register_and_get_metadata(self):
        r = self._make_fresh_registry()

        def dummy_handler():
            return "ok"

        r.register(
            name="dummy",
            description="测试",
            category=ToolCategory.ORDER,
            handler=dummy_handler,
        )
        meta = r.get_metadata("dummy")
        assert meta is not None
        assert meta.name == "dummy"
        assert r.get_metadata("nonexistent") is None

    def test_list_tools_all(self):
        r = self._make_fresh_registry()

        def handler():
            pass

        r.register(
            name="t1", description="test1", category=ToolCategory.SCHEDULING, handler=handler
        )
        r.register(name="t2", description="test2", category=ToolCategory.ORDER, handler=handler)
        r.register(name="t3", description="test3", category=ToolCategory.MACHINE, handler=handler)

        all_tools = r.list_tools()
        assert len(all_tools) == 3

    def test_list_tools_by_category(self):
        r = self._make_fresh_registry()

        def handler():
            pass

        r.register(
            name="t1", description="test1", category=ToolCategory.SCHEDULING, handler=handler
        )
        r.register(name="t2", description="test2", category=ToolCategory.ORDER, handler=handler)
        r.register(
            name="t3", description="test3", category=ToolCategory.SCHEDULING, handler=handler
        )

        scheduling_tools = r.list_tools(category=ToolCategory.SCHEDULING)
        assert len(scheduling_tools) == 2

        order_tools = r.list_tools(category=ToolCategory.ORDER)
        assert len(order_tools) == 1


class TestGlobalRegistry:
    def test_has_tools(self):
        tools = registry.list_tools()
        assert len(tools) > 0

    def test_scheduling_category(self):
        tools = registry.list_tools(category=ToolCategory.SCHEDULING)
        names = [t.name for t in tools]
        assert "run_aps_schedule" in names
        assert "get_schedule_status" in names

    def test_order_category(self):
        tools = registry.list_tools(category=ToolCategory.ORDER)
        names = [t.name for t in tools]
        assert "add_order" in names
        assert "get_orders" in names
        assert "remove_order" in names
        assert "update_order" in names

    def test_machine_category(self):
        tools = registry.list_tools(category=ToolCategory.MACHINE)
        names = [t.name for t in tools]
        assert "add_machine" in names
        assert "get_machines" in names
        assert "update_machine_status" in names

    def test_constraint_category(self):
        tools = registry.list_tools(category=ToolCategory.CONSTRAINT)
        names = [t.name for t in tools]
        assert "set_constraints" in names
        assert "get_constraints" in names

    def test_result_category(self):
        tools = registry.list_tools(category=ToolCategory.RESULT)
        names = [t.name for t in tools]
        assert "explain_schedule" in names
        assert "validate_schedule" in names

    def test_handler_retrieval(self):
        from aps.mcp.tools import add_order

        handler = registry.get_handler("add_order")
        assert handler is add_order

    def test_metadata_retrieval(self):
        meta = registry.get_metadata("add_order")
        assert meta is not None
        assert meta.category == ToolCategory.ORDER
