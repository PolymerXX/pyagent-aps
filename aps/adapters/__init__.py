"""数据适配层"""

from aps.adapters.base import DataAdapter, BaseAdapter, DataConfig, CompositeAdapter
from aps.adapters.rest import RESTAdapter
from aps.adapters.database import DatabaseAdapter
from aps.adapters.file import FileAdapter

__all__ = [
    "DataAdapter",
    "BaseAdapter",
    "DataConfig",
    "CompositeAdapter",
    "RESTAdapter",
    "DatabaseAdapter",
    "FileAdapter",
]
