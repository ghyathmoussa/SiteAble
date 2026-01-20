"""Test HTML report generation."""

import json
import os
import tempfile

import pytest

from core.severity import CRITICAL, MAJOR, MINOR


def test_generate_single_page_report():
    """Test generating a single page report."""
    from reporting.html_report import generate_html_report

    report = {
        "issues": [
            {"code": "IMG_MISSING_ALT", "message": "Missing alt", "severity": CRITICAL, "wcag": "1.1.1"},
            {"code": "LOW_CONTRAST", "message": "Low contrast", "severity": MAJOR, "wcag": "1.4.3"},
        ],
        "severity_summary": {CRITICAL: 1, MAJOR: 1, MINOR: 0},
        "version": "1.0.0",
    }

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = f.name

    try:
        result = generate_html_report(report, output_path)

        assert os.path.exists(result)
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Check essential content
        assert "SiteAble" in content
        assert "IMG_MISSING_ALT" in content
        assert "LOW_CONTRAST" in content
        assert "1.1.1" in content
        assert "critical" in content.lower()
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_generate_site_report():
    """Test generating a site-wide report."""
    from reporting.html_report import generate_html_report

    report = {
        "pages": {
            "https://example.com/": {
                "issues": [
                    {"code": "IMG_MISSING_ALT", "message": "Missing alt", "severity": CRITICAL},
                ],
            },
            "https://example.com/about": {
                "issues": [
                    {"code": "HEADING_ORDER", "message": "Bad heading", "severity": MINOR},
                ],
            },
        },
        "severity_summary": {CRITICAL: 1, MAJOR: 0, MINOR: 1},
        "version": "1.0.0",
    }

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = f.name

    try:
        result = generate_html_report(report, output_path)

        assert os.path.exists(result)
        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        # Check essential content
        assert "example.com" in content
        assert "2" in content  # 2 pages
        assert "Pages Scanned" in content
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)


def test_report_with_custom_title():
    """Test report with custom title."""
    from reporting.html_report import generate_html_report

    report = {
        "issues": [],
        "severity_summary": {CRITICAL: 0, MAJOR: 0, MINOR: 0},
    }

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
        output_path = f.name

    try:
        result = generate_html_report(
            report,
            output_path,
            title="My Custom Report",
        )

        with open(result, "r", encoding="utf-8") as f:
            content = f.read()

        assert "My Custom Report" in content
    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)
