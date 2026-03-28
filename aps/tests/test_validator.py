"""ValidatorAgent 单元测试 - 不依赖LLM"""

import pytest

from aps.agents.validator import ConstraintViolation, ValidationResult, ValidatorAgent
from aps.models.schedule import ScheduleResult, TaskAssignment, TaskStatus


@pytest.fixture
def validator():
    return ValidatorAgent()


@pytest.fixture
def good_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0,
                end_time=10,
                quantity=1000,
                status=TaskStatus.PLANNED,
                is_on_time=True,
            ),
            TaskAssignment(
                order_id="O002",
                machine_id="M001",
                product_name="牛奶",
                product_type="dairy",
                start_time=10.5,
                end_time=15,
                quantity=500,
                status=TaskStatus.PLANNED,
            ),
        ],
        total_makespan=15.0,
        on_time_delivery_rate=1.0,
        machine_utilization={"M001": 0.8},
    )


@pytest.fixture
def delayed_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0,
                end_time=10,
                quantity=1000,
                status=TaskStatus.PLANNED,
                is_on_time=True,
            ),
            TaskAssignment(
                order_id="O002",
                machine_id="M001",
                product_name="牛奶",
                product_type="dairy",
                start_time=10.5,
                end_time=18.0,
                quantity=500,
                status=TaskStatus.PLANNED,
                is_on_time=False,
                delay_hours=6.0,
            ),
        ],
        total_makespan=18.0,
        on_time_delivery_rate=0.5,
        total_changeover_time=4.0,
        machine_utilization={"M001": 1.0},
    )


@pytest.fixture
def empty_result():
    return ScheduleResult(assignments=[])


@pytest.fixture
def high_util_result():
    return ScheduleResult(
        assignments=[
            TaskAssignment(
                order_id="O001",
                machine_id="M001",
                product_name="可乐",
                product_type="beverage",
                start_time=0,
                end_time=10,
                quantity=1000,
                status=TaskStatus.PLANNED,
            ),
        ],
        total_makespan=10.0,
        machine_utilization={"M001": 0.96},
    )


class TestQuickValidate:
    def test_valid_result(self, validator, good_result):
        result = validator.quick_validate(good_result)
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.overall_status == "normal"
        assert result.quality_score >= 0.8

    def test_delayed_result(self, validator, delayed_result):
        result = validator.quick_validate(delayed_result)
        assert isinstance(result, ValidationResult)
        assert len(result.warnings) > 0

    def test_empty_result(self, validator, empty_result):
        result = validator.quick_validate(empty_result)
        assert isinstance(result, ValidationResult)
        assert result.quality_score == 0.0

    def test_high_util_result(self, validator, high_util_result):
        result = validator.quick_validate(high_util_result)
        assert isinstance(result, ValidationResult)
        has_capacity_violation = any(v.type == "capacity" for v in result.constraint_violations)
        assert has_capacity_violation


class TestCheckConstraintViolations:
    def test_no_violations(self, validator, good_result):
        violations = validator._check_constraint_violations(good_result)
        assert len(violations) == 0

    def test_due_date_violation(self, validator, delayed_result):
        violations = validator._check_constraint_violations(delayed_result)
        due_violations = [v for v in violations if v.type == "due_date"]
        assert len(due_violations) == 1
        assert due_violations[0].severity == "error"
        assert due_violations[0].order_id == "O002"

    def test_capacity_violation(self, validator, high_util_result):
        violations = validator._check_constraint_violations(high_util_result)
        cap_violations = [v for v in violations if v.type == "capacity"]
        assert len(cap_violations) == 1
        assert cap_violations[0].severity == "warning"

    def test_severe_capacity_violation(self, validator):
        result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=10,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                ),
            ],
            total_makespan=10.0,
            machine_utilization={"M001": 0.99},
        )
        violations = validator._check_constraint_violations(result)
        cap_violations = [v for v in violations if v.type == "capacity"]
        assert len(cap_violations) == 1
        assert cap_violations[0].severity == "error"


class TestGenerateWarnings:
    def test_no_warnings(self, validator, good_result):
        warnings = validator._generate_warnings(good_result)
        assert len(warnings) == 0

    def test_delayed_warning(self, validator, delayed_result):
        warnings = validator._generate_warnings(delayed_result)
        assert any("延期" in w for w in warnings)

    def test_high_util_warning(self, validator, high_util_result):
        warnings = validator._generate_warnings(high_util_result)
        assert any("负载过高" in w for w in warnings)

    def test_changeover_warning(self, validator):
        result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=10,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                ),
            ],
            total_makespan=10.0,
            total_changeover_time=3.0,
            machine_utilization={"M001": 0.5},
        )
        warnings = validator._generate_warnings(result)
        assert any("换产" in w for w in warnings)


class TestCalculateQualityScore:
    def test_good_score(self, validator, good_result):
        score = validator._calculate_quality_score(good_result)
        assert 0.8 <= score <= 1.0

    def test_empty_score(self, validator, empty_result):
        score = validator._calculate_quality_score(empty_result)
        assert score == 0.0

    def test_delayed_score(self, validator, delayed_result):
        score = validator._calculate_quality_score(delayed_result)
        assert 0.0 < score < 0.8

    def test_score_bounded(self, validator):
        result = ScheduleResult(
            assignments=[
                TaskAssignment(
                    order_id="O001",
                    machine_id="M001",
                    product_name="可乐",
                    product_type="beverage",
                    start_time=0,
                    end_time=10,
                    quantity=1000,
                    status=TaskStatus.PLANNED,
                ),
            ],
            total_makespan=10.0,
            on_time_delivery_rate=1.0,
            machine_utilization={"M001": 0.85},
            total_changeover_time=0.5,
        )
        score = validator._calculate_quality_score(result)
        assert 0.0 <= score <= 1.0


class TestGenerateRecommendations:
    def test_good_recommendation(self, validator, good_result):
        recs = validator._generate_recommendations(good_result, quality_score=0.9)
        assert any("良好" in r for r in recs)

    def test_delayed_recommendation(self, validator, delayed_result):
        recs = validator._generate_recommendations(delayed_result, quality_score=0.5)
        assert len(recs) > 0

    def test_default_recommendation(self, validator, good_result):
        recs = validator._generate_recommendations(good_result, quality_score=0.85)
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_high_load_recommendation(self, validator, high_util_result):
        recs = validator._generate_recommendations(high_util_result, quality_score=0.6)
        assert any("负载" in r for r in recs)


class TestConstraintViolation:
    def test_creation(self):
        v = ConstraintViolation(
            type="due_date",
            order_id="O001",
            machine_id="M001",
            description="订单延期 5.0小时",
            severity="warning",
            impact=0.5,
        )
        assert v.type == "due_date"
        assert v.order_id == "O001"
        assert v.severity == "warning"

    def test_defaults(self):
        v = ConstraintViolation(
            type="capacity",
            order_id=None,
            machine_id=None,
            description="利用率过高",
            severity="warning",
            impact=0.0,
        )
        assert v.order_id is None
        assert v.machine_id is None
        assert v.severity == "warning"
        assert v.impact == 0.0


class TestValidationResult:
    def test_defaults(self):
        r = ValidationResult(is_valid=True)
        assert r.constraint_violations == []
        assert r.warnings == []
        assert r.recommendations == []
        assert r.quality_score == 0.0
        assert r.overall_status == "normal"
        assert r.confidence_score == 0.8
