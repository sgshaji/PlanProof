"""Focused catalog and resolution tests aligned to current APIs."""

from pathlib import Path
from types import SimpleNamespace


def test_parse_validation_requirements(tmp_path):
    """Parse a minimal markdown rules file and ensure a Rule is produced."""
    md_path = tmp_path / "rules.md"
    md_path.write_text(
        """1: Test Rule
Required fields: site_address, applicant_name
Evidence: application_form
Severity: error
""",
        encoding="utf-8",
    )

    from planproof.rules.catalog import parse_validation_requirements

    rules = parse_validation_requirements(md_path)
    assert rules
    assert rules[0].rule_id == "R1"
    assert "site_address" in rules[0].required_fields


def test_write_rule_catalog_json(tmp_path):
    """Write catalog JSON from markdown and verify payload."""
    md_path = tmp_path / "rules.md"
    md_path.write_text(
        """2: Another Rule
Required fields: site_address
Evidence: application_form
""",
        encoding="utf-8",
    )
    out_path = tmp_path / "catalog.json"

    from planproof.rules.catalog import write_rule_catalog_json

    payload = write_rule_catalog_json(md_path, out_path)
    assert out_path.exists()
    assert payload["rule_count"] == 1
    assert payload["rules"][0]["rule_id"] == "R2"


def test_dependency_resolver_basic():
    """Ensure dependency resolver maps dependencies correctly."""
    from planproof.services.resolution_service import DependencyResolver

    issues = [
        SimpleNamespace(issue_id="a", resolution=SimpleNamespace(depends_on_issues=["b"])),
        SimpleNamespace(issue_id="b", resolution=SimpleNamespace(depends_on_issues=[])),
    ]

    resolver = DependencyResolver(issues)
    assert resolver.get_dependent_issues("b") == ["a"]
    assert resolver.get_blocking_issues("a") == ["b"]
