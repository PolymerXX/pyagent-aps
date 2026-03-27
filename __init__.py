"""APS Agent Package"""

__version__ = "0.1.0"

from .models.order import Order, Product, ProductType
from .models.machine import ProductionLine
from .models.constraint import ProductionConstraints, DEFAULT_CHANGEOVER_RULES
from .models.schedule import ScheduleResult, TaskAssignment
from .models.optimization import OptimizationParams, ObjectiveWeights, OptimizationStrategy
from .engine.solver import APSSolver

__all__ = [
    "__version__",
    "Order", "Product", "ProductType",
    "ProductionLine",
    "ProductionConstraints", "DEFAULT_CHANGEOVER_RULES",
    "ScheduleResult", "TaskAssignment",
    "OptimizationParams", "ObjectiveWeights", "OptimizationStrategy",
    "APSSolver",
]
