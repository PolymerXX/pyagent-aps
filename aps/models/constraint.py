"""约束数据模型"""

from pydantic import BaseModel, ConfigDict, Field


class ChangeoverRule(BaseModel):
    """换产规则"""

    from_type: str = Field(..., description="源产品类型")
    to_type: str = Field(..., description="目标产品类型")
    setup_hours: float = Field(default=0.0, ge=0.0, description="换产时间（小时）")
    priority: int = Field(default=1, ge=1, le=10, description="优先级（1-10)")
    enabled: bool = Field(default=True, description="是否启用")

    model_config = ConfigDict()


DEFAULT_CHANGEOVER_RULES: list[ChangeoverRule] = [
    ChangeoverRule(
        from_type="beverage",
        to_type="juice",
        setup_hours=1.0,
        priority=1,
    ),
    ChangeoverRule(
        from_type="dairy",
        to_type="juice",
        setup_hours=2.0,
        priority=6,
    ),
    ChangeoverRule(
        from_type="dairy",
        to_type="water",
        setup_hours=4.0,
        priority=7,
    ),
    ChangeoverRule(
        from_type="juice",
        to_type="beverage",
        setup_hours=8.0,
        priority=8,
    ),
]


class ProductionConstraints(BaseModel):
    """生产约束配置"""

    max_daily_hours: float = Field(default=24.0, ge=0.0, description="每日最大生产小时数")
    min_break_hours: float = Field(default=0.0, ge=0.0, description="最小休息时间")
    max_consecutive_hours: float = Field(default=8.0, ge=0.0, description="最大连续工作小时数")
    allow_overtime: bool = Field(default=True, description="是否允许加班")
    max_overtime_hours: float = Field(default=4.0, ge=0.0, description="最大加班小时数")
    changeover_rules: list[ChangeoverRule] = Field(
        default_factory=lambda: DEFAULT_CHANGEOVER_RULES.copy(), description="换产规则列表"
    )

    model_config = ConfigDict()

    def get_changeover_time(self, from_type: str, to_type: str) -> float:
        """获取换产时间"""
        if from_type == to_type:
            return 0.0

        for rule in self.changeover_rules:
            if rule.from_type == from_type and rule.to_type == to_type:
                return rule.setup_hours

        return 1.0
