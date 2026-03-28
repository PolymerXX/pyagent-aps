"""优化参数数据模型"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class OptimizationStrategy(str, Enum):
    BALANCED = "balanced"
    ON_TIME_DELIVERY = "on_time"
    MINIMIZE_CHANGEOVER = "min_changeover"
    MAXIMIZE_PROFIT = "max_profit"
    MAX_UTILIZATION = "max_utilization"


class ObjectiveWeights(BaseModel):
    """优化目标权重"""

    on_time: float = Field(default=0.4, ge=0.0, le=1.0, description="准时交付权重")
    changeover: float = Field(default=0.2, ge=0.0, le=1.0, description="最小换产权重")
    utilization: float = Field(default=0.2, ge=0.0, le=1.0, description="设备利用率权重")
    profit: float = Field(default=0.2, ge=0.0, le=1.0, description="利润权重")

    @property
    def total(self) -> float:
        return self.on_time + self.changeover + self.utilization + self.profit

    def normalize(self) -> "ObjectiveWeights":
        total = self.on_time + self.changeover + self.utilization + self.profit
        if total == 0:
            return ObjectiveWeights()
        return ObjectiveWeights(
            on_time=self.on_time / total,
            changeover=self.changeover / total,
            utilization=self.utilization / total,
            profit=self.profit / total,
        )


class OptimizationParams(BaseModel):
    strategy: OptimizationStrategy = Field(default=OptimizationStrategy.BALANCED)
    time_limit_seconds: int = Field(default=60, ge=1, le=3600, description="求解时间限制（秒）")
    weights: ObjectiveWeights = Field(default_factory=ObjectiveWeights)
    planning_horizon_hours: int = Field(default=168, ge=1, le=7200, description="计划周期（小时）")
    allow_late_delivery: bool = Field(default=True)
    max_late_hours: int = Field(default=8, description="最大允许延迟小时数")

    model_config = ConfigDict()
