"""
Unit tests for the SDO (Semantic Development Object) module.
Tests state transitions, confidence calculation, and data integrity.
"""
import pytest
import time
from sdo import SDO, SDOStatus, Contract, GenerationStep, Candidate


class TestSDOInitialization:
    """Test SDO creation and defaults."""

    def test_default_status_is_draft(self):
        sdo = SDO(id="test-1", raw_intent="Create a login form", language="python")
        assert sdo.status == SDOStatus.DRAFT

    def test_default_confidence_is_zero(self):
        sdo = SDO(id="test-2", raw_intent="intent", language="python")
        assert sdo.confidence == 0.0

    def test_empty_history_on_creation(self):
        sdo = SDO(id="test-3", raw_intent="intent", language="go")
        assert sdo.history == []
        assert sdo.candidates == []
        assert sdo.contracts == []

    def test_timestamps_are_set(self):
        before = time.time()
        sdo = SDO(id="test-4", raw_intent="intent", language="rust")
        after = time.time()
        assert before <= sdo.created_at <= after
        assert before <= sdo.updated_at <= after


class TestSDOStatusTransitions:
    """Test status update logic."""

    def test_update_status_changes_status(self):
        sdo = SDO(id="test-5", raw_intent="intent", language="python")
        sdo.update_status(SDOStatus.PARSING)
        assert sdo.status == SDOStatus.PARSING

    def test_update_status_updates_timestamp(self):
        sdo = SDO(id="test-6", raw_intent="intent", language="python")
        original_time = sdo.updated_at
        time.sleep(0.01)
        sdo.update_status(SDOStatus.GENERATING)
        assert sdo.updated_at > original_time

    def test_full_lifecycle(self):
        sdo = SDO(id="test-7", raw_intent="intent", language="python")
        for status in [SDOStatus.PARSING, SDOStatus.PLANNING, SDOStatus.GENERATING,
                       SDOStatus.VERIFYING, SDOStatus.VERIFIED]:
            sdo.update_status(status)
        assert sdo.status == SDOStatus.VERIFIED


class TestSDOConfidenceCalculation:
    """Test the weighted confidence calculation."""

    def test_empty_history_gives_zero(self):
        sdo = SDO(id="test-8", raw_intent="intent", language="python")
        assert sdo.calculate_confidence() == 0.0

    def test_single_parse_step(self):
        sdo = SDO(id="test-9", raw_intent="intent", language="python")
        sdo.add_step("parse", {"parsed": True}, confidence=0.9, model="gpt-4")
        # weight for parse = 0.2, score = 0.9 * 0.2 = 0.18, total_weight = 0.2
        # confidence = 0.18 / 0.2 = 0.9
        assert abs(sdo.calculate_confidence() - 0.9) < 0.01

    def test_mixed_steps_weighted(self):
        sdo = SDO(id="test-10", raw_intent="intent", language="python")
        sdo.add_step("parse", {"parsed": True}, confidence=0.9, model="gpt-4")
        sdo.add_step("code", {"code": "print(1)"}, confidence=0.8, model="gpt-4")
        # parse: 0.9 * 0.2 = 0.18, code: 0.8 * 0.3 = 0.24
        # total = 0.42 / 0.5 = 0.84
        assert abs(sdo.calculate_confidence() - 0.84) < 0.01

    def test_confidence_capped_at_one(self):
        sdo = SDO(id="test-11", raw_intent="intent", language="python")
        sdo.add_step("parse", {}, confidence=1.5, model="gpt-4")  # Artificially high
        assert sdo.calculate_confidence() <= 1.0

    def test_unknown_step_type_uses_default_weight(self):
        sdo = SDO(id="test-12", raw_intent="intent", language="python")
        sdo.add_step("custom_step", {}, confidence=0.7, model="gpt-4")
        # weight default = 0.1, score = 0.07 / 0.1 = 0.7
        assert abs(sdo.calculate_confidence() - 0.7) < 0.01


class TestSDOHistory:
    """Test history tracking."""

    def test_add_step_appends_to_history(self):
        sdo = SDO(id="test-13", raw_intent="intent", language="python")
        sdo.add_step("parse", {"key": "value"}, confidence=0.5, model="gpt-4")
        assert len(sdo.history) == 1
        assert sdo.history[0].step_type == "parse"
        assert sdo.history[0].model_id == "gpt-4"

    def test_add_step_updates_timestamp(self):
        sdo = SDO(id="test-14", raw_intent="intent", language="python")
        original = sdo.updated_at
        time.sleep(0.01)
        sdo.add_step("code", {}, confidence=0.8, model="gpt-4")
        assert sdo.updated_at > original


class TestCandidate:
    """Test the Candidate model."""

    def test_candidate_defaults(self):
        c = Candidate(id="c-1", code="print('hello')")
        assert c.confidence == 0.0
        assert c.verification_passed is False
        assert c.pruned is False

    def test_candidate_with_verification(self):
        c = Candidate(
            id="c-2",
            code="def add(a, b): return a + b",
            confidence=0.95,
            model_id="gpt-4",
            verification_score=0.92,
            verification_passed=True,
        )
        assert c.verification_passed is True
        assert c.verification_score == 0.92


class TestContract:
    """Test the Contract model."""

    def test_contract_creation(self):
        c = Contract(type="precondition", description="x > 0", expression="x > 0")
        assert c.type == "precondition"

    def test_contract_without_expression(self):
        c = Contract(type="invariant", description="list length < 100")
        assert c.expression is None
