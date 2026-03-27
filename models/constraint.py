"""约束数据模型"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict
from aps.models.order import ProductType


DEFAULT_CHANGEOVER_RULES: Dict[str, Dict[str, float]] = {
    "beverage": {"dairy": 2.0, "juice": 0.5, "beverage": 0.0},
    "dairy": {"beverage": 1.5, "juice": 2.0,    },
}


DEFAULT_CHANGEOVER_RULES = DEFAULT_CHANGEOVER_RULES


class ProductionConstraints(BaseModel):
    max_continuous_hours: int = Field(default=24, description="最大连续生产时间")
    min_break_hours: int = Field(default=2, description="最小休息时间")
    changeover_rules: Dict[str, Dict[str, float]] = Field(
        default_factory=lambda: DEFAULT_CHANGEOVER_RULES,
        description="换产规则矩阵"
    )
    max_late_hours: int = Field(default=8, description="最大允许延迟小时数")
    
    def get_changeover_time(self, from_type: str, to_type: str) -> float:
        if from_type == to_type:
            return 0.0
        return self.changeover_rules.get(from_type, {}).get(to_type, 1.0)

    model_config = ConfigDict()


class Constraint(BaseModel):
    id: str
    type: str
    params: dict = Field(default_factory=dict)
    priority: int = Field(default=1)
    enabled: bool = Field(default=True)
    model_config = ConfigDict()
