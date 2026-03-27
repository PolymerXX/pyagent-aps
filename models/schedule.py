"""排程结果数据模型"""

from enum import Enum
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional


class TaskStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


class TaskAssignment(BaseModel):
    order_id: str = Field(..., description="订单ID")
    machine_id: str = Field(..., description="分配的机器/生产线ID")
    product_name: str = Field(..., description="产品名称")
    product_type: str = Field(..., description="产品类型")
    start_time: float = Field(..., ge=0, description="开始时间（小时）")
    end_time: float = Field(..., ge=0, description="结束时间（小时）")
    quantity: int = Field(..., gt=0, description="生产数量")
    status: TaskStatus = Field(default=TaskStatus.PLANNED, description="任务状态")
    is_on_time: bool = Field(default=True, description="是否按时完成")
    delay_hours: float = Field(default=0.0, description="延期小时数")

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

