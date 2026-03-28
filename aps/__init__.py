"""APS Agent Package"""

__version__ = "0.1.0"

from .engine.solver import APSSolver
from .models.constraint import DEFAULT_CHANGEOVER_RULES, ProductionConstraints
from .models.machine import ProductionLine
from .models.optimization import ObjectiveWeights, OptimizationParams, OptimizationStrategy
from .models.order import Order, Product, ProductType
from .models.schedule import ScheduleResult, TaskAssignment

__all__ = [
    "__version__",
    "Order", "Product", "ProductType",
    "ProductionLine",
    "ProductionConstraints", "DEFAULT_CHANGEOVER_RULES",
    "ScheduleResult", "TaskAssignment",
    "OptimizationParams", "ObjectiveWeights", "OptimizationStrategy",
    "APSSolver",
]
