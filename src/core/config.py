"""Configuration management for SiteAble.

Supports loading configuration from YAML files, environment variables,
and command-line arguments with proper precedence.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# Try to import yaml, fall back gracefully
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False


@dataclass
class ScanConfig:
    """Configuration for scanning behavior."""

    concurrency: int = 10
    max_pages: int = 200
    delay: float = 0.0
    rate_limit: float = 0.0
    timeout: float = 10.0
    respect_robots: bool = True


@dataclass
class AnalyzerConfig:
    """Configuration for analyzers."""

    exclude: List[str] = field(default_factory=list)
    wcag_level: str = "AA"  # AA or AAA


@dataclass
class OutputConfig:
    """Configuration for output."""

    format: str = "pretty"  # pretty, json, html
    path: Optional[str] = None
    html_path: Optional[str] = None


@dataclass
class AIConfig:
    """Configuration for AI features."""

    enabled: bool = False
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None


@dataclass
class DatabaseConfig:
    """Configuration for database."""

    path: Optional[str] = None
    auto_save: bool = False


@dataclass
class Config:
    """Main configuration container."""

    scan: ScanConfig = field(default_factory=ScanConfig)
    analyzers: AnalyzerConfig = field(default_factory=AnalyzerConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        config = cls()

        if "scan" in data:
            scan = data["scan"]
            config.scan = ScanConfig(
                concurrency=scan.get("concurrency", 10),
                max_pages=scan.get("max_pages", 200),
                delay=scan.get("delay", 0.0),
                rate_limit=scan.get("rate_limit", 0.0),
                timeout=scan.get("timeout", 10.0),
                respect_robots=scan.get("respect_robots", True),
            )

        if "analyzers" in data:
            analyzers = data["analyzers"]
            config.analyzers = AnalyzerConfig(
                exclude=analyzers.get("exclude", []),
                wcag_level=analyzers.get("wcag_level", "AA"),
            )

        if "output" in data:
            output = data["output"]
            config.output = OutputConfig(
                format=output.get("format", "pretty"),
                path=output.get("path"),
                html_path=output.get("html_path"),
            )

        if "ai" in data:
            ai = data["ai"]
            config.ai = AIConfig(
                enabled=ai.get("enabled", False),
                model=ai.get("model", "gpt-3.5-turbo"),
                api_key=ai.get("api_key"),
            )

        if "database" in data:
            db = data["database"]
            config.database = DatabaseConfig(
                path=db.get("path"),
                auto_save=db.get("auto_save", False),
            )

        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert Config to dictionary."""
        return {
            "scan": {
                "concurrency": self.scan.concurrency,
                "max_pages": self.scan.max_pages,
                "delay": self.scan.delay,
                "rate_limit": self.scan.rate_limit,
                "timeout": self.scan.timeout,
                "respect_robots": self.scan.respect_robots,
            },
            "analyzers": {
                "exclude": self.analyzers.exclude,
                "wcag_level": self.analyzers.wcag_level,
            },
            "output": {
                "format": self.output.format,
                "path": self.output.path,
                "html_path": self.output.html_path,
            },
            "ai": {
                "enabled": self.ai.enabled,
                "model": self.ai.model,
            },
            "database": {
                "path": self.database.path,
                "auto_save": self.database.auto_save,
            },
        }


def load_config(config_path: Optional[str] = None) -> Config:
    """Load configuration from file.

    Searches for configuration in the following order:
    1. Specified config_path
    2. ./siteable.yaml or ./siteable.yml
    3. ~/.siteable/config.yaml

    Args:
        config_path: Optional path to configuration file

    Returns:
        Config object with loaded settings
    """
    paths_to_try = []

    if config_path:
        paths_to_try.append(Path(config_path))
    else:
        # Current directory
        paths_to_try.append(Path("siteable.yaml"))
        paths_to_try.append(Path("siteable.yml"))
        paths_to_try.append(Path(".siteable.yaml"))
        paths_to_try.append(Path(".siteable.yml"))

        # Home directory
        home = Path.home()
        paths_to_try.append(home / ".siteable" / "config.yaml")
        paths_to_try.append(home / ".siteable" / "config.yml")

    for path in paths_to_try:
        if path.exists():
            return load_config_from_file(path)

    # Return default config if no file found
    return Config()


def load_config_from_file(path: Path) -> Config:
    """Load configuration from a specific file.

    Args:
        path: Path to configuration file

    Returns:
        Config object

    Raises:
        ImportError: If YAML support is needed but not available
        ValueError: If file format is not supported
    """
    suffix = path.suffix.lower()

    if suffix in (".yaml", ".yml"):
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required to load YAML configuration files. "
                "Install with: pip install pyyaml"
            )
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    elif suffix == ".json":
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise ValueError(f"Unsupported configuration file format: {suffix}")

    return Config.from_dict(data)


def merge_env_config(config: Config) -> Config:
    """Merge environment variables into configuration.

    Environment variables take precedence over file configuration.

    Args:
        config: Existing configuration

    Returns:
        Updated configuration
    """
    # Scan settings
    if os.environ.get("SITEABLE_CONCURRENCY"):
        config.scan.concurrency = int(os.environ["SITEABLE_CONCURRENCY"])
    if os.environ.get("SITEABLE_MAX_PAGES"):
        config.scan.max_pages = int(os.environ["SITEABLE_MAX_PAGES"])
    if os.environ.get("SITEABLE_DELAY"):
        config.scan.delay = float(os.environ["SITEABLE_DELAY"])
    if os.environ.get("SITEABLE_RATE_LIMIT"):
        config.scan.rate_limit = float(os.environ["SITEABLE_RATE_LIMIT"])

    # AI settings
    if os.environ.get("OPENAI_API_KEY"):
        config.ai.api_key = os.environ["OPENAI_API_KEY"]
    if os.environ.get("AI_MODEL"):
        config.ai.model = os.environ["AI_MODEL"]

    # Database
    if os.environ.get("SITEABLE_DB_PATH"):
        config.database.path = os.environ["SITEABLE_DB_PATH"]

    return config
