"""Engine模块单元测试 - cache和profiler"""

import time

from aps.engine.cache import SolverCache, clear_solver_cache, compute_order_hash, get_solver_cache
from aps.engine.profiler import PerformanceMetrics, Profiler, get_profiler, reset_profiler
from aps.models.machine import MachineStatus, ProductionLine
from aps.models.order import Order, Product, ProductType


class TestSolverCache:
    """SolverCache测试类"""

    def test_init_default(self):
        cache = SolverCache()
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert cache._cache == {}
        assert cache._hits == 0
        assert cache._misses == 0

    def test_init_custom(self):
        cache = SolverCache(max_size=50, ttl_seconds=600)
        assert cache.max_size == 50
        assert cache.ttl_seconds == 600

    def test_compute_key(self, sample_orders, sample_machines, sample_constraints, sample_params):
        cache = SolverCache()
        key = cache._compute_key(sample_orders, sample_machines, sample_constraints, sample_params)
        assert isinstance(key, str)
        assert len(key) > 0
        assert ":" in key

    def test_compute_key_consistency(
        self, sample_orders, sample_machines, sample_constraints, sample_params
    ):
        cache = SolverCache()
        key1 = cache._compute_key(sample_orders, sample_machines, sample_constraints, sample_params)
        key2 = cache._compute_key(sample_orders, sample_machines, sample_constraints, sample_params)
        assert key1 == key2

    def test_get_miss(self, sample_orders, sample_machines, sample_constraints, sample_params):
        cache = SolverCache()
        result = cache.get(sample_orders, sample_machines, sample_constraints, sample_params)
        assert result is None
        assert cache._misses == 1
        assert cache._hits == 0

    def test_set_and_get(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache()
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)

        result = cache.get(sample_orders, sample_machines, sample_constraints, sample_params)
        assert result is not None
        assert result == sample_result
        assert cache._hits == 1
        assert cache._misses == 0

    def test_get_expired(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache(ttl_seconds=0.01)
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)

        time.sleep(0.02)

        result = cache.get(sample_orders, sample_machines, sample_constraints, sample_params)
        assert result is None
        assert cache._misses == 1

    def test_max_size_eviction(self, sample_constraints, sample_params, sample_result):
        cache = SolverCache(max_size=2)

        order1 = Order(
            id="O1",
            product=Product(
                id="P1", name="P1", product_type=ProductType.BEVERAGE, production_rate=100
            ),
            quantity=100,
            due_date=10,
        )
        order2 = Order(
            id="O2",
            product=Product(
                id="P2", name="P2", product_type=ProductType.BEVERAGE, production_rate=100
            ),
            quantity=100,
            due_date=10,
        )
        order3 = Order(
            id="O3",
            product=Product(
                id="P3", name="P3", product_type=ProductType.BEVERAGE, production_rate=100
            ),
            quantity=100,
            due_date=10,
        )
        machine = ProductionLine(
            id="M1",
            name="M1",
            supported_product_types=[ProductType.BEVERAGE],
            capacity_per_hour=100,
            setup_time_hours=0.5,
            status=MachineStatus(machine_id="M1", status="active"),
        )

        cache.set([order1], [machine], sample_constraints, sample_params, sample_result)
        cache.set([order2], [machine], sample_constraints, sample_params, sample_result)
        cache.set([order3], [machine], sample_constraints, sample_params, sample_result)

        assert len(cache._cache) == 2

    def test_clear(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache()
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)
        cache._hits = 5
        cache._misses = 3

        cache.clear()

        assert cache._cache == {}
        assert cache._hits == 0
        assert cache._misses == 0

    def test_hit_rate_empty(self):
        cache = SolverCache()
        assert cache.hit_rate == 0.0

    def test_hit_rate_all_hits(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache()
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)
        cache.get(sample_orders, sample_machines, sample_constraints, sample_params)
        cache.get(sample_orders, sample_machines, sample_constraints, sample_params)

        assert cache.hit_rate == 1.0

    def test_hit_rate_mixed(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache()
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)
        cache.get(sample_orders, sample_machines, sample_constraints, sample_params)
        cache.get([], [], sample_constraints, sample_params)

        assert cache.hit_rate == 0.5

    def test_stats(
        self, sample_orders, sample_machines, sample_constraints, sample_params, sample_result
    ):
        cache = SolverCache()
        cache.set(sample_orders, sample_machines, sample_constraints, sample_params, sample_result)
        cache.get(sample_orders, sample_machines, sample_constraints, sample_params)

        stats = cache.stats
        assert stats["size"] == 1
        assert stats["max_size"] == 100
        assert stats["hits"] == 1
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 1.0


