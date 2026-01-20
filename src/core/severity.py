"""Severity scoring system for accessibility issues.

Maps issue codes to severity levels and WCAG criteria for better prioritization.
"""

from typing import Any, Dict, List, Optional

# Severity levels
CRITICAL = "critical"  # Blocks access for users with disabilities
MAJOR = "major"  # Significant barrier to accessibility
MINOR = "minor"  # Usability issue, but workarounds exist


# Mapping of issue codes to severity and WCAG criteria
SEVERITY_MAP: Dict[str, Dict[str, str]] = {
    # Critical - Completely blocks access
    "IMG_MISSING_ALT": {
        "level": CRITICAL,
        "wcag": "1.1.1",
        "wcag_name": "Non-text Content",
        "impact": "Screen reader users cannot understand image content",
    },
    "LINK_IMG_MISSING_ALT": {
        "level": CRITICAL,
        "wcag": "1.1.1",
        "wcag_name": "Non-text Content",
        "impact": "Screen reader users cannot understand link purpose",
    },
    "FORM_CONTROL_NO_LABEL": {
        "level": CRITICAL,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "Screen reader users cannot identify form fields",
    },
    "LINK_NO_TEXT": {
        "level": CRITICAL,
        "wcag": "2.4.4",
        "wcag_name": "Link Purpose (In Context)",
        "impact": "Screen reader users cannot understand link destination",
    },
    "BUTTON_NO_TEXT": {
        "level": CRITICAL,
        "wcag": "4.1.2",
        "wcag_name": "Name, Role, Value",
        "impact": "Screen reader users cannot understand button purpose",
    },
    "MISSING_LANG": {
        "level": CRITICAL,
        "wcag": "3.1.1",
        "wcag_name": "Language of Page",
        "impact": "Screen readers may mispronounce content",
    },
    "TABLE_NO_HEADERS": {
        "level": CRITICAL,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "Screen reader users cannot understand table structure",
    },
    "ARIA_HIDDEN_FOCUSABLE": {
        "level": CRITICAL,
        "wcag": "4.1.2",
        "wcag_name": "Name, Role, Value",
        "impact": "Keyboard users can focus invisible elements",
    },
    # Major - Significant barriers
    "LOW_CONTRAST": {
        "level": MAJOR,
        "wcag": "1.4.3",
        "wcag_name": "Contrast (Minimum)",
        "impact": "Users with low vision may not be able to read text",
    },
    "VIDEO_NO_CAPTIONS": {
        "level": MAJOR,
        "wcag": "1.2.2",
        "wcag_name": "Captions (Prerecorded)",
        "impact": "Deaf users cannot access video audio content",
    },
    "AUDIO_NO_TRANSCRIPT": {
        "level": MAJOR,
        "wcag": "1.2.1",
        "wcag_name": "Audio-only and Video-only",
        "impact": "Deaf users cannot access audio content",
    },
    "INVALID_ARIA_ROLE": {
        "level": MAJOR,
        "wcag": "4.1.2",
        "wcag_name": "Name, Role, Value",
        "impact": "Assistive technology may not interpret element correctly",
    },
    "MISSING_MAIN": {
        "level": MAJOR,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "Screen reader users cannot easily navigate to main content",
    },
    "AUTOPLAY_NO_CONTROLS": {
        "level": MAJOR,
        "wcag": "1.4.2",
        "wcag_name": "Audio Control",
        "impact": "Users cannot stop unwanted audio",
    },
    # Minor - Usability issues
    "HEADING_ORDER": {
        "level": MINOR,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "May confuse screen reader users navigating by headings",
    },
    "INVALID_LANG": {
        "level": MINOR,
        "wcag": "3.1.1",
        "wcag_name": "Language of Page",
        "impact": "Screen readers may not properly switch language",
    },
    "NO_SKIP_LINK": {
        "level": MINOR,
        "wcag": "2.4.1",
        "wcag_name": "Bypass Blocks",
        "impact": "Keyboard users must tab through all navigation",
    },
    "BROKEN_SKIP_LINK": {
        "level": MINOR,
        "wcag": "2.4.1",
        "wcag_name": "Bypass Blocks",
        "impact": "Skip link does not work as expected",
    },
    "MULTIPLE_H1": {
        "level": MINOR,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "May confuse screen reader users about page structure",
    },
    "TABLE_NO_CAPTION": {
        "level": MINOR,
        "wcag": "1.3.1",
        "wcag_name": "Info and Relationships",
        "impact": "Screen reader users may not understand table purpose",
    },
    "MISSING_TITLE": {
        "level": MINOR,
        "wcag": "2.4.2",
        "wcag_name": "Page Titled",
        "impact": "Users may not identify page purpose in tabs/bookmarks",
    },
}

