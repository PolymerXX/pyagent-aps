"""BaseAPSAgent 单元测试 - 不依赖LLM"""

from typing import Any, cast

from aps.agents.base import DEFAULT_SETTINGS, AgentContext, BaseAPSAgent, create_model_settings


class TestCreateModelSettings:
    def test_defaults(self):
        # OpenRouterModelSettings 为 TypedDict(total=False)，直接用 [] 会触发类型告警
        settings = cast(dict[str, Any], create_model_settings())
        assert settings["temperature"] is not None
        assert settings["max_tokens"] is not None

    def test_custom_temperature(self):
        settings = cast(dict[str, Any], create_model_settings(temperature=0.5))
        assert settings["temperature"] == 0.5

    def test_custom_max_tokens(self):
        settings = cast(dict[str, Any], create_model_settings(max_tokens=2048))
        assert settings["max_tokens"] == 2048

    def test_custom_top_p(self):
        settings = cast(dict[str, Any], create_model_settings(top_p=0.8))
        assert settings["top_p"] == 0.8


class TestDefaultSettings:
    def test_exists(self):
        assert DEFAULT_SETTINGS is not None

    def test_is_dict(self):
        assert isinstance(DEFAULT_SETTINGS, dict)


class TestAgentContext:
    def test_empty_context(self):
        ctx = AgentContext()
        assert ctx.user_input == ""
        assert ctx.orders_info == ""
        assert ctx.machines_info == ""
        assert ctx.constraints_info == ""
        assert ctx.optimization_params is None
        assert ctx.schedule_result is None

    def test_context_with_input(self):
        ctx = AgentContext(user_input="排产请求")
        assert ctx.user_input == "排产请求"

    def test_context_with_all_fields(self):
        ctx = AgentContext(
            user_input="测试",
            orders_info="订单1: 产品A",
            machines_info="机器1: 产线A",
            constraints_info="约束1: 最大24h",
            optimization_params={"strategy": "balanced"},
            schedule_result={"task_count": 5},
        )
        assert ctx.orders_info == "订单1: 产品A"
        assert ctx.machines_info == "机器1: 产线A"
        assert ctx.constraints_info == "约束1: 最大24h"
        assert ctx.optimization_params == {"strategy": "balanced"}
        assert ctx.schedule_result == {"task_count": 5}


class TestBaseAPSAgent:
    def test_init_defaults(self):
        agent = BaseAPSAgent(instructions="test instructions", output_type=str)
        assert agent.instructions == "test instructions"
        assert agent.output_type is str
        assert agent._agent is None

    def test_agent_lazy_init(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        assert agent._agent is None
        pydantic_agent = agent.agent
        assert pydantic_agent is not None
        assert agent._agent is not None

    def test_agent_cached(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        agent1 = agent.agent
        agent2 = agent.agent
        assert agent1 is agent2


class TestBuildPrompt:
    def test_prompt_without_context(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        prompt = agent._build_prompt("测试输入", AgentContext())
        assert "测试输入" in prompt

    def test_prompt_with_orders(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(orders_info="订单1: 产品A")
        prompt = agent._build_prompt("测试", ctx)
        assert "订单信息" in prompt
        assert "订单1: 产品A" in prompt

    def test_prompt_with_machines(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(machines_info="机器1: 产线A")
        prompt = agent._build_prompt("测试", ctx)
        assert "机器信息" in prompt

    def test_prompt_with_constraints(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(constraints_info="约束1: 最大24h")
        prompt = agent._build_prompt("测试", ctx)
        assert "约束信息" in prompt

    def test_prompt_with_optimization_params(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(optimization_params={"strategy": "balanced"})
        prompt = agent._build_prompt("测试", ctx)
        assert "优化参数" in prompt

    def test_prompt_with_schedule_result(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(schedule_result={"task_count": 5})
        prompt = agent._build_prompt("测试", ctx)
        assert "排程结果" in prompt

    def test_prompt_with_all_context(self):
        agent = BaseAPSAgent(instructions="test", output_type=str)
        ctx = AgentContext(
            orders_info="订单信息",
            machines_info="机器信息",
            constraints_info="约束信息",
            optimization_params={"key": "val"},
            schedule_result={"key": "val"},
        )
        prompt = agent._build_prompt("完整请求", ctx)
        assert "订单信息" in prompt
        assert "机器信息" in prompt
        assert "约束信息" in prompt
        assert "优化参数" in prompt
        assert "排程结果" in prompt
        assert "完整请求" in prompt
