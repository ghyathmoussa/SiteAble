# SiteAble — Accessibility Scanner for Small Websites

[![CI](https://github.com/ghyathmoussa/SiteAble/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ghyathmoussa/SiteAble/actions/workflows/ci.yml)
[![Codecov](https://codecov.io/gh/ghyathmoussa/SiteAble/branch/main/graph/badge.svg)](https://codecov.io/gh/ghyathmoussa/SiteAble)
[![License](https://img.shields.io/github/license/ghyathmoussa/SiteAble.svg)](LICENSE)
[![Open Source Love](https://img.shields.io/badge/Open%20Source-MIT-brightgreen.svg)](LICENSE)
[![Python Versions](https://img.shields.io/badge/python-3.11%2C%203.12-blue.svg)](https://www.python.org/)
[![Maintained?](https://img.shields.io/badge/maintained-yes-green.svg)](https://github.com/ghyathmoussa/SiteAble)


SiteAble is a lightweight, plugin-based accessibility scanner for small websites. It offers both a CLI and a REST API for running accessibility checks, generating one-click fixes, and storing scan results for later inspection.

Key features
- Plugin-based analyzers (alt text, form labels, headings, contrast, link text)
- Single-page and site-wide crawling (sitemap discovery, robots.txt respect)
- Asynchronous, concurrent site crawling (via `httpx` & `asyncio`)
- One-click automatic fixes for issues like missing `alt` attributes and low contrast
- Optional AI-powered suggestions using OpenAI (if `OPENAI_API_KEY` is available)
- Persist scan results to an SQLite database and view via a minimal API dashboard

This repository contains an example scanner that's intentionally small and extendable.

Table of contents
- [Quickstart](#quickstart)
- [How it works (overview)](#how-it-works-overview)
- [CLI usage](#cli-usage)
- [API usage](#api-usage)
- [Analyzer plugins](#analyzer-plugins)
- [Fixes & AI suggestions](#fixes--ai-suggestions)
- [Persistence & Dashboard](#persistence--dashboard)
- [Development & Tests](#development--tests)
- [Extending SiteAble](#extending-siteable)
- [Environment variables](#environment-variables)
- [License](#license)

---


## Supported Python Versions

This project is tested on Python 3.11 and 3.12 via GitHub Actions.

## Quickstart

1) Create a virtual environment, install dependencies, and run tests (Python 3.11/3.12 recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

2) Run a single page scan (CLI):

```bash
# from repo root
cd src
python -m ai.accessibility.cli --url https://example.com
```

3) Run a site scan with concurrency and persistence (CLI):

```bash
# scan site, save to SQLite file
cd src
python -m ai.accessibility.cli --url https://example.com --scan-site --concurrency 10 --max-pages 200 --save-db ../data/siteable_scans.db
```

4) Run the API (view scan results):

```bash
# from src
python api/api.py
# Then visit GET http://127.0.0.1:8000/api/dashboard/example.com
```

Tip: The CLI also supports local HTML files via `--file path/to/file.html`.

---

## How it works (overview)

SiteAble is composed of a few main parts:

- CLI (`ai.accessibility.cli`) — single-page and site crawling, persistence and fixes
- Crawler (`crawler.crawler_scanner`) — enhanced async scanning with robots.txt & sitemap support
- Analyzers (`analyzers/plugins.py`) — plugin analyzers that implement `Analyzer.analyze(html)`
- Analyzer registry (`core/analyzer.py`) — global registry to register plugins and run analyzers
- Fixes (`ai/accessibility/fixes.py`) — simple one-click fixes; add alt attributes and fix contrast
- AI helpers (`ai/accessibility/analyzer.py`) — optional OpenAI integration for suggested fixes
- Storage (`core/storage.py`) — SQLite helper functions to store and query scans
- API (`api/api.py`, `api/routes/dashboard.py`) — FastAPI app to expose stored scans

Data flow (site scan): crawl → fetch HTML → analyze with analyzers → persist → report

---

## CLI usage

The CLI exposes several useful flags and options available in `ai/accessibility/cli.py`:

- `--url`: scan a remote URL
- `--file`: scan a local HTML file
- `--scan-site`: crawl and scan multiple pages under the provided URL
- `--concurrency`: number of concurrent requests (site scan)
- `--max-pages`: limit to the number of pages scanned (site scan)
- `--delay`: time (seconds) between requests
- `--save-db`: path to SQLite DB to persist scan results
- `--apply-fixes`: apply one-click fixes, print or write fixed files
- `--outdir`: directory to write fixed files when scanning sites
- `--ai`: enable OpenAI suggestions (requires `OPENAI_API_KEY`)
- `--exclude-analyzers`: comma-separated list of analyzer names to skip

Examples:

```bash
python -m ai.accessibility.cli --url https://example.com --scan-site --concurrency 5 --save-db ../data/siteable_scans.db
python -m ai.accessibility.cli --file page.html --apply-fixes --format json
```

Use `--list-analyzers` to view installed analyzers.

---

## API usage

Run the API server with:

```bash
cd src
python api/api.py
```

Endpoints (currently minimal):

- `GET /api/dashboard/{site}` — returns saved scans for the site (reads from `data/siteable_scans.db` by default)

Note: The API is intentionally small and can be extended to add scanning jobs, scheduling, authentication, and a richer dashboard.

---

## Analyzer plugins

Analyzers follow the `Analyzer` interface in `core/analyzer.py`:

- `name` property (unique string)
- `description` property (string)
- `analyze(html: str)` method which returns a list of issues (dicts)

Built-in analyzers (registered by `analyzers.init_default_analyzers()`) include:
- `alt_text` — finds missing `alt` on images and images inside links
- `form_labels` — detects form controls missing labels
- `heading_order` — notices jumping heading levels
- `contrast` — detects low contrast from inline styles
- `link_text` — detects links without accessible names

To add new analyzers: add a new class that inherits `Analyzer` in `analyzers/plugins.py` and register it in `analyzers/__init__.py`.

---

## Fixes & AI suggestions

- `ai/accessibility/fixes.py` contains helper logic to automatically apply some fixes:
  - Add `alt` attributes to images flagged as missing
  - Adjust inline style colors to an accessible foreground when contrast is low
- For richer, human-friendly suggestions, `ai/accessibility/analyzer.suggest_fixes_with_ai` can generate suggestions via OpenAI when `openai` is installed and `OPENAI_API_KEY` is provided.

---

## Persistence & Dashboard

SiteAble uses a small SQLite DB to store scan results via `core/storage.py`.
Default DB path used by the API is `data/siteable_scans.db`. You can change it when invoking the CLI with `--save-db <path>`.

Schema (scans table):

- `id` INTEGER PRIMARY KEY
- `site` TEXT
- `url` TEXT
- `issues_json` TEXT
- `ts` INTEGER (timestamp)

The API route `GET /api/dashboard/{site}` calls `get_scan_results` to return all scans for a site.

---

## Development & Tests

1) Set up a development environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Run unit tests:

```bash
pytest -q
```

3) Linting / formatting suggestions: You can run `black` / `ruff` / `isort` as desired (not included by default).

---

## Extending SiteAble

- Add a new analyzer: create a new `Analyzer` subclass and register it in `analyzers.__init__.py`.
- Add API endpoints:
  - Create a new router under `src/api/routes` and add it to `api/api.py` via `app.include_router`.
- Add async job scheduling or a job queue for scanning long-running sites.
- Improve robots parsing and add sitemapindex support in `crawler/crawler_scanner.py`.

---

## Environment variables

The following environment variables control runtime behavior:

- `OPENAI_API_KEY` — (optional) enable AI suggestions
- `CONCURRENCY`, `MAX_PAGES`, `REQUEST_DELAY` — default values for CLI scanning
- `USE_RICH_LOGGER` — set to `0` to disable `rich` logging if installed
- `API_HOST`, `API_PORT` — host and port for the `api/api.py` uvicorn server

---

## License

This project is distributed under the terms in `LICENSE`.

---

Want help? Open an issue, or submit a PR that improves analyzers, CLI UX, or the UI dashboard. See `todo.txt` for planned enhancements.
# SiteAble