# Priority order for sorting
SEVERITY_ORDER = {CRITICAL: 0, MAJOR: 1, MINOR: 2}


def get_severity(code: str) -> str:
    """Get severity level for an issue code.

    Args:
        code: Issue code (e.g., 'IMG_MISSING_ALT')

    Returns:
        Severity level ('critical', 'major', or 'minor')
    """
    if code in SEVERITY_MAP:
        return SEVERITY_MAP[code]["level"]
    return MINOR  # Default to minor for unknown codes


def get_wcag_criterion(code: str) -> Optional[str]:
    """Get WCAG criterion for an issue code.

    Args:
        code: Issue code

    Returns:
        WCAG criterion (e.g., '1.1.1') or None
    """
    if code in SEVERITY_MAP:
        return SEVERITY_MAP[code]["wcag"]
    return None


def get_wcag_name(code: str) -> Optional[str]:
    """Get WCAG criterion name for an issue code.

    Args:
        code: Issue code

    Returns:
        WCAG criterion name (e.g., 'Non-text Content') or None
    """
    if code in SEVERITY_MAP:
        return SEVERITY_MAP[code].get("wcag_name")
    return None


def get_impact(code: str) -> Optional[str]:
    """Get impact description for an issue code.

    Args:
        code: Issue code

    Returns:
        Impact description or None
    """
    if code in SEVERITY_MAP:
        return SEVERITY_MAP[code].get("impact")
    return None


def enrich_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich an issue with severity and WCAG information.

    Args:
        issue: Issue dict with at least a 'code' key

    Returns:
        Enriched issue dict with severity, wcag, wcag_name, and impact
    """
    code = issue.get("code", "")
    enriched = issue.copy()

    enriched["severity"] = get_severity(code)
    enriched["wcag"] = get_wcag_criterion(code)
    enriched["wcag_name"] = get_wcag_name(code)
    enriched["impact"] = get_impact(code)

    return enriched


def enrich_issues(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich a list of issues with severity information.

    Args:
        issues: List of issue dicts

    Returns:
        List of enriched issue dicts
    """
    return [enrich_issue(issue) for issue in issues]


def sort_by_severity(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort issues by severity (critical first, then major, then minor).

    Args:
        issues: List of issue dicts (should be enriched first)

    Returns:
        Sorted list of issues
    """
    return sorted(
        issues,
        key=lambda x: SEVERITY_ORDER.get(x.get("severity", MINOR), 2),
    )


def summarize_by_severity(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize issues by severity level.

    Args:
        issues: List of issue dicts (should be enriched first)

    Returns:
        Dict with counts per severity level
    """
    counts = {CRITICAL: 0, MAJOR: 0, MINOR: 0}
    for issue in issues:
        severity = issue.get("severity", MINOR)
        if severity in counts:
            counts[severity] += 1
        else:
            counts[MINOR] += 1
    return counts


def get_severity_color(severity: str) -> str:
    """Get color code for severity (for CLI/HTML output).

    Args:
        severity: Severity level

    Returns:
        Color name for rich/HTML
    """
    return {
        CRITICAL: "red",
        MAJOR: "yellow",
        MINOR: "blue",
    }.get(severity, "white")


def get_severity_emoji(severity: str) -> str:
    """Get emoji for severity (for CLI output).

    Args:
        severity: Severity level

    Returns:
        Emoji string
    """
    return {
        CRITICAL: "🔴",
        MAJOR: "🟡",
        MINOR: "🔵",
    }.get(severity, "⚪")
