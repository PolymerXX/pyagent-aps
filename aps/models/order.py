"""订单数据模型"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ProductType(str, Enum):
    """产品类型"""

    COLA = "cola"
    MILK = "milk"
    ORANGE_JUICE = "orange_juice"
    WATER = "water"
    DAIRY = "dairy"
    JUICE = "juice"
    BEVERAGE = "beverage"


class Product(BaseModel):
    """产品信息"""

    name: str = Field(..., description="产品名称")
    product_type: ProductType = Field(..., description="产品类型")
    unit_profit: float = Field(default=1.0, ge=0, description="单位利润")


class Order(BaseModel):
    """生产订单"""

    id: str = Field(..., description="订单ID")
    product: Product = Field(..., description="产品信息")
    quantity: int = Field(..., gt=0, description="数量")
    due_date: float = Field(default=72.0, ge=0, description="截止时间（小时）")
    min_start_time: float = Field(default=0.0, ge=0, description="最早开始时间")

    @property
    def estimated_production_hours(self) -> float:
        """估算生产时间（基于1000/小时的默认产能）"""
        return self.quantity / 1000.0
