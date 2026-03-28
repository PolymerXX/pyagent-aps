"""数据适配层"""

from aps.adapters.base import BaseAdapter, CompositeAdapter, DataAdapter, DataConfig
from aps.adapters.database import DatabaseAdapter
from aps.adapters.file import FileAdapter
from aps.adapters.rest import RESTAdapter

__all__ = [
    "DataAdapter",
    "BaseAdapter",
    "DataConfig",
    "CompositeAdapter",
    "RESTAdapter",
    "DatabaseAdapter",
    "FileAdapter",
]
