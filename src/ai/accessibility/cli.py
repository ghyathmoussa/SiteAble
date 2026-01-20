import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

from .__version__ import __version__
from .analyzer import analyze_html, summarize_issues, suggest_fixes_with_ai
from .analyzer_plugin import list_analyzers
from .utils import fetch_url
from core.logging import setup_logging
from core.severity import (
    CRITICAL,
    MAJOR,
    MINOR,
    enrich_issues,
    get_severity_emoji,
    sort_by_severity,
    summarize_by_severity,
)

# Load .env if present
load_dotenv()

logger = logging.getLogger("siteable")


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _merge_config(args: argparse.Namespace, cfg: Dict[str, Any]) -> argparse.Namespace:
    """Merge JSON config file values into parsed args where not provided on CLI."""
    for k, v in cfg.items():
        if hasattr(args, k) and getattr(args, k) in (None, False, ""):
            setattr(args, k, v)
    return args


def _pretty_print_issues_grouped(issues: List[Dict[str, Any]]) -> None:
    """Print issues grouped by severity with colors and emojis."""
    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    # Enrich and sort issues
    enriched = enrich_issues(issues)
    sorted_issues = sort_by_severity(enriched)
    severity_counts = summarize_by_severity(enriched)

    if use_rich:
        # Summary table
        summary_table = Table(title="Issue Summary by Severity")
        summary_table.add_column("Severity", style="bold")
        summary_table.add_column("Count", justify="right")

        if severity_counts[CRITICAL] > 0:
            summary_table.add_row(f"🔴 {CRITICAL.upper()}", str(severity_counts[CRITICAL]), style="red")
        if severity_counts[MAJOR] > 0:
            summary_table.add_row(f"🟡 {MAJOR.upper()}", str(severity_counts[MAJOR]), style="yellow")
        if severity_counts[MINOR] > 0:
            summary_table.add_row(f"🔵 {MINOR.upper()}", str(severity_counts[MINOR]), style="blue")

        summary_table.add_row("TOTAL", str(len(issues)), style="bold")
        console.print(summary_table)
        console.print()

        # Issues table
        if sorted_issues:
            issues_table = Table(title="Issues Found", show_lines=True)
            issues_table.add_column("Sev", width=3)
            issues_table.add_column("Code", style="cyan")
            issues_table.add_column("WCAG", style="green")
            issues_table.add_column("Message")
            issues_table.add_column("Context", max_width=40)

            for issue in sorted_issues[:50]:  # Limit to 50 issues in pretty print
                emoji = get_severity_emoji(issue.get("severity", MINOR))
                issues_table.add_row(
                    emoji,
                    issue.get("code", ""),
                    issue.get("wcag", ""),
                    issue.get("message", ""),
                    (issue.get("context", "") or "")[:40] + "...",
                )

            console.print(issues_table)

            if len(sorted_issues) > 50:
                console.print(f"\n[dim]... and {len(sorted_issues) - 50} more issues (use --format json for full list)[/dim]")
    else:
        # Fallback to plain text
        print("\n=== Issue Summary by Severity ===")
        print(f"  🔴 CRITICAL: {severity_counts[CRITICAL]}")
        print(f"  🟡 MAJOR:    {severity_counts[MAJOR]}")
        print(f"  🔵 MINOR:    {severity_counts[MINOR]}")
        print(f"  ─────────────────")
        print(f"  TOTAL:       {len(issues)}")
        print()

        if sorted_issues:
            print("=== Issues Found ===")
            for issue in sorted_issues[:50]:
                emoji = get_severity_emoji(issue.get("severity", MINOR))
                code = issue.get("code", "UNKNOWN")
                wcag = issue.get("wcag", "")
                message = issue.get("message", "")
                print(f"  {emoji} [{code}] (WCAG {wcag})")
                print(f"     {message}")
                print()

            if len(sorted_issues) > 50:
                print(f"... and {len(sorted_issues) - 50} more issues (use --format json for full list)")


