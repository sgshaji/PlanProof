"""Coverage-focused tests for core helpers."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from planproof import config
from planproof.enhanced_issues import DocumentCandidate, IssueSeverity, create_missing_document_issue
from planproof.issue_factory import (
    create_bng_applicability_issue,
    create_bng_exemption_reason_issue,
    create_data_conflict_issue,
    create_m3_registration_issue,
    create_pa_required_docs_issue,
)
from planproof.ui.components import (
    bulk_operations,
    dashboard,
    error_display,
    export as export_component,
    filters,
    issue_display,
    messages,
    navigation,
    resolution,
    search,
)


def test_settings_validation_rejects_invalid_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "invalid")
    with pytest.raises(ValueError):
        config.reload_settings()


def test_get_settings_caches_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    config._settings = None
    first = config.get_settings()
    second = config.get_settings()
    assert first is second


def test_create_missing_document_issue_optional_and_candidates() -> None:
    candidates = [
        DocumentCandidate(document_id=1, filename="site_plan.pdf", confidence=0.8, reason="match")
    ]
    issue = create_missing_document_issue(
        document_type="site_plan",
        rule_id="DOC-001",
        candidates=candidates,
        optional=True,
        severity=IssueSeverity.WARNING,
    )
    assert issue.user_message.subtitle == "Optional but recommended"
    assert issue.actions.secondary[-1].type.value == "mark_not_required"
    assert "issue_id" in issue.to_dict()


def test_create_missing_document_issue_unknown_type() -> None:
    issue = create_missing_document_issue(document_type="custom_doc", rule_id="DOC-999")
    assert "custom doc" in issue.user_message.title.lower()


def test_issue_factory_variants_cover_paths() -> None:
    conflict_issue = create_data_conflict_issue(
        field_name="site_address",
        conflicting_values=[
            {"field_value": "A", "document_id": 1, "snippet": "A"},
            {"field_value": "B", "document_id": 2, "snippet": "B"},
        ],
        rule_id="VAL-001",
    )
    assert conflict_issue.issue_id.startswith("CONFLICT-")

    bng_issue = create_bng_applicability_issue(rule_id="BNG-001")
    assert bng_issue.rule_id == "BNG-001"

    exemption_issue = create_bng_exemption_reason_issue(rule_id="BNG-002", found_snippet="exempt")
    assert exemption_issue.evidence is not None

    m3_issue = create_m3_registration_issue(rule_id="M3-001")
    assert m3_issue.rule_id == "M3-001"

    pa_issue = create_pa_required_docs_issue(
        rule_id="PA-001",
        pa_type="Part 1",
        missing_docs=["doc_a"],
        linked_issues={"doc_a": "DOC-001"},
    )
    assert pa_issue.rule_id == "PA-001"


@patch("streamlit.error")
@patch("streamlit.warning")
@patch("streamlit.info")
def test_issue_display_variants(mock_info, mock_warning, mock_error) -> None:
    issue_display.display_issue({"severity": "error", "message": "error"})
    issue_display.display_issue({"severity": "warning", "message": "warning"})
    issue_display.display_issue({"severity": "info", "message": "info"})
    assert mock_error.called
    assert mock_warning.called
    assert mock_info.called


@patch("streamlit.expander")
def test_issue_display_evidence(mock_expander) -> None:
    issue_display.display_evidence(
        {"evidence_page": 2, "evidence_text": "text", "bounding_box": [1, 2, 3, 4]}
    )
    assert mock_expander.called


def test_issue_card_formatting() -> None:
    html = issue_display.format_issue_card(
        {"issue_id": "DOC-1", "severity": "error", "message": "oops", "rule_category": "Docs"}
    )
    assert "DOC-1" in html


@patch("streamlit.metric")
def test_dashboard_metrics(mock_metric) -> None:
    dashboard.display_completion_metric({"total_issues": 4, "resolved_issues": 2})
    assert mock_metric.called


@patch("streamlit.progress")
def test_dashboard_progress(mock_progress) -> None:
    dashboard.display_progress_bar(1, 2)
    assert mock_progress.called


@patch("streamlit.columns")
def test_dashboard_row(mock_columns) -> None:
    mock_columns.return_value = [Mock(), Mock(), Mock()]
    dashboard.display_metrics_row({"total_documents": 1, "total_issues": 2, "blockers": 0})
    assert mock_columns.called


def test_dashboard_grouping_helpers() -> None:
    issues = [
        {"severity": "error", "status": "open", "rule_category": "Docs"},
        {"severity": "warning", "status": "resolved", "rule_category": "Docs"},
    ]
    assert dashboard.calculate_severity_counts(issues)["error"] == 1
    assert dashboard.calculate_status_distribution(issues)["resolved"] == 1
    assert len(dashboard.group_by_category(issues)["Docs"]) == 2


@patch("streamlit.file_uploader")
def test_resolution_document_upload(mock_uploader) -> None:
    resolution.render_document_upload({"issue_id": "DOC-1"})
    assert mock_uploader.called


@patch("streamlit.text_area")
@patch("streamlit.button")
def test_resolution_explanation(mock_button, mock_text_area) -> None:
    resolution.render_explanation_form({"issue_id": "DOC-1"})
    assert mock_text_area.called
    assert mock_button.called


@patch("streamlit.radio")
def test_resolution_option_selection(mock_radio) -> None:
    resolution.render_option_selection({"resolution_options": ["opt1"]})
    assert mock_radio.called


@patch("streamlit.warning")
@patch("streamlit.button")
def test_resolution_dismiss(mock_button, mock_warning) -> None:
    resolution.render_dismiss_option({"issue_id": "DOC-1"})
    assert mock_warning.called
    assert mock_button.called


@patch("streamlit.text_input")
@patch("planproof.services.search_service.SearchService")
def test_search_interface_handles_list_results(mock_search_service, mock_text_input) -> None:
    mock_text_input.return_value = "APP-001"
    mock_service = Mock()
    mock_service.search_applications.return_value = []
    mock_search_service.return_value = mock_service
    search.render_search_interface()


@patch("streamlit.text_input")
@patch("planproof.services.search_service.SearchService")
def test_search_interface_handles_dict_results(mock_search_service, mock_text_input) -> None:
    mock_text_input.return_value = "APP-002"
    mock_service = Mock()
    mock_service.search_applications.return_value = {"results": []}
    mock_search_service.return_value = mock_service
    search.render_search_interface()


@patch("streamlit.selectbox")
def test_filters_severity(mock_selectbox) -> None:
    mock_selectbox.return_value = "error"
    assert filters.render_severity_filter() == "error"


@patch("streamlit.multiselect")
def test_filters_category(mock_multiselect) -> None:
    mock_multiselect.return_value = ["Docs"]
    assert filters.render_category_filter(["Docs"]) == ["Docs"]


@patch("streamlit.sidebar")
def test_navigation_sidebar_callable(mock_sidebar) -> None:
    mock_sidebar.return_value.radio.return_value = "Dashboard"
    assert navigation.render_sidebar() == "Dashboard"


@patch("streamlit.tabs")
def test_navigation_tabs(mock_tabs) -> None:
    mock_tabs.return_value = [Mock()]
    tabs = navigation.render_tabs(["Tab"])
    assert tabs == mock_tabs.return_value


@patch("streamlit.checkbox")
@patch("streamlit.button")
def test_bulk_operations_selection(mock_button, mock_checkbox) -> None:
    mock_checkbox.return_value = True
    selected = bulk_operations.render_bulk_selector([{"issue_id": "DOC-1"}])
    assert selected == ["DOC-1"]
    assert mock_button.called


@patch("streamlit.file_uploader")
@patch("streamlit.button")
def test_bulk_operations_upload(mock_button, mock_uploader) -> None:
    bulk_operations.render_bulk_upload()
    assert mock_uploader.called
    assert mock_button.called


@patch("streamlit.error")
@patch("streamlit.warning")
def test_error_display_helpers(mock_warning, mock_error) -> None:
    error_display.show_database_error("oops")
    error_display.show_validation_warning("warn")
    assert mock_error.called
    assert mock_warning.called


@patch("streamlit.info")
def test_message_info(mock_info) -> None:
    messages.show_info("hi")
    assert mock_info.called


@patch("streamlit.download_button")
def test_export_helpers(mock_download) -> None:
    csv_data = export_component._issues_to_csv([{"a": 1}])
    assert "a" in csv_data
    assert export_component._issues_to_csv([]) == ""
    export_component.render_csv_download([{"a": 1}])
    export_component.render_decision_package_download(1)
    assert mock_download.called


@patch("streamlit.text_input")
def test_search_interface_empty_query(mock_text_input) -> None:
    mock_text_input.return_value = ""
    search.render_search_interface()
