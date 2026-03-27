"""订单和产品数据模型"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProductType(str, Enum):
    BEVERAGE = "beverage"
    DAIRY = "dairy"
    JUICE = "juice"


class Product(BaseModel):
    id: str = Field(..., description="产品唯一标识")
    name: str = Field(..., description="产品名称")
    product_type: ProductType = Field(..., description="产品类型")
    production_rate: float = Field(..., description="生产速率（瓶/小时）")
    unit_profit: float = Field(default=0.0, description="单位利润")

    model_config = ConfigDict()


class Order(BaseModel):
    id: str = Field(..., description="订单唯一标识")
    product: Product = Field(..., description="产品信息")
    quantity: int = Field(..., gt=0, description="订单数量（瓶）")
    due_date: int = Field(..., description="截止时间(相对于时间0的小时数)")
    priority: int = Field(default=1, ge=1, le=10, description="优先级（1-10，10最高)")
    min_start_time: int = Field(default=0, ge=0, description="最早开始时间")

    @property
    def estimated_production_hours(self) -> float:
        return self.quantity / self.product.production_rate

    model_config = ConfigDict()


class MachineStatus(BaseModel):
    machine_id: str
    status: str
    current_task: Optional[str] = None
    completed_tasks: int = Field(default=0, description="已完成任务数")
    uptime_hours: float = Field(default=0.0, description="运行时间（小时）")
    last_maintenance: Optional[str] = Field(default=None, description="最后维护时间")

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
