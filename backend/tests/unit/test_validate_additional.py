"""API-aligned smoke tests for validate.py specialized validators."""

from planproof.rules.catalog import EvidenceExpectation, Rule


def _make_rule(rule_id: str, category: str = "FIELD_REQUIRED") -> Rule:
    return Rule(
        rule_id=rule_id,
        title="",
        description="",
        required_fields=[],
        evidence=EvidenceExpectation(source_types=[], keywords=[]),
        severity="error",
        applies_to=[],
        tags=[],
        required_fields_any=False,
        rule_category=category,
    )


class TestValidateFee:
    def test_validate_fee_amount_pass(self):
        from planproof.pipeline.validate import _validate_fee

        rule = _make_rule("FEE-02")
        context = {"fields": {"fee_amount": 200, "application_type": "householder"}}

        result = _validate_fee(rule, context)
        assert result and result["status"] == "pass"

    def test_validate_fee_missing(self):
        from planproof.pipeline.validate import _validate_fee

        rule = _make_rule("FEE-02")
        context = {"fields": {"application_type": "full"}}

        result = _validate_fee(rule, context)
        assert result and result["status"] == "needs_review"


class TestValidateOwnership:
    def test_validate_ownership_valid(self):
        from planproof.pipeline.validate import _validate_ownership

        rule = _make_rule("OWN-01")
        context = {"fields": {"certificate_type": "Certificate A"}}

        result = _validate_ownership(rule, context)
        assert result and result["status"] == "pass"

    def test_validate_ownership_missing(self):
        from planproof.pipeline.validate import _validate_ownership

        rule = _make_rule("OWN-01")
        context = {"fields": {}}

        result = _validate_ownership(rule, context)
        assert result and result["status"] == "fail"


class TestValidatePriorApproval:
    def test_prior_approval_not_applicable(self):
        from planproof.pipeline.validate import _validate_prior_approval

        rule = _make_rule("PA-01")
        context = {"fields": {"application_type": "full planning"}}

        result = _validate_prior_approval(rule, context)
        assert result and result["status"] == "pass"


class TestValidateConstraint:
    def test_constraint_none_declared(self):
        from planproof.pipeline.validate import _validate_constraint

        rule = _make_rule("CON-01")
        context = {"fields": {}}

        result = _validate_constraint(rule, context)
        assert result and result["status"] == "pass"


class TestHelpers:
    def test_build_text_index_with_tables(self):
        from planproof.pipeline.validate import _build_text_index

        extraction_result = {
            "text_blocks": [{"content": "Header text"}],
            "tables": [{"cells": [{"content": "Cell 1"}, {"content": "Cell 2"}]}],
        }

        index = _build_text_index(extraction_result)
        assert "header text" in index["full_text"].lower()
        assert "cell 1" in index["full_text"].lower()
        assert "cell 2" in index["full_text"].lower()

    def test_extract_field_value_simple(self):
        from planproof.pipeline.validate import _build_text_index, _extract_field_value

        extraction_result = {
            "text_blocks": [
                {"content": "Applicant Name: Jane Doe"},
            ]
        }
        index = _build_text_index(extraction_result)
        value = _extract_field_value("applicant_name", index, extraction_result)
        assert value == "Jane Doe"

    def test_find_evidence_location(self):
        from planproof.pipeline.validate import _find_evidence_location

        extraction_result = {
            "text_blocks": [
                {"content": "Site Address: 1 High St", "page_number": 2, "bounding_box": {}},
            ]
        }
        page, location = _find_evidence_location("site_address", "Site Address: 1 High St", extraction_result)
        assert page == 2
        assert location is not None