class TestGlobalCache:
    """全局缓存函数测试"""

    def test_get_solver_cache_singleton(self):
        clear_solver_cache()
        cache1 = get_solver_cache()
        cache2 = get_solver_cache()
        assert cache1 is cache2

    def test_clear_solver_cache(self):
        cache = get_solver_cache()
        cache._hits = 10
        clear_solver_cache()
        assert cache._hits == 0

    def test_compute_order_hash(self):
        hash1 = compute_order_hash("O001", 1000, 24.0)
        hash2 = compute_order_hash("O001", 1000, 24.0)
        hash3 = compute_order_hash("O002", 1000, 24.0)

        assert hash1 == hash2
        assert hash1 != hash3


class TestPerformanceMetrics:
    """PerformanceMetrics测试类"""

    def test_init(self):
        metrics = PerformanceMetrics()
        assert metrics.solve_count == 0
        assert metrics.total_solve_time == 0.0
        assert metrics.avg_solve_time == 0.0
        assert metrics.min_solve_time == float("inf")
        assert metrics.max_solve_time == 0.0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0

    def test_record_solve(self):
        metrics = PerformanceMetrics()

        metrics.record_solve(1.5)
        assert metrics.solve_count == 1
        assert metrics.total_solve_time == 1.5
        assert metrics.avg_solve_time == 1.5
        assert metrics.min_solve_time == 1.5
        assert metrics.max_solve_time == 1.5

        metrics.record_solve(2.5)
        assert metrics.solve_count == 2
        assert metrics.total_solve_time == 4.0
        assert metrics.avg_solve_time == 2.0
        assert metrics.min_solve_time == 1.5
        assert metrics.max_solve_time == 2.5

    def test_record_solve_recent_times(self):
        metrics = PerformanceMetrics(max_recent_count=3)

        metrics.record_solve(1.0)
        metrics.record_solve(2.0)
        metrics.record_solve(3.0)
        metrics.record_solve(4.0)

        assert len(metrics.recent_solve_times) == 3
        assert metrics.recent_solve_times == [2.0, 3.0, 4.0]

    def test_record_cache_hit(self):
        metrics = PerformanceMetrics()
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        assert metrics.cache_hits == 2

    def test_record_cache_miss(self):
        metrics = PerformanceMetrics()
        metrics.record_cache_miss()
        assert metrics.cache_misses == 1

    def test_cache_hit_rate_empty(self):
        metrics = PerformanceMetrics()
        assert metrics.cache_hit_rate == 0.0

    def test_cache_hit_rate_calculated(self):
        metrics = PerformanceMetrics()
        metrics.record_cache_hit()
        metrics.record_cache_hit()
        metrics.record_cache_miss()
        assert metrics.cache_hit_rate == 2 / 3

    def test_recent_avg_time_empty(self):
        metrics = PerformanceMetrics()
        assert metrics.recent_avg_time == 0.0

    def test_recent_avg_time_calculated(self):
        metrics = PerformanceMetrics()
        metrics.record_solve(2.0)
        metrics.record_solve(4.0)
        assert metrics.recent_avg_time == 3.0

    def test_to_dict(self):
        metrics = PerformanceMetrics()
        metrics.record_solve(1.5)
        metrics.record_cache_hit()

        d = metrics.to_dict()
        assert d["solve_count"] == 1
        assert d["total_solve_time"] == 1.5
        assert d["cache_hits"] == 1
        assert "avg_solve_time" in d
        assert "cache_hit_rate" in d


class TestProfiler:
    """Profiler测试类"""

    def test_init(self):
        profiler = Profiler()
        assert profiler.metrics.solve_count == 0
        assert profiler._start_time is None

    def test_measure_solve(self):
        profiler = Profiler()

        with profiler.measure("solve"):
            time.sleep(0.01)

        assert profiler.metrics.solve_count == 1
        assert profiler.metrics.total_solve_time > 0

    def test_measure_other_operation(self):
        profiler = Profiler()

        with profiler.measure("other"):
            time.sleep(0.01)

        assert profiler.metrics.solve_count == 0

    def test_record_result_cache_hit(self, sample_result):
        profiler = Profiler()
        profiler.record_result(sample_result, from_cache=True)
        assert profiler.metrics.cache_hits == 1

    def test_record_result_cache_miss(self, sample_result):
        profiler = Profiler()
        profiler.record_result(sample_result, from_cache=False)
        assert profiler.metrics.cache_misses == 1

    def test_get_report(self, sample_result):
        profiler = Profiler()
        profiler.metrics.record_solve(1.0)
        profiler.metrics.record_cache_hit()

        report = profiler.get_report()

        assert "performance" in report
        assert "timestamp" in report

    def test_reset(self):
        profiler = Profiler()
        profiler.metrics.record_solve(1.0)
        profiler.metrics.record_cache_hit()

        profiler.reset()

        assert profiler.metrics.solve_count == 0
        assert profiler.metrics.cache_hits == 0


class TestGlobalProfiler:
    """全局profiler函数测试"""

    def test_get_profiler_singleton(self):
        reset_profiler()
        p1 = get_profiler()
        p2 = get_profiler()
        assert p1 is p2

    def test_reset_profiler(self):
        profiler = get_profiler()
        profiler.metrics.record_solve(1.0)
        reset_profiler()
        assert profiler.metrics.solve_count == 0
