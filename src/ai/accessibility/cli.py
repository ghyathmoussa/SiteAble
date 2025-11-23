import argparse
import json
import sys

from .analyzer import analyze_html, summarize_issues, suggest_fixes_with_ai
from .analyzer_plugin import list_analyzers
from .utils import fetch_url


def _read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description="AI-Powered Accessibility scanner for small websites")
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--url", help="URL of the page to scan")
    group.add_argument("--file", help="Local HTML file to scan")
    parser.add_argument("--ai", action="store_true", help="Enable AI suggestions (requires OPENAI_API_KEY)")
    parser.add_argument("--output", help="Write JSON report to this file (default stdout)")
    parser.add_argument("--scan-site", action="store_true", help="Crawl site from --url and scan multiple pages")
    parser.add_argument("--apply-fixes", action="store_true", help="Apply one-click fixes and print fixed HTML (or write files when scanning site to outdir)")
    parser.add_argument("--outdir", help="Directory to write fixed files when using --scan-site --apply-fixes")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent page fetches for --scan-site (default 10)")
    parser.add_argument("--max-pages", type=int, default=200, help="Maximum pages to scan for --scan-site (default 200)")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay between requests for --scan-site (default 0.0)")
    parser.add_argument("--save-db", help="Save scan results to SQLite database at this path")
    parser.add_argument("--exclude-analyzers", help="Comma-separated list of analyzer names to skip (e.g., 'contrast,alt_text')")
    parser.add_argument("--list-analyzers", action="store_true", help="List available analyzers and exit")
    args = parser.parse_args(argv)

    if args.list_analyzers:
        analyzers = list_analyzers()
        print("Available analyzers:")
        for name, desc in analyzers.items():
            print(f"  {name}: {desc}")
        return 0

    # require --url or --file if not listing analyzers
    if not args.url and not args.file:
        parser.error("one of the arguments --url --file is required")

    exclude_analyzers = None
    if args.exclude_analyzers:
        exclude_analyzers = [a.strip() for a in args.exclude_analyzers.split(',')]

    try:
        if args.url:
            html = fetch_url(args.url)
        else:
            html = _read_file(args.file)
    except Exception as e:
        print(f"Failed to load page: {e}", file=sys.stderr)
        return 2

    if args.scan_site:
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
            html_text = None
            if args.apply_fixes:
                # fetch original HTML and apply fixes
                try:
                    html_text = fetch_url(page)
                    fixed_html, applied = apply_fixes(html_text, issues)
                    entry["fixed_fixes"] = applied
                    if args.outdir:
                        import os
                        os.makedirs(args.outdir, exist_ok=True)
                        # create filename-safe path
                        fname = page.replace('://', '_').replace('/', '_') + '.html'
                        with open(os.path.join(args.outdir, fname), 'w', encoding='utf-8') as f:
                            f.write(fixed_html)
                    else:
                        entry["fixed_html"] = fixed_html[:2000]
                except Exception as e:
                    entry["fixed_error"] = str(e)
            report["pages"][page] = entry
        if args.ai:
            report["ai_report"] = suggest_fixes_with_ai(''.join(issues_map.keys()), [])
        out = json.dumps(report, indent=2)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(out)
        else:
            print(out)
        return 0

    # single page flow
    issues = analyze_html(html, exclude_analyzers=exclude_analyzers)
    summary = summarize_issues(issues)
    report = {"issues": issues, "summary": summary}

    if args.apply_fixes:
        from .fixes import apply_fixes
        fixed_html, applied = apply_fixes(html, issues)
        report["fixed_fixes"] = applied
        report["fixed_html"] = fixed_html[:2000]

    if args.ai:
        report["ai_suggestions"] = suggest_fixes_with_ai(html, issues)

    out = json.dumps(report, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
