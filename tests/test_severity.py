"""Test severity scoring module."""

import pytest

from core.severity import (
    CRITICAL,
    MAJOR,
    MINOR,
    enrich_issue,
    enrich_issues,
    get_impact,
    get_severity,
    get_severity_color,
    get_severity_emoji,
    get_wcag_criterion,
    get_wcag_name,
    sort_by_severity,
    summarize_by_severity,
)


def test_get_severity_known_code():
    """Test severity lookup for known codes."""
    assert get_severity("IMG_MISSING_ALT") == CRITICAL
    assert get_severity("LOW_CONTRAST") == MAJOR
    assert get_severity("HEADING_ORDER") == MINOR


def test_get_severity_unknown_code():
    """Test severity defaults to minor for unknown codes."""
    assert get_severity("UNKNOWN_CODE") == MINOR


def test_get_wcag_criterion():
    """Test WCAG criterion lookup."""
    assert get_wcag_criterion("IMG_MISSING_ALT") == "1.1.1"
    assert get_wcag_criterion("LOW_CONTRAST") == "1.4.3"
    assert get_wcag_criterion("UNKNOWN_CODE") is None


def test_get_wcag_name():
    """Test WCAG criterion name lookup."""
    assert get_wcag_name("IMG_MISSING_ALT") == "Non-text Content"
    assert get_wcag_name("LOW_CONTRAST") == "Contrast (Minimum)"


def test_get_impact():
    """Test impact description lookup."""
    impact = get_impact("IMG_MISSING_ALT")
    assert impact is not None
    assert "screen reader" in impact.lower()


def test_enrich_issue():
    """Test issue enrichment."""
    issue = {"code": "IMG_MISSING_ALT", "message": "Test"}
    enriched = enrich_issue(issue)

    assert enriched["severity"] == CRITICAL
    assert enriched["wcag"] == "1.1.1"
    assert enriched["wcag_name"] == "Non-text Content"
    assert enriched["impact"] is not None
    # Original fields preserved
    assert enriched["code"] == "IMG_MISSING_ALT"
    assert enriched["message"] == "Test"


def test_enrich_issues():
    """Test enriching multiple issues."""
    issues = [
        {"code": "IMG_MISSING_ALT"},
        {"code": "LOW_CONTRAST"},
        {"code": "HEADING_ORDER"},
    ]
    enriched = enrich_issues(issues)

    assert len(enriched) == 3
    assert enriched[0]["severity"] == CRITICAL
    assert enriched[1]["severity"] == MAJOR
    assert enriched[2]["severity"] == MINOR


def test_sort_by_severity():
    """Test sorting issues by severity."""
    issues = [
        {"code": "HEADING_ORDER", "severity": MINOR},
        {"code": "IMG_MISSING_ALT", "severity": CRITICAL},
        {"code": "LOW_CONTRAST", "severity": MAJOR},
    ]
    sorted_issues = sort_by_severity(issues)

    assert sorted_issues[0]["severity"] == CRITICAL
    assert sorted_issues[1]["severity"] == MAJOR
    assert sorted_issues[2]["severity"] == MINOR


def test_summarize_by_severity():
    """Test summarizing issues by severity."""
    issues = [
        {"severity": CRITICAL},
        {"severity": CRITICAL},
        {"severity": MAJOR},
        {"severity": MINOR},
        {"severity": MINOR},
        {"severity": MINOR},
    ]
    summary = summarize_by_severity(issues)

    assert summary[CRITICAL] == 2
    assert summary[MAJOR] == 1
    assert summary[MINOR] == 3


def test_get_severity_color():
    """Test color mapping for severities."""
    assert get_severity_color(CRITICAL) == "red"
    assert get_severity_color(MAJOR) == "yellow"
    assert get_severity_color(MINOR) == "blue"


def test_get_severity_emoji():
    """Test emoji mapping for severities."""
    assert get_severity_emoji(CRITICAL) == "🔴"
    assert get_severity_emoji(MAJOR) == "🟡"
    assert get_severity_emoji(MINOR) == "🔵"
