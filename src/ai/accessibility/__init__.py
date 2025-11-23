from .analyzer import analyze_html, summarize_issues, suggest_fixes_with_ai
from .cli import main
from .fixes import apply_fixes
from .auto_scanner import scan_site

__all__ = [
	"analyze_html",
	"summarize_issues",
	"suggest_fixes_with_ai",
	"apply_fixes",
	"scan_site",
	"main",
]
