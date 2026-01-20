from .analyzer import analyze_html, suggest_fixes_with_ai, summarize_issues
from .auto_scanner import scan_site
from .cli import main
from .fixes import apply_fixes

__all__ = [
    "analyze_html",
    "summarize_issues",
    "suggest_fixes_with_ai",
    "apply_fixes",
    "scan_site",
    "main",
]

