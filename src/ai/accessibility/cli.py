import argparse
import json
import logging
import sys
import os
from typing import Any, Dict

from dotenv import load_dotenv

from .analyzer import analyze_html, summarize_issues, suggest_fixes_with_ai
from .analyzer_plugin import list_analyzers
from .utils import fetch_url
from core.logging import setup_logging

# Load .env if present
load_dotenv()

logger = logging.getLogger("siteable")


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _merge_config(args: argparse.Namespace, cfg: Dict[str, Any]) -> argparse.Namespace:
    """Merge JSON config file values into parsed args where not provided on CLI."""
    for k, v in cfg.items():
        if hasattr(args, k) and getattr(args, k) in (None, False, ''):
            setattr(args, k, v)
    return args


def _pretty_print_report(report: Dict[str, Any]):
    if 'pages' in report:
        for page, entry in report['pages'].items():
            print(f"{page}: {len(entry.get('issues', []))} issues")
            for code, count in entry.get('summary', {}).items():
                print(f"  - {code}: {count}")
    else:
        print("Single page report:")
        for code, count in report.get('summary', {}).items():
            print(f"  - {code}: {count}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="AI-Powered Accessibility scanner for small websites",
        epilog="Examples:\n  siteable --url https://example.com --scan-site --concurrency 5\n  siteable --file page.html --apply-fixes --outdir fixes/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="URL of the page to scan")
    group.add_argument("--file", help="Local HTML file to scan")
    parser.add_argument("--config", help="Path to JSON config file with default options")
    parser.add_argument("--ai", action="store_true", help="Enable AI suggestions (requires OPENAI_API_KEY)")
    parser.add_argument("--output", help="Write output to this file (default stdout)")
    parser.add_argument("--format", choices=["json", "pretty"], default="pretty", help="Output format (json or pretty)")
    parser.add_argument("--scan-site", action="store_true", help="Crawl site from --url and scan multiple pages")
    parser.add_argument("--apply-fixes", action="store_true", help="Apply one-click fixes and print fixed HTML (or write files when scanning site to outdir)")
    parser.add_argument("--outdir", help="Directory to write fixed files when using --scan-site --apply-fixes")
    parser.add_argument("--concurrency", type=int, default=int(os.environ.get('CONCURRENCY', '10')), help="Concurrent page fetches for --scan-site (default 10)")
    parser.add_argument("--max-pages", type=int, default=int(os.environ.get('MAX_PAGES', '200')), help="Maximum pages to scan for --scan-site (default 200)")
    parser.add_argument("--delay", type=float, default=float(os.environ.get('REQUEST_DELAY', '0.0')), help="Delay between requests for --scan-site (default 0.0)")
    parser.add_argument("--save-db", help="Save scan results to SQLite database at this path")
    parser.add_argument("--exclude-analyzers", help="Comma-separated list of analyzer names to skip (e.g., 'contrast,alt_text')")
    parser.add_argument("--list-analyzers", action="store_true", help="List available analyzers and exit")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--quiet", action="store_true", help="Only output essential information")
    args = parser.parse_args(argv)

    # Load config file if present and merge
    if args.config:
        try:
            with open(args.config, 'r', encoding='utf-8') as cf:
                cfg = json.load(cf)
            args = _merge_config(args, cfg)
        except Exception as e:
            print(f"Failed to load config {args.config}: {e}", file=sys.stderr)
            return 2

    # logging via centralized setup (uses rich if installed)
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    use_rich = os.environ.get("USE_RICH_LOGGER", "1") not in ("0", "false", "False")
    setup_logging(level=level, use_rich=use_rich)
    logger.setLevel(level)

    # list available analyzers
    if args.list_analyzers:
        analyzers = list_analyzers()
        print("Available analyzers:")
        for name, desc in analyzers.items():
            print(f"  {name}: {desc}")
        return 0

    # require --url or --file for scanning single pages or site
    if not args.url and not args.file:
        parser.error("one of the arguments --url --file is required")

    # compute exclude list
    exclude_analyzers = None
    if args.exclude_analyzers:
        exclude_analyzers = [a.strip() for a in args.exclude_analyzers.split(',') if a.strip()]

    # Site scan flow
    if args.scan_site:
        if not args.url:
            parser.error("--scan-site requires --url to be specified")
        from crawler.crawler_scanner import scan_site
        from .fixes import apply_fixes

        issues_map = scan_site(
            args.url,
            max_pages=args.max_pages,
            concurrency=args.concurrency,
            delay=args.delay,
            db_path=args.save_db,
            exclude_analyzers=exclude_analyzers,
        )

        report = {"pages": {}}
        for page, issues in issues_map.items():
            entry = {"issues": issues, "summary": summarize_issues(issues)}
            if args.apply_fixes:
                try:
                    html_text = fetch_url(page)
                    fixed_html, applied = apply_fixes(html_text, issues)
                    entry["fixed_fixes"] = applied
                    if args.outdir:
                        os.makedirs(args.outdir, exist_ok=True)
                        fname = page.replace('://', '_').replace('/', '_') + '.html'
                        with open(os.path.join(args.outdir, fname), 'w', encoding='utf-8') as f:
                            f.write(fixed_html)
                    else:
                        entry["fixed_html_snippet"] = fixed_html[:2000]
                except Exception as e:
                    entry["fixed_error"] = str(e)
            report["pages"][page] = entry

        if args.ai:
            report["ai_report"] = suggest_fixes_with_ai('\n'.join(issues_map.keys()), [])

        # output
        if args.format == 'json':
            out = json.dumps(report, indent=2)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(out)
            else:
                print(out)
        else:
            _pretty_print_report(report)
        return 0

    # single page flow
    try:
        if args.url:
            html = fetch_url(args.url)
        else:
            html = _read_file(args.file)
    except Exception as e:
        print(f"Failed to load page: {e}", file=sys.stderr)
        return 2

    issues = analyze_html(html, exclude_analyzers=exclude_analyzers)
    summary = summarize_issues(issues)
    report = {"issues": issues, "summary": summary}

    if args.apply_fixes:
        from .fixes import apply_fixes

        try:
            fixed_html, applied = apply_fixes(html, issues)
            report["fixed_fixes"] = applied
            report["fixed_html_snippet"] = fixed_html[:2000]
        except Exception as e:
            report["fixed_error"] = str(e)

    if args.ai:
        try:
            report["ai_suggestions"] = suggest_fixes_with_ai(html, issues)
        except Exception:
            report["ai_suggestions"] = None

    if args.format == 'json':
        out = json.dumps(report, indent=2)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(out)
        else:
            print(out)
    else:
        _pretty_print_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
