"""排程结果数据模型"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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


class ScheduleExplanation(BaseModel):
    """排程解释"""
    summary: str = Field(default="", description="排程摘要")
    key_decisions: list[str] = Field(default_factory=list, description="关键决策")
    risks: list[str] = Field(default_factory=list, description="风险提示")
    alternatives: list[str] = Field(default_factory=list, description="备选方案")


class ScheduleResult(BaseModel):
    """排程结果"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    assignments: list[TaskAssignment] = Field(default_factory=list, description="任务分配列表")
    total_makespan: float = Field(default=0.0, description="总完工时间（小时）")
    on_time_delivery_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="准时交付率")
    total_changeover_time: float = Field(default=0.0, description="总换产时间（小时）")
    machine_utilization: dict = Field(default_factory=dict, description="机器利用率")
    planning_time_seconds: float = Field(default=0.0, description="规划耗时（秒）")
    is_optimal: bool = Field(default=False, description="是否最优解")
    explanation: ScheduleExplanation | None = Field(default=None, description="排程解释")

    @property
    def task_count(self) -> int:
        """任务数量"""
        return len(self.assignments)

    @property
    def on_time_count(self) -> int:
        """准时任务数量"""
        return sum(1 for a in self.assignments if a.is_on_time)

    @property
    def delayed_count(self) -> int:
        """延期任务数量"""
        return sum(1 for a in self.assignments if not a.is_on_time)

    def get_assignments_by_machine(self, machine_id: str) -> list[TaskAssignment]:
        """获取指定机器的任务分配"""
        return [a for a in self.assignments if a.machine_id == machine_id]

    def get_sorted_assignments(self) -> list[TaskAssignment]:
        """获取按开始时间排序的任务分配"""
        return sorted(self.assignments, key=lambda a: a.start_time)

