"""订单和产品数据模型"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
