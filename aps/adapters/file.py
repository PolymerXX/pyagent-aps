"""文件适配器"""

import json
from pathlib import Path
from typing import Any

from aps.adapters.base import BaseAdapter, DataConfig
from aps.models.machine import ProductionLine
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult


class FileAdapter(BaseAdapter):
    """文件适配器"""

    def __init__(self, config: DataConfig):
        super().__init__(config)
        self.file_path = Path(config.file_path or ".")
        self._data: dict[str, Any] = {}
        self._load_data()

    def _load_data(self) -> None:
        if not self.file_path.exists():
            self._data = {"orders": [], "machines": []}
            return

        if self.file_path.is_file() and self.file_path.suffix == ".json":
            with open(self.file_path, encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {"orders": [], "machines": []}

    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]:
        orders_data = self._data.get("orders", [])
        return [self._parse_order(item) for item in orders_data]

    def get_machines(
        self, filter: dict[str, Any] | None = None
    ) -> list[ProductionLine]:
        machines_data = self._data.get("machines", [])
        return [self._parse_machine(item) for item in machines_data]

    def push_schedule(self, result: ScheduleResult) -> bool:
        output_path = (
            self.file_path.parent
            / f"schedule_{result.model_dump().get('schedule_id', 'new')}.json"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, ensure_ascii=False, indent=2)
        return True

    def _parse_order(self, data: dict[str, Any]) -> Order:
        return Order(
            id=str(data.get("id") or data.get("job_id", "")),
            product=Product(
                name=str(data.get("product", "")), product_type=ProductType.COLA
            ),
            quantity=int(data.get("quantity", 0)),
            due_date=float(data.get("due_date", 72.0)),
        )

    def _parse_machine(self, data: dict[str, Any]) -> ProductionLine:
        return ProductionLine(
            id=str(data.get("id") or data.get("machine_id", "")),
            name=str(data.get("name", "")),
            capacity_per_hour=int(data.get("capacity_per_hour", 1000)),
        )
