from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Analyzer(ABC):
    """Base class for accessibility analyzers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this analyzer."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass

    @abstractmethod
    def analyze(self, html: str) -> List[Dict[str, Any]]:
        """Analyze HTML and return list of issues with keys: code, message, context."""
        pass


class AnalyzerRegistry:
    """Registry to manage available analyzers."""

    def __init__(self):
        self._analyzers: Dict[str, Analyzer] = {}

    def register(self, analyzer: Analyzer) -> None:
        """Register an analyzer instance."""
        self._analyzers[analyzer.name] = analyzer

    def unregister(self, name: str) -> None:
        """Unregister an analyzer by name."""
        if name in self._analyzers:
            del self._analyzers[name]

    def get(self, name: str) -> Analyzer:
        """Get analyzer by name."""
        return self._analyzers.get(name)

    def list(self) -> Dict[str, Analyzer]:
        """List all registered analyzers."""
        return dict(self._analyzers)

    def analyze_all(self, html: str, exclude: List[str] = None) -> List[Dict[str, Any]]:
        """Run all analyzers (except excluded) and return combined issues."""
        exclude = exclude or []
        issues = []
        for name, analyzer in self._analyzers.items():
            if name not in exclude:
                try:
                    analyzer_issues = analyzer.analyze(html)
                    issues.extend(analyzer_issues)
                except Exception:
                    pass
        return issues


# Global registry instance
_registry = AnalyzerRegistry()


def get_registry() -> AnalyzerRegistry:
    """Get the global analyzer registry."""
    return _registry
