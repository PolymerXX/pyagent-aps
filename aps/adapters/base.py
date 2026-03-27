"""数据适配器基类"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Protocol
from dataclasses import dataclass, field
from datetime import datetime

from aps.models.order import Order
from aps.models.machine import ProductionLine
from aps.models.schedule import ScheduleResult


@dataclass
class DataConfig:
    """数据源配置"""

    source_type: str
    connection_string: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    file_path: Optional[str] = None
    refresh_interval: int = 300
    timeout: int = 30
    retry_count: int = 3
    last_sync: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class DataAdapter(Protocol):
    """数据适配器协议"""

    def get_orders(self, filter: Optional[Dict[str, Any]] = None) -> List[Order]: ...
    def get_machines(
        self, filter: Optional[Dict[str, Any]] = None
    ) -> List[ProductionLine]: ...
    def push_schedule(self, result: ScheduleResult) -> bool: ...
    def health_check(self) -> bool: ...


class BaseAdapter(ABC):
    """适配器基类"""

    def __init__(self, config: DataConfig):
        self.config = config
        self._cache: Dict[str, Any] = {}
        self._last_sync: Optional[datetime] = None

    @abstractmethod
    def get_orders(self, filter: Optional[Dict[str, Any]] = None) -> List[Order]:
        pass

    @abstractmethod
    def get_machines(
        self, filter: Optional[Dict[str, Any]] = None
    ) -> List[ProductionLine]:
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

    def __init__(self, adapters: List[BaseAdapter]):
        self.adapters = adapters

    def get_orders(self, filter: Optional[Dict[str, Any]] = None) -> List[Order]:
        orders = []
        for adapter in self.adapters:
            try:
                orders.extend(adapter.get_orders(filter))
            except Exception:
                continue
        return orders

    def get_machines(
        self, filter: Optional[Dict[str, Any]] = None
    ) -> List[ProductionLine]:
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
