"""生产线和机器数据模型"""

from aps.models.order import Order, Product, ProductType
from pydantic import BaseModel, ConfigDict, Field


class MachineStatus(BaseModel):
    machine_id: str = Field(default="", description="机器ID")
    status: str = Field(default="idle", description="状态")
    current_task: str | None = Field(default=None, description="当前任务")
    completed_tasks: int = Field(default=0, description="已完成任务数")
    uptime_hours: float = Field(default=0.0, description="运行时间（小时）")
    last_maintenance: str | None = Field(default=None, description="最后维护时间")

    model_config = ConfigDict()


class ProductionLine(BaseModel):
    """生产线/机器模型"""

    id: str = Field(..., description="生产线ID")
    name: str = Field(default="", description="生产线名称")
    supported_product_types: list = Field(default_factory=list, description="支持的产品类型列表")
    capacity_per_hour: float = Field(default=1000.0, description="每小时产能")
    setup_time_hours: float = Field(default=0.0, description="换产时间（小时）")
    status: MachineStatus = Field(default_factory=MachineStatus, description="机器状态")

    def can_produce(self, product_type) -> bool:
        """检查是否可以生产该产品类型"""
        return product_type in self.supported_product_types
