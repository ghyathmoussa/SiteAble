# SiteAble Architecture Guide

This document provides a detailed technical overview of the SiteAble architecture, component interactions, and design patterns.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SiteAble Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                           Entry Points                                │ │
│   │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐   │ │
│   │  │    CLI      │    │  REST API   │    │  Python Import          │   │ │
│   │  │  cli.py     │    │  api.py     │    │  from ai.accessibility  │   │ │
│   │  └──────┬──────┘    └──────┬──────┘    └────────────┬────────────┘   │ │
│   └─────────┼──────────────────┼───────────────────────┼─────────────────┘ │
│             │                  │                       │                    │
│             ▼                  ▼                       ▼                    │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                        Core Services                                  │ │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │ │
│   │  │ Analyzer Engine │  │ Crawler Engine  │  │   Fix Engine        │   │ │
│   │  │ analyzer.py     │  │ crawler_scanner │  │   fixes.py          │   │ │
│   │  └────────┬────────┘  └────────┬────────┘  └──────────┬──────────┘   │ │
│   └───────────┼────────────────────┼─────────────────────┼───────────────┘ │
│               │                    │                     │                  │
│               ▼                    │                     │                  │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                       Plugin System                                   │ │
│   │  ┌─────────────────────────────────────────────────────────────────┐ │ │
│   │  │                    Analyzer Registry                             │ │ │
│   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │ │ │
│   │  │  │ Alt Text │ │ Form    │ │ Heading  │ │ Contrast │ │ Link   │ │ │ │
│   │  │  │ Analyzer │ │ Labels  │ │  Order   │ │ Analyzer │ │  Text  │ │ │ │
│   │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │ │ │
│   │  └─────────────────────────────────────────────────────────────────┘ │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────┐ │
│   │                       Data Layer                                      │ │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │ │
│   │  │ SQLite Storage  │  │ Logging         │  │ Configuration       │   │ │
│   │  │ storage.py      │  │ logging.py      │  │ .env / config.json  │   │ │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────────┘   │ │
│   └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Entry Points

#### CLI (`src/ai/accessibility/cli.py`)

The command-line interface serves as the primary user interaction point.

**Responsibilities**:
- Parse command-line arguments
- Load and merge configuration files
- Orchestrate scanning workflow
- Format and output results

**Key Functions**:
```python
def main(argv=None):
    """Main CLI entry point."""
    # 1. Parse arguments
    # 2. Load config file (if --config)
    # 3. Setup logging
    # 4. Execute scan (single page or site)
    # 5. Apply fixes (if --apply-fixes)
    # 6. Generate AI suggestions (if --ai)
    # 7. Output results (JSON or pretty)
```

**Argument Flow**:
```
CLI Args → env vars → config.json → defaults
         (precedence order →)
```

#### REST API (`src/api/api.py`)

FastAPI-based HTTP interface for programmatic access.

**Current Endpoints**:
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Health check |
| GET | `/api/dashboard/{site}` | Get scan results for a site |

**Router Pattern**:
```python
# api.py
app.include_router(dashboard_router, prefix="/api")

# routes/dashboard.py
router = APIRouter()

@router.get("/dashboard/{site}")
def dashboard(site: str):
    rows = get_scan_results('data/siteable_scans.db', site=site)
    return {"site": site, "results": rows}
```

---

### 2. Core Services

#### Analyzer Engine (`src/ai/accessibility/analyzer.py`)

The main analysis orchestration layer.

**Design Pattern**: Facade + Strategy

```python
def analyze_html(html: str, exclude_analyzers: List[str] = None) -> List[Dict]:
    """
    1. Try plugin-based analysis (preferred)
    2. Fall back to legacy inline analysis
    """
    try:
        from .analyzer_plugin import analyze_html as plugin_analyze
        return plugin_analyze(html, exclude_analyzers=exclude_analyzers)
    except Exception:
        # Legacy fallback implementation
        ...
```

**Issue Schema**:
```python
{
    "code": "IMG_MISSING_ALT",           # Unique issue identifier
    "message": "Image missing alt...",   # Human-readable description
    "context": "<img src='...'/>",       # Relevant HTML snippet
    "analyzer": "alt_text"               # Which analyzer found it
}
```

#### Crawler Engine (`src/crawler/crawler_scanner.py`)

Async website crawler with politeness features.

**Design Pattern**: Producer-Consumer Queue

```
                    ┌─────────────┐
                    │ Start URL   │
                    └──────┬──────┘
                           ▼
          ┌────────────────────────────────┐
          │         Initialize             │
          │  - Fetch robots.txt            │
          │  - Parse disallow rules        │
          │  - Fetch sitemap.xml           │
          │  - Seed URL queue              │
          └────────────────┬───────────────┘
                           ▼
          ┌────────────────────────────────┐
          │       Async Queue              │
          │  ┌──────────────────────────┐  │
          │  │ URL1  URL2  URL3  ...    │  │
          │  └──────────────────────────┘  │
          └────────────────┬───────────────┘
                           ▼
          ┌────────────────────────────────┐
          │    Worker Pool (N workers)     │
          │  ┌────────┐ ┌────────┐        │
          │  │Worker 1│ │Worker 2│ ...    │
          │  └────────┘ └────────┘        │
          └────────────────┬───────────────┘
                           ▼
          ┌────────────────────────────────┐
          │    For each URL:               │
          │  1. Check robots.txt rules     │
          │  2. Fetch page (semaphore)     │
          │  3. Analyze HTML               │
          │  4. Persist to DB (optional)   │
          │  5. Extract links              │
          │  6. Add new URLs to queue      │
          │  7. Respect crawl-delay        │
          └────────────────────────────────┘
```

