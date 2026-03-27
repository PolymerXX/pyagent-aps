"""MCP工具注册器"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum


class ToolCategory(str, Enum):
    """工具类别"""

    SCHEDULING = "scheduling"
    ORDER = "order"
    MACHINE = "machine"
    CONSTRAINT = "constraint"
    RESULT = "result"


@dataclass
class ToolMetadata:
    """工具元数据"""

    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)


class MCPToolRegistry:
    """MCP工具注册表"""

    _instance: Optional["MCPToolRegistry"] = None

    def __new__(cls) -> "MCPToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, ToolMetadata] = {}
            cls._instance._handlers: Dict[str, Callable] = {}
        return cls._instance

    def register(
        self,
        name: str,
        description: str,
        category: ToolCategory,
        handler: Callable,
        version: str = "1.0.0",
        requires: Optional[List[str]] = None,
        provides: Optional[List[str]] = None,
        examples: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """注册工具"""
        self._tools[name] = ToolMetadata(
            name=name,
            description=description,
            category=category,
            version=version,
            requires=requires or [],
            provides=provides or [],
            examples=examples or [],
        )
        self._handlers[name] = handler

    def get_handler(self, name: str) -> Optional[Callable]:
        """获取工具处理函数"""
        return self._handlers.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """获取工具元数据"""
        return self._tools.get(name)

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolMetadata]:
        """列出所有工具"""
        tools = list(self._tools.values())
        if category:
            tools = [t for t in tools if t.category == category]
        return tools


registry = MCPToolRegistry()


def tool(
    name: str,
    description: str,
    category: ToolCategory,
    **kwargs,
):
    """工具注册装饰器"""

    def decorator(func: Callable) -> Callable:
        registry.register(
            name=name,
            description=description,
            category=category,
            handler=func,
            **kwargs,
        )
        return func

    return decorator
