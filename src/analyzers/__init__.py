"""Initialize and register built-in analyzers."""

from analyzers.plugins import (
    AltTextAnalyzer,
    ARIAAnalyzer,
    ButtonAnalyzer,
    ContrastAnalyzer,
    DocumentStructureAnalyzer,
    FormLabelAnalyzer,
    HeadingOrderAnalyzer,
    LanguageAnalyzer,
    LinkTextAnalyzer,
    MediaAnalyzer,
    SkipLinkAnalyzer,
    TableAnalyzer,
)
from core.analyzer import get_registry


def init_default_analyzers() -> None:
    """Register built-in analyzers.

    This function registers all the default accessibility analyzers
    with the global registry. It's called lazily when analyzers are
    first needed.
    """
    registry = get_registry()

    # Original analyzers
    registry.register(AltTextAnalyzer())
    registry.register(FormLabelAnalyzer())
    registry.register(HeadingOrderAnalyzer())
    registry.register(ContrastAnalyzer())
    registry.register(LinkTextAnalyzer())

    # New analyzers (Phase 2)
    registry.register(LanguageAnalyzer())
    registry.register(ButtonAnalyzer())
    registry.register(DocumentStructureAnalyzer())
    registry.register(TableAnalyzer())
    registry.register(ARIAAnalyzer())
    registry.register(SkipLinkAnalyzer())
    registry.register(MediaAnalyzer())


# List of all available analyzer names for reference
ANALYZER_NAMES = [
    "alt_text",
    "form_labels",
    "heading_order",
    "contrast",
    "link_text",
    "language",
    "button",
    "document_structure",
    "table",
    "aria",
    "skip_link",
    "media",
]