**Key Configuration**:
```python
async def scan_site_enhanced(
    start_url: str,
    max_pages: int = 200,        # Stop after N pages
    concurrency: int = 10,       # Parallel workers
    delay: float = 0.0,          # Delay between requests
    db_path: str = None,         # Persist results
    exclude_analyzers: List[str] = None
)
```

#### Fix Engine (`src/ai/accessibility/fixes.py`)

Automatic remediation for supported issues.

**Supported Fixes**:

| Issue Code | Fix Applied |
|------------|-------------|
| `IMG_MISSING_ALT` | Add `alt` attribute (from AI map or filename) |
| `LOW_CONTRAST` | Replace `color` with accessible foreground |

**Fix Pipeline**:
```python
def apply_fixes(html, issues, ai_alt_map=None) -> Tuple[str, List[Dict]]:
    """
    1. Parse HTML with BeautifulSoup
    2. For each flagged element:
       a. Determine fix type from issue code
       b. Apply DOM modification
       c. Record applied fix
    3. Return (modified_html, applied_fixes_list)
    """
```

---

### 3. Plugin System

#### Base Analyzer Interface (`src/core/analyzer.py`)

```python
from abc import ABC, abstractmethod

class Analyzer(ABC):
    """Abstract base class for accessibility analyzers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this analyzer."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
    
    @abstractmethod
    def analyze(self, html: str) -> List[Dict[str, Any]]:
        """
        Analyze HTML and return issues.
        
        Returns: List of dicts with keys: code, message, context
        """
        pass
```

#### Registry Pattern (`src/core/analyzer.py`)

```python
class AnalyzerRegistry:
    """Singleton registry for analyzer plugins."""
    
    def __init__(self):
        self._analyzers: Dict[str, Analyzer] = {}
    
    def register(self, analyzer: Analyzer) -> None:
        self._analyzers[analyzer.name] = analyzer
    
    def unregister(self, name: str) -> None:
        del self._analyzers[name]
    
    def analyze_all(self, html: str, exclude: List[str] = None) -> List[Dict]:
        """Run all registered analyzers, collect issues."""
        issues = []
        for name, analyzer in self._analyzers.items():
            if name not in (exclude or []):
                issues.extend(analyzer.analyze(html))
        return issues

# Global singleton
_registry = AnalyzerRegistry()

def get_registry() -> AnalyzerRegistry:
    return _registry
```

#### Built-in Analyzers (`src/analyzers/plugins.py`)

Each analyzer follows the same pattern:

```python
class AltTextAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        return "alt_text"
    
    @property
    def description(self) -> str:
        return "Detect missing alt text on images"
    
    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []
        
        for img in soup.find_all("img"):
            if not img.get("alt"):
                issues.append({
                    "code": "IMG_MISSING_ALT",
                    "message": "Image missing alt text.",
                    "context": str(img)[:200],
                })
        
        return issues
```

#### Lazy Initialization (`src/analyzers/__init__.py`)

```python
def init_default_analyzers():
    """Register built-in analyzers on first use."""
    registry = get_registry()
    registry.register(AltTextAnalyzer())
    registry.register(FormLabelAnalyzer())
    registry.register(HeadingOrderAnalyzer())
    registry.register(ContrastAnalyzer())
    registry.register(LinkTextAnalyzer())
```

---

### 4. Data Layer

#### SQLite Storage (`src/core/storage.py`)

Simple persistence for scan results.

**Schema**:
```sql
CREATE TABLE scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,      -- Domain being scanned
    url TEXT NOT NULL,       -- Specific page URL
    issues_json TEXT,        -- JSON array of issues
    ts INTEGER               -- Unix timestamp
);
```

**Operations**:
```python
def init_db(db_path: str) -> None:
    """Create database and table if not exists."""

def save_scan_result(db_path: str, site: str, url: str, issues: List[Dict]) -> None:
    """Insert a scan result."""

def get_scan_results(db_path: str, site: Optional[str] = None) -> List[Dict]:
    """Query scan results, optionally filtered by site."""
```

#### Logging (`src/core/logging.py`)

Centralized logging configuration with optional Rich integration.

```python
def setup_logging(level: int = logging.INFO, use_rich: Optional[bool] = None):
    """
    Configure logging:
    - Use Rich handler if available and enabled
    - Fall back to standard StreamHandler
    - Install Rich tracebacks for better error display
    """
```

---

## Data Flow

### Single Page Scan

