"""Initialize and register built-in analyzers."""
from core.analyzer import get_registry
from analyzers.plugins import (
    AltTextAnalyzer,
    FormLabelAnalyzer,
    HeadingOrderAnalyzer,
    ContrastAnalyzer,
    LinkTextAnalyzer,
)


def init_default_analyzers():
    """Register built-in analyzers."""
    registry = get_registry()
    registry.register(AltTextAnalyzer())
    registry.register(FormLabelAnalyzer())
    registry.register(HeadingOrderAnalyzer())
    registry.register(ContrastAnalyzer())
    registry.register(LinkTextAnalyzer())
