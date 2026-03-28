"""数据适配器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from aps.models.machine import ProductionLine
from aps.models.order import Order
from aps.models.schedule import ScheduleResult


@dataclass
class DataConfig:
    """数据源配置"""

    source_type: str
    connection_string: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    file_path: str | None = None
    refresh_interval: int = 300
    timeout: int = 30
    retry_count: int = 3
    last_sync: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class DataAdapter(Protocol):
    """数据适配器协议"""

    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]: ...
    def get_machines(
        self, filter: dict[str, Any] | None = None
    ) -> list[ProductionLine]: ...
    def push_schedule(self, result: ScheduleResult) -> bool: ...
    def health_check(self) -> bool: ...


class BaseAdapter(ABC):
    """适配器基类"""

    def __init__(self, config: DataConfig):
        self.config = config
        self._cache: dict[str, Any] = {}
        self._last_sync: datetime | None = None

    @abstractmethod
    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]:
        pass

    @abstractmethod
    def get_machines(
        self, filter: dict[str, Any] | None = None
    ) -> list[ProductionLine]:
        pass

    @abstractmethod
    def push_schedule(self, result: ScheduleResult) -> bool:
        pass

    def health_check(self) -> bool:
        try:
            self.get_machines()
            return True
        except Exception:
            return False


class CompositeAdapter(BaseAdapter):
    """组合适配器"""

    def __init__(self, adapters: list[BaseAdapter]):
        self.adapters = adapters

    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]:
        orders = []
        for adapter in self.adapters:
            try:
                orders.extend(adapter.get_orders(filter))
            except Exception:
                continue
        return orders

    def get_machines(
        self, filter: dict[str, Any] | None = None
    ) -> list[ProductionLine]:
        machines = []
        for adapter in self.adapters:
            try:
                machines.extend(adapter.get_machines(filter))
            except Exception:
                continue
        return machines

    def push_schedule(self, result: ScheduleResult) -> bool:
        if self.adapters:
            return self.adapters[0].push_schedule(result)
        return False