```
User Input (URL/File)
         │
         ▼
┌─────────────────────┐
│   Fetch HTML        │ ◄─── requests/file read
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Initialize        │ ◄─── Lazy load analyzers
│   Analyzer Registry │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Run Each Analyzer │ ◄─── BeautifulSoup parsing
│   - alt_text        │
│   - form_labels     │
│   - heading_order   │
│   - contrast        │
│   - link_text       │
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│   Aggregate Issues  │
└──────────┬──────────┘
           ▼
    ┌──────┴──────┐
    ▼             ▼
┌────────┐   ┌────────┐
│ Fixes? │   │  AI?   │
└───┬────┘   └───┬────┘
    ▼            ▼
┌────────┐   ┌────────┐
│ Apply  │   │OpenAI  │
│ Fixes  │   │Suggest │
└───┬────┘   └───┬────┘
    └──────┬─────┘
           ▼
┌─────────────────────┐
│   Output Report     │ ◄─── JSON/Pretty/HTML
└─────────────────────┘
```

### Site Crawl Scan

```
Start URL
    │
    ▼
┌────────────────────────────┐
│  Fetch robots.txt          │
│  Parse User-agent rules    │
│  Get Crawl-delay           │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│  Fetch sitemap.xml         │
│  Extract <loc> URLs        │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│  Initialize Queue          │
│  Add start URL + sitemap   │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│  Spawn N Workers           │
│  (asyncio.create_task)     │
└────────────┬───────────────┘
             ▼
      ┌──────┴──────┐
      ▼             ▼
┌──────────┐   ┌──────────┐
│ Worker 1 │   │ Worker N │  (concurrent)
└────┬─────┘   └────┬─────┘
     └──────┬───────┘
            ▼
┌────────────────────────────┐
│  For each URL from queue:  │
│  1. Skip if seen           │
│  2. Check robots rules     │
│  3. Fetch HTML (semaphore) │
│  4. Analyze with registry  │
│  5. Save to DB (optional)  │
│  6. Extract <a href> links │
│  7. Add new URLs to queue  │
│  8. Sleep crawl-delay      │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│  Stop when:                │
│  - Queue empty, or         │
│  - max_pages reached       │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│  Return issues_map:        │
│  { url: [issues], ... }    │
└────────────────────────────┘
```

---

## Extension Points

### Adding a New Analyzer

1. Create analyzer class in `src/analyzers/plugins.py`:

```python
class MyNewAnalyzer(Analyzer):
    @property
    def name(self) -> str:
        return "my_analyzer"
    
    @property
    def description(self) -> str:
        return "Description of what it checks"
    
    def analyze(self, html: str) -> List[Dict[str, Any]]:
        # Implementation
        return issues
```

2. Register in `src/analyzers/__init__.py`:

```python
def init_default_analyzers():
    registry = get_registry()
    # ... existing analyzers
    registry.register(MyNewAnalyzer())
```

### Adding a New API Endpoint

1. Create router in `src/api/routes/`:

```python
# src/api/routes/scan.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/scan")
async def trigger_scan(url: str):
    # Implementation
    return {"status": "started"}
```

2. Include in `src/api/api.py`:

```python
from routes.scan import router as scan_router

app.include_router(scan_router, prefix="/api")
```

### Adding a New Fix Type

1. Add fix logic in `src/ai/accessibility/fixes.py`:

```python
def apply_fixes(html, issues, ...):
    # ... existing fixes
    
    # New fix for BUTTON_NO_TEXT
    for button in soup.find_all("button"):
        # Check if this element is in issues
        # Apply fix
        applied.append({
            "code": "BUTTON_NO_TEXT",
            "fix": "Added aria-label",
            "context": str(button)[:200]
        })
```

---

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required for AI suggestions |
| `AI_MODEL` | `gpt-4` | OpenAI model to use |
| `CONCURRENCY` | `10` | Default concurrent requests |
| `MAX_PAGES` | `200` | Default max pages to scan |
| `REQUEST_DELAY` | `0.0` | Delay between requests |
| `USE_RICH_LOGGER` | `1` | Enable Rich logging |
| `API_HOST` | `0.0.0.0` | API server host |
| `API_PORT` | `8000` | API server port |
| `REQUESTS_TIMEOUT` | `10` | HTTP request timeout |
| `USER_AGENT` | `SiteAble...` | HTTP User-Agent header |
| `LOG_LEVEL` | `info` | Logging verbosity |

---

## Testing Architecture

```
tests/
├── test_accessibility_analyzer.py   # Core analyzer tests
├── test_analyzers_plugins.py        # Individual plugin tests
├── test_crawler.py                  # Crawler with mocked HTTP
└── test_fixes.py                    # Fix engine tests
```

**Test Patterns**:

1. **Unit Tests** - Individual analyzer functions
2. **Integration Tests** - Full analysis pipeline
3. **Mock Tests** - Crawler with MockTransport

```python
# Example: Mocking HTTP for crawler tests
def make_mock_transport():
    async def handler(request: Request):
        if request.url.path == "/robots.txt":
            return Response(200, text="...")
        # ...
    return MockTransport(handler)
```
