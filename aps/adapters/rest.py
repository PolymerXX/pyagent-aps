"""REST API适配器"""

from typing import Any

import httpx

from aps.adapters.base import BaseAdapter, DataConfig
from aps.adapters.parsers import DEFAULT_PRODUCTION_RATE, parse_product_type
from aps.models.machine import ProductionLine
from aps.models.order import Order, Product, ProductType
from aps.models.schedule import ScheduleResult


class RESTAdapter(BaseAdapter):
    """REST API适配器"""

    def __init__(self, config: DataConfig):
        super().__init__(config)
        self.client = httpx.Client(
            base_url=config.api_url,
            timeout=config.timeout,
            headers={"Authorization": f"Bearer {config.api_key}"} if config.api_key else {},
        )

    def get_orders(self, filter: dict[str, Any] | None = None) -> list[Order]:
        try:
            response = self.client.get("/orders", params=filter or {})
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            return [self._parse_order(item) for item in items]
        except httpx.HTTPError:
            return []

    def get_machines(self, filter: dict[str, Any] | None = None) -> list[ProductionLine]:
        try:
            response = self.client.get("/machines", params=filter or {})
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            return [self._parse_machine(item) for item in items]
        except httpx.HTTPError:
            return []

    def push_schedule(self, result: ScheduleResult) -> bool:
        try:
            response = self.client.post("/schedules", json=result.model_dump())
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    def _parse_order(self, data: dict[str, Any]) -> Order:
        product_type_raw = data.get("product_type") or data.get("product")
        try:
            product_type = parse_product_type(product_type_raw)
        except ValueError:
            product_type = ProductType.BEVERAGE

        return Order(
            id=str(data.get("id") or data.get("job_id", "")),
            product=Product(
                id=f"prod_{data.get('id', data.get('job_id', ''))}",
                name=str(data.get("product_name", data.get("product", ""))),
                product_type=product_type,
                production_rate=float(data.get("production_rate", DEFAULT_PRODUCTION_RATE)),
            ),
            quantity=int(data.get("quantity", 0)),
            due_date=int(data.get("due_date", 72)),
            priority=int(data.get("priority", 1)),
            min_start_time=int(data.get("min_start_time", 0)),
        )

    def _parse_machine(self, data: dict[str, Any]) -> ProductionLine:
        raw_types = data.get("supported_product_types") or data.get("supported_products", [])
        supported_types = []
        if isinstance(raw_types, list):
            for t in raw_types:
                try:
                    supported_types.append(parse_product_type(t))
                except ValueError:
                    pass
        elif isinstance(raw_types, str) and raw_types:
            for t in raw_types.split(","):
                t = t.strip()
                if t:
                    try:
                        supported_types.append(parse_product_type(t))
                    except ValueError:
                        pass

        return ProductionLine(
            id=str(data.get("id") or data.get("machine_id", "")),
            name=str(data.get("name", "")),
            capacity_per_hour=float(data.get("capacity_per_hour", 1000)),
            supported_product_types=supported_types,
            setup_time_hours=float(data.get("setup_time_hours", 0.0)),
        )

    def __del__(self):
        if hasattr(self, "client"):
            self.client.close()
