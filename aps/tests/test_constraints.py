"""约束模型单元测试"""

import pytest
from pydantic import ValidationError

from aps.models.constraint import DEFAULT_CHANGEOVER_RULES, ChangeoverRule, ProductionConstraints


class TestChangeoverRule:
    """ChangeoverRule模型测试"""

    def test_rule_creation(self, sample_changeover_rule: ChangeoverRule):
        assert sample_changeover_rule.from_type == "beverage"
        assert sample_changeover_rule.to_type == "dairy"
        assert sample_changeover_rule.setup_hours == 1.5
        assert sample_changeover_rule.priority == 5
        assert sample_changeover_rule.enabled is True

    def test_rule_defaults(self):
        rule = ChangeoverRule(from_type="a", to_type="b")
        assert rule.setup_hours == 0.0
        assert rule.priority == 1
        assert rule.enabled is True

    def test_rule_invalid_priority(self):
        with pytest.raises(ValidationError):
            ChangeoverRule(from_type="a", to_type="b", priority=0)

    def test_rule_invalid_setup_hours(self):
        with pytest.raises(ValidationError):
            ChangeoverRule(from_type="a", to_type="b", setup_hours=-1.0)


class TestProductionConstraints:
    """ProductionConstraints模型测试"""

    def test_constraints_creation(self, sample_constraints: ProductionConstraints):
        assert sample_constraints.max_daily_hours == 24.0
        assert sample_constraints.allow_overtime is True
        assert sample_constraints.max_overtime_hours == 4.0

    def test_constraints_defaults(self):
        constraints = ProductionConstraints()
        assert constraints.max_daily_hours == 24.0
        assert constraints.min_break_hours == 0.0
        assert constraints.max_consecutive_hours == 8.0
        assert constraints.allow_overtime is True

    def test_constraints_changeover_rules_default(self):
        constraints = ProductionConstraints()
        assert len(constraints.changeover_rules) > 0

    def test_get_changeover_time_same_product(self, sample_constraints: ProductionConstraints):
        time = sample_constraints.get_changeover_time("beverage", "beverage")
        assert time == 0.0

    def test_get_changeover_time_different_product(self, sample_constraints: ProductionConstraints):
        time = sample_constraints.get_changeover_time("beverage", "juice")
        assert time >= 0.0

    def test_get_changeover_time_not_found(self, sample_constraints: ProductionConstraints):
        time = sample_constraints.get_changeover_time("unknown_type", "another_unknown")
        assert time == 1.0  # 默认换产时间

    def test_constraints_custom_rules(self, sample_changeover_rule: ChangeoverRule):
        constraints = ProductionConstraints(changeover_rules=[sample_changeover_rule])
        assert len(constraints.changeover_rules) == 1
        time = constraints.get_changeover_time("beverage", "dairy")
        assert time == 1.5


class TestDefaultChangeoverRules:
    """默认换产规则测试"""

    def test_default_rules_exist(self):
        assert len(DEFAULT_CHANGEOVER_RULES) > 0

    def test_default_rules_structure(self):
        for rule in DEFAULT_CHANGEOVER_RULES:
            assert isinstance(rule, ChangeoverRule)
            assert rule.from_type is not None
            assert rule.to_type is not None
            assert rule.setup_hours >= 0

    def test_default_rules_beverage_to_juice(self):
        matching = [
            r
            for r in DEFAULT_CHANGEOVER_RULES
            if r.from_type == "beverage" and r.to_type == "juice"
        ]
        assert len(matching) > 0
        assert matching[0].setup_hours == 1.0

    def test_default_rules_dairy_to_juice(self):
        matching = [
            r
            for r in DEFAULT_CHANGEOVER_RULES
            if r.from_type == "dairy" and r.to_type == "juice"
        ]
        assert len(matching) > 0