def _pretty_print_report(report: Dict[str, Any]) -> None:
    """Pretty print a scan report."""
    if "pages" in report:
        # Site scan report
        total_issues = 0
        all_issues = []

        for page, entry in report["pages"].items():
            page_issues = entry.get("issues", [])
            total_issues += len(page_issues)
            all_issues.extend(page_issues)

        print(f"\n📊 Site Scan Complete: {len(report['pages'])} pages scanned")
        print(f"   Total issues found: {total_issues}\n")

        # Print per-page summary
        for page, entry in report["pages"].items():
            issue_count = len(entry.get("issues", []))
            status = "✅" if issue_count == 0 else "⚠️"
            print(f"  {status} {page}: {issue_count} issues")

        print()

        # Print aggregated severity summary
        if all_issues:
            _pretty_print_issues_grouped(all_issues)
    else:
        # Single page report
        issues = report.get("issues", [])
        print(f"\n📊 Scan Complete: {len(issues)} issues found\n")
        _pretty_print_issues_grouped(issues)

    # Show fixes applied
    if report.get("fixed_fixes"):
        print(f"\n🔧 Fixes Applied: {len(report['fixed_fixes'])}")
        for fix in report["fixed_fixes"][:10]:
            print(f"   - {fix.get('code')}: {fix.get('fix')}")

    # Show AI suggestions
    if report.get("ai_suggestions"):
        print("\n🤖 AI Suggestions:")
        print(report["ai_suggestions"][:500])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="SiteAble - AI-Powered Accessibility Scanner for Websites",
        epilog="Examples:\n"
        "  siteable --url https://example.com --scan-site --concurrency 5\n"
        "  siteable --file page.html --apply-fixes --outdir fixes/\n"
        "  siteable --url https://example.com --format json --output report.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Version
    parser.add_argument(
        "--version", "-V",
        action="version",
        version=f"SiteAble v{__version__}",
    )

    # Input options
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="URL of the page to scan")
    group.add_argument("--file", help="Local HTML file to scan")

    # Configuration
    parser.add_argument("--config", help="Path to JSON/YAML config file with default options")

    # AI options
    parser.add_argument(
        "--ai",
        action="store_true",
        help="Enable AI suggestions (requires OPENAI_API_KEY)",
    )

    # Output options
    parser.add_argument("--output", "-o", help="Write output to this file (default: stdout)")
    parser.add_argument(
        "--format", "-f",
        choices=["json", "pretty", "html"],
        default="pretty",
        help="Output format (default: pretty)",
    )
    parser.add_argument(
        "--output-html",
        help="Generate HTML report at specified path",
    )

    # Site scanning options
    parser.add_argument(
        "--scan-site",
        action="store_true",
        help="Crawl site from --url and scan multiple pages",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("CONCURRENCY", "10")),
        help="Concurrent page fetches for --scan-site (default: 10)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=int(os.environ.get("MAX_PAGES", "200")),
        help="Maximum pages to scan for --scan-site (default: 200)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=float(os.environ.get("REQUEST_DELAY", "0.0")),
        help="Delay between requests for --scan-site (default: 0.0)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.0,
        help="Max requests per second (0 = unlimited)",
    )

    # Fix options
    parser.add_argument(
        "--apply-fixes",
        action="store_true",
        help="Apply one-click fixes and output fixed HTML",
    )
    parser.add_argument(
        "--outdir",
        help="Directory to write fixed files when using --scan-site --apply-fixes",
    )

    # Database options
    parser.add_argument(
        "--save-db",
        help="Save scan results to SQLite database at this path",
    )

    # Analyzer options
    parser.add_argument(
        "--exclude-analyzers",
        help="Comma-separated list of analyzer names to skip (e.g., 'contrast,alt_text')",
    )
    parser.add_argument(
        "--list-analyzers",
        action="store_true",
        help="List available analyzers and exit",
    )

    # WCAG level
    parser.add_argument(
        "--wcag-level",
        choices=["AA", "AAA"],
        default="AA",
        help="WCAG conformance level (default: AA)",
    )

    # Logging options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only output essential information")

    args = parser.parse_args(argv)

    # Load config file if present and merge
    if args.config:
        try:
            config_path = args.config
            if config_path.endswith((".yaml", ".yml")):
                try:
                    import yaml
                    with open(config_path, "r", encoding="utf-8") as cf:
                        cfg = yaml.safe_load(cf)
                except ImportError:
                    print("PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)
                    return 2
            else:
                with open(config_path, "r", encoding="utf-8") as cf:
                    cfg = json.load(cf)
            args = _merge_config(args, cfg)
        except Exception as e:
            print(f"Failed to load config {args.config}: {e}", file=sys.stderr)
            return 2

    # Logging via centralized setup (uses rich if installed)
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    if args.quiet:
        level = logging.WARNING
    use_rich = os.environ.get("USE_RICH_LOGGER", "1") not in ("0", "false", "False")
    setup_logging(level=level, use_rich=use_rich)
    logger.setLevel(level)

    # List available analyzers
    if args.list_analyzers:
        analyzers = list_analyzers()
        print("Available analyzers:")
        for name, desc in analyzers.items():
            print(f"  {name}: {desc}")
        return 0

    # Require --url or --file for scanning
    if not args.url and not args.file:
        parser.error("one of the arguments --url --file is required")

    # Compute exclude list
    exclude_analyzers = None
    if args.exclude_analyzers:
        exclude_analyzers = [a.strip() for a in args.exclude_analyzers.split(",") if a.strip()]

    # Site scan flow
    if args.scan_site:
        if not args.url:
            parser.error("--scan-site requires --url to be specified")

        from crawler.crawler_scanner import scan_site
        from .fixes import apply_fixes

        logger.info(f"Starting site scan: {args.url}")
        logger.info(f"Max pages: {args.max_pages}, Concurrency: {args.concurrency}")

        issues_map = scan_site(
            args.url,
            max_pages=args.max_pages,
            concurrency=args.concurrency,
            delay=args.delay,
            db_path=args.save_db,
            exclude_analyzers=exclude_analyzers,
        )

        report = {"pages": {}, "version": __version__}
        all_issues = []

        for page, issues in issues_map.items():
            # Enrich issues with severity
            enriched = enrich_issues(issues)
            entry = {
                "issues": enriched,
                "summary": summarize_issues(issues),
                "severity_summary": summarize_by_severity(enriched),
            }
            all_issues.extend(enriched)

            if args.apply_fixes:
                try:
                    html_text = fetch_url(page)
                    fixed_html, applied = apply_fixes(html_text, issues)
                    entry["fixed_fixes"] = applied
                    if args.outdir:
                        os.makedirs(args.outdir, exist_ok=True)
                        fname = page.replace("://", "_").replace("/", "_") + ".html"
                        with open(os.path.join(args.outdir, fname), "w", encoding="utf-8") as f:
                            f.write(fixed_html)
                    else:
                        entry["fixed_html_snippet"] = fixed_html[:2000]
                except Exception as e:
                    entry["fixed_error"] = str(e)

            report["pages"][page] = entry

        # Add overall severity summary
        report["severity_summary"] = summarize_by_severity(all_issues)

        if args.ai:
            report["ai_report"] = suggest_fixes_with_ai("\n".join(issues_map.keys()), [])

        # Generate HTML report if requested
        if args.output_html:
            try:
                from reporting.html_report import generate_html_report
                generate_html_report(report, args.output_html)
                logger.info(f"HTML report saved to: {args.output_html}")
            except ImportError:
                logger.warning("HTML report generation not available")
            except Exception as e:
                logger.error(f"Failed to generate HTML report: {e}")

        # Output
        if args.format == "json":
            out = json.dumps(report, indent=2)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(out)
            else:
                print(out)
        else:
            _pretty_print_report(report)

        return 0

    # Single page flow
    try:
        if args.url:
            logger.info(f"Scanning URL: {args.url}")
            html = fetch_url(args.url)
        else:
            logger.info(f"Scanning file: {args.file}")
            html = _read_file(args.file)
    except Exception as e:
        print(f"Failed to load page: {e}", file=sys.stderr)
        return 2

    issues = analyze_html(html, exclude_analyzers=exclude_analyzers)

    # Enrich issues with severity
    enriched_issues = enrich_issues(issues)

    summary = summarize_issues(issues)
    severity_summary = summarize_by_severity(enriched_issues)

    report = {
        "issues": enriched_issues,
        "summary": summary,
        "severity_summary": severity_summary,
        "version": __version__,
    }

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

    # Generate HTML report if requested
    if args.output_html:
        try:
            from reporting.html_report import generate_html_report
            generate_html_report(report, args.output_html)
            logger.info(f"HTML report saved to: {args.output_html}")
        except ImportError:
            logger.warning("HTML report generation not available")
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

    if args.format == "json":
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
