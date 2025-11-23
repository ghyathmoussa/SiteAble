"""Plugin-based accessibility analyzer using registered analyzers."""
from typing import List, Dict, Any

from core.analyzer import get_registry


def analyze_html(html: str, exclude_analyzers: List[str] = None) -> List[Dict[str, Any]]:
    """Analyze HTML using all registered analyzers (except excluded ones).
    
    Returns a list of issues with keys: code, message, context, analyzer.
    """
    from analyzers import init_default_analyzers
    
    # Ensure analyzers are initialized
    registry = get_registry()
    if not registry.list():
        init_default_analyzers()
    
    exclude_analyzers = exclude_analyzers or []
    issues = []
    
    for name, analyzer in registry.list().items():
        if name not in exclude_analyzers:
            try:
                analyzer_issues = analyzer.analyze(html)
                # Add analyzer name to each issue
                for issue in analyzer_issues:
                    issue['analyzer'] = name
                issues.extend(analyzer_issues)
            except Exception:
                pass
    
    return issues


def summarize_issues(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    """Summarize issues by code."""
    counts: Dict[str, int] = {}
    for it in issues:
        code = it.get("code", "UNKNOWN")
        counts[code] = counts.get(code, 0) + 1
    return counts


def list_analyzers() -> Dict[str, str]:
    """List available analyzers and their descriptions."""
    from analyzers import init_default_analyzers
    
    registry = get_registry()
    if not registry.list():
        init_default_analyzers()
    
    return {name: analyzer.description for name, analyzer in registry.list().items()}
