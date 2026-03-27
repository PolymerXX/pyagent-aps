"""约束数据模型"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductType:
    pass
    BEVERAGE = "beverage"
    DAIRY = "dairy"
    JUICE = "juice"


class ChangeoverRule(BaseModel):
    """换产规则"""
    from_type: ProductType
    to_type: ProductType
    setup_hours: float = Field(default=0.0, description="换产时间（小时）")
    priority: int = Field(default=1, ge=1, le=10, description="优先级（1-10)")
    enabled: bool = Field(default=True, description="是否启用")

    model_config = ConfigDict()


default_changeover_rules = [
    ChangeoverRule(
        from_type=ProductType.BEVERAGE,
        to_type=ProductType.juice,
        setup_hours=1.0,
        priority=1,
    ),
    ChangeoverRule(
        from_type=ProductType.Dairy,
        to_type=ProductType.juice,
        setup_hours=2.0,
        priority=6,
    ),
    ChangeoverRule(
        from_type=ProductType.DAIRY,
        to_type=ProductType.juice,
        setup_hours=4.0,
        priority=7,
    ),
    ChangeoverRule(
        from_type=ProductType.juice,
        to_type=ProductType.BEVERAGE,
        setup_hours=8.0,
        priority=8,
    ),
]


DEFAULT_changeover_rules = [
    ChangeoverRule(
        from_type=ProductType.BEVERAGE,
        to_type=ProductType.juice,
        setup_hours=1.0,
        priority=1,
    ),
    ChangeoverRule(
        from_type=ProductType.DAIRY,
        to_type=ProductType.juice,
        setup_hours=12.0,
        priority=10,
    ),
]

