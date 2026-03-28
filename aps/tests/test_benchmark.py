"""性能基准测试"""

import time

import pytest

from aps.engine.solver import APSSolver
from aps.models.constraint import ProductionConstraints
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.optimization import OptimizationParams, OptimizationStrategy
from aps.models.order import Order, Product, ProductType


def generate_orders(count: int, base_id: int = 0) -> list[Order]:
    """生成测试订单"""
    orders = []
    products = [
        Product(
            id=f"P{i}", name=f"产品{i}", product_type=ProductType.BEVERAGE, production_rate=100.0
        )
        for i in range(5)
    ]
    for i in range(count):
        orders.append(
            Order(
                id=f"O{base_id + i:04d}",
                product=products[i % 5],
                quantity=500 + (i * 100) % 1000,
                due_date=24 + (i % 10) * 12,
            )
        )
    return orders


def generate_machines(count: int) -> list[ProductionLine]:
    """生成测试机器"""
    machines = []
    for i in range(count):
        machines.append(
            ProductionLine(
                id=f"M{i:03d}",
                name=f"产线{i + 1}",
                supported_product_types=list(ProductType),
                capacity_per_hour=50.0 + i * 10,
                setup_time_hours=1.0,
                status=MachineStatus(machine_id=f"M{i:03d}", status="active"),
            )
        )
    return machines


class TestBenchmark:
    """性能基准测试类"""

    @pytest.fixture
    def constraints(self):
        return ProductionConstraints()

    @pytest.fixture
    def params(self):
        return OptimizationParams(strategy=OptimizationStrategy.BALANCED)

    def test_small_scale(self, constraints, params):
        """小规模: 10订单 x 3机器"""
        orders = generate_orders(10)
        machines = generate_machines(3)
        start = time.time()
        solver = APSSolver(
            orders=orders,
            machines=machines,
            constraints=constraints,
            params=params,
            use_cp_sat=False,
        )
        result = solver.solve()
        elapsed = time.time() - start
        assert result.task_count == 10
        assert elapsed < 0.1, f"Small scale took {elapsed:.3f}s, expected <0.1s"
        print(f"\n小规模: {elapsed:.4f}s, {result.task_count} tasks")

    def test_medium_scale(self, constraints, params):
        """中规模: 50订单 x 5机器"""
        orders = generate_orders(50)
        machines = generate_machines(5)
        start = time.time()
        solver = APSSolver(
            orders=orders,
            machines=machines,
            constraints=constraints,
            params=params,
            use_cp_sat=False,
        )
        result = solver.solve()
        elapsed = time.time() - start
        assert result.task_count == 50
        assert elapsed < 1.0, f"Medium scale took {elapsed:.3f}s, expected <1s"
        print(f"\n中规模: {elapsed:.4f}s, {result.task_count} tasks")

    def test_large_scale(self, constraints, params):
        """大规模: 200订单 x 10机器"""
        orders = generate_orders(200)
        machines = generate_machines(10)
        start = time.time()
        solver = APSSolver(
            orders=orders,
            machines=machines,
            constraints=constraints,
            params=params,
            use_cp_sat=False,
        )
        result = solver.solve()
        elapsed = time.time() - start
        assert result.task_count == 200
        assert elapsed < 10.0, f"Large scale took {elapsed:.3f}s, expected <10s"
        print(f"\n大规模: {elapsed:.4f}s, {result.task_count} tasks")

    def test_solution_quality_small(self, constraints, params):
        """小规模解质量评估"""
        orders = generate_orders(10)
        machines = generate_machines(3)
        solver = APSSolver(
            orders=orders,
            machines=machines,
            constraints=constraints,
            params=params,
            use_cp_sat=False,
        )
        result = solver.solve()
        on_time_rate = result.on_time_delivery_rate
        assert on_time_rate >= 0.5, f"On-time rate {on_time_rate:.2%} < 50%"
        print(f"\n准时率: {on_time_rate:.2%}")

    def test_repeated_solving(self, constraints, params):
        """重复求解性能"""
        orders = generate_orders(20)
        machines = generate_machines(4)
        times = []
        for _ in range(5):
            start = time.time()
            solver = APSSolver(
                orders=orders,
                machines=machines,
                constraints=constraints,
                params=params,
                use_cp_sat=False,
            )
            solver.solve()
            times.append(time.time() - start)
        avg_time = sum(times) / len(times)
        assert avg_time < 0.5, f"Average time {avg_time:.3f}s > 0.5s"
        print(f"\n5次平均: {avg_time:.4f}s")

    def test_empty_inputs(self, params):
        """空输入性能"""
        constraints = ProductionConstraints()
        start = time.time()
        solver = APSSolver(orders=[], machines=[], constraints=constraints, params=params)
        result = solver.solve()
        elapsed = time.time() - start
        assert result.task_count == 0
        assert elapsed < 0.01
        print(f"\n空输入: {elapsed:.6f}s")


class TestBenchmarkReport:
    """基准测试报告"""

    def test_full_report(self):
        """生成完整性能报告"""
        constraints = ProductionConstraints()
        params = OptimizationParams(strategy=OptimizationStrategy.BALANCED)
        configs = [
            ("tiny", 5, 2),
            ("small", 10, 3),
            ("medium", 50, 5),
            ("large", 200, 10),
        ]
        results = []
        print("\n" + "=" * 70)
        print("APS Performance Benchmark Report")
        print("=" * 70)
        for name, order_count, machine_count in configs:
            orders = generate_orders(order_count)
            machines = generate_machines(machine_count)
            start = time.time()
            solver = APSSolver(
                orders=orders,
                machines=machines,
                constraints=constraints,
                params=params,
                use_cp_sat=False,
            )
            result = solver.solve()
            elapsed = time.time() - start
            results.append(
                {
                    "name": name,
                    "orders": order_count,
                    "machines": machine_count,
                    "time": elapsed,
                    "tasks": result.task_count,
                    "on_time_rate": result.on_time_delivery_rate,
                    "makespan": result.total_makespan,
                }
            )
        header = (
            f"\n{'Name':<10} {'Orders':<8} {'Machines':<10} {'Time(s)':<12} "
            f"{'Tasks':<8} {'On-Time':<10} {'Makespan':<10}"
        )
        print(header)
        print("-" * 68)
        for r in results:
            row = (
                f"{r['name']:<10} {r['orders']:<8} {r['machines']:<10} "
                f"{r['time']:<12.4f} {r['tasks']:<8} {r['on_time_rate']:<10.1%} "
                f"{r['makespan']:<10.1f}h"
            )
            print(row)
        print("=" * 70)
        assert all(r["tasks"] == r["orders"] for r in results)
