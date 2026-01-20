"""HTML report generator for SiteAble accessibility scans."""

import html
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.severity import CRITICAL, MAJOR, MINOR, get_severity_emoji, summarize_by_severity


def generate_html_report(
    report: Dict[str, Any],
    output_path: str,
    title: Optional[str] = None,
) -> str:
    """Generate an HTML report from scan results.

    Args:
        report: Scan results dictionary (single page or site scan)
        output_path: Path to write the HTML report
        title: Optional title for the report

    Returns:
        Path to the generated report
    """
    # Determine if this is a site scan or single page
    is_site_scan = "pages" in report

    if is_site_scan:
        html_content = _generate_site_report(report, title)
    else:
        html_content = _generate_page_report(report, title)

    # Write to file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")

    return str(output_path)


def _generate_site_report(report: Dict[str, Any], title: Optional[str] = None) -> str:
    """Generate HTML report for site-wide scan."""
    pages = report.get("pages", {})
    severity_summary = report.get("severity_summary", {})
    version = report.get("version", "1.0.0")

    # Calculate totals
    total_pages = len(pages)
    total_issues = sum(len(p.get("issues", [])) for p in pages.values())
    critical_count = severity_summary.get(CRITICAL, 0)
    major_count = severity_summary.get(MAJOR, 0)
    minor_count = severity_summary.get(MINOR, 0)

    # Generate page rows
    page_rows = []
    for url, data in sorted(pages.items(), key=lambda x: -len(x[1].get("issues", []))):
        issues = data.get("issues", [])
        page_severity = summarize_by_severity(issues)

        status_class = "success" if len(issues) == 0 else "warning" if page_severity.get(CRITICAL, 0) == 0 else "danger"
        page_rows.append(f"""
            <tr class="{status_class}">
                <td><a href="#{_url_to_id(url)}">{html.escape(url)}</a></td>
                <td class="text-center">{len(issues)}</td>
                <td class="text-center text-critical">{page_severity.get(CRITICAL, 0)}</td>
                <td class="text-center text-major">{page_severity.get(MAJOR, 0)}</td>
                <td class="text-center text-minor">{page_severity.get(MINOR, 0)}</td>
            </tr>
        """)

    # Generate page details
    page_details = []
    for url, data in pages.items():
        issues = data.get("issues", [])
        if issues:
            page_details.append(_generate_page_section(url, issues))

    report_title = title or "SiteAble Accessibility Report"

    return _get_html_template().format(
        title=html.escape(report_title),
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        version=version,
        total_pages=total_pages,
        total_issues=total_issues,
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        page_rows="".join(page_rows),
        page_details="".join(page_details),
        chart_data=json.dumps({
            "critical": critical_count,
            "major": major_count,
            "minor": minor_count,
        }),
    )


def _generate_page_report(report: Dict[str, Any], title: Optional[str] = None) -> str:
    """Generate HTML report for single page scan."""
    issues = report.get("issues", [])
    severity_summary = report.get("severity_summary", summarize_by_severity(issues))
    version = report.get("version", "1.0.0")

    critical_count = severity_summary.get(CRITICAL, 0)
    major_count = severity_summary.get(MAJOR, 0)
    minor_count = severity_summary.get(MINOR, 0)

    # Generate issue rows
    issue_rows = _generate_issue_rows(issues)

    report_title = title or "SiteAble Accessibility Report"

    return _get_single_page_template().format(
        title=html.escape(report_title),
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        version=version,
        total_issues=len(issues),
        critical_count=critical_count,
        major_count=major_count,
        minor_count=minor_count,
        issue_rows=issue_rows,
        chart_data=json.dumps({
            "critical": critical_count,
            "major": major_count,
            "minor": minor_count,
        }),
    )


def _generate_page_section(url: str, issues: List[Dict[str, Any]]) -> str:
    """Generate HTML section for a single page's issues."""
    issue_rows = _generate_issue_rows(issues)

    return f"""
        <section class="page-section" id="{_url_to_id(url)}">
            <h3>
                <a href="{html.escape(url)}" target="_blank" rel="noopener">{html.escape(url)}</a>
                <span class="badge">{len(issues)} issues</span>
            </h3>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th width="60">Severity</th>
                        <th width="180">Code</th>
                        <th width="80">WCAG</th>
                        <th>Message</th>
                        <th>Context</th>
                    </tr>
                </thead>
                <tbody>
                    {issue_rows}
                </tbody>
            </table>
        </section>
    """


def _generate_issue_rows(issues: List[Dict[str, Any]]) -> str:
    """Generate table rows for issues."""
    rows = []

    # Sort by severity
    severity_order = {CRITICAL: 0, MAJOR: 1, MINOR: 2}
    sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.get("severity", MINOR), 2))

    for issue in sorted_issues:
        severity = issue.get("severity", MINOR)
        code = issue.get("code", "UNKNOWN")
        wcag = issue.get("wcag", "")
        message = issue.get("message", "")
        context = issue.get("context", "")

        severity_class = severity.lower() if severity else "minor"
        emoji = get_severity_emoji(severity)

        rows.append(f"""
            <tr class="severity-{severity_class}">
                <td class="text-center">
                    <span class="severity-badge {severity_class}">{emoji} {severity.upper() if severity else 'MINOR'}</span>
                </td>
                <td><code>{html.escape(code)}</code></td>
                <td>{html.escape(wcag) if wcag else '-'}</td>
                <td>{html.escape(message)}</td>
                <td><code class="context">{html.escape(context[:100])}{'...' if len(context) > 100 else ''}</code></td>
            </tr>
        """)

    return "".join(rows)


def _url_to_id(url: str) -> str:
    """Convert URL to valid HTML id."""
    import re
    return re.sub(r"[^a-zA-Z0-9]", "-", url)[:50]


def _get_html_template() -> str:
    """Get the HTML template for site reports."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --color-critical: #dc3545;
            --color-major: #ffc107;
            --color-minor: #17a2b8;
            --color-success: #28a745;
            --color-bg: #f8f9fa;
            --color-card: #ffffff;
            --color-text: #212529;
            --color-text-muted: #6c757d;
            --color-border: #dee2e6;
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
        }}

        header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        header .meta {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: var(--color-card);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .card h3 {{
            font-size: 0.9rem;
            color: var(--color-text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .card .value {{
            font-size: 2.5rem;
            font-weight: bold;
        }}

        .card.critical .value {{ color: var(--color-critical); }}
        .card.major .value {{ color: var(--color-major); }}
        .card.minor .value {{ color: var(--color-minor); }}
        .card.success .value {{ color: var(--color-success); }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--color-card);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }}

        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }}

        th {{
            background: #f1f3f4;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        tr.success {{ border-left: 4px solid var(--color-success); }}
        tr.warning {{ border-left: 4px solid var(--color-major); }}
        tr.danger {{ border-left: 4px solid var(--color-critical); }}

        .text-center {{ text-align: center; }}
        .text-critical {{ color: var(--color-critical); font-weight: bold; }}
        .text-major {{ color: var(--color-major); font-weight: bold; }}
        .text-minor {{ color: var(--color-minor); font-weight: bold; }}

        .severity-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }}

        .severity-badge.critical {{ background: #f8d7da; color: var(--color-critical); }}
        .severity-badge.major {{ background: #fff3cd; color: #856404; }}
        .severity-badge.minor {{ background: #d1ecf1; color: #0c5460; }}

        .page-section {{
            background: var(--color-card);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .page-section h3 {{
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .page-section h3 a {{
            color: var(--color-text);
            text-decoration: none;
        }}

        .page-section h3 a:hover {{
            text-decoration: underline;
        }}

        .badge {{
            background: var(--color-bg);
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.85rem;
            font-weight: normal;
        }}

        .issues-table {{
            font-size: 0.9rem;
        }}

        code {{
            background: #f1f3f4;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85em;
        }}

        code.context {{
            display: block;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .chart-container {{
            max-width: 300px;
            margin: 0 auto 2rem;
        }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--color-text-muted);
            font-size: 0.9rem;
        }}

        @media (max-width: 768px) {{
            .container {{ padding: 1rem; }}
            .summary-cards {{ grid-template-columns: 1fr 1fr; }}
            th, td {{ padding: 0.5rem; font-size: 0.85rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {title}</h1>
            <p class="meta">Generated: {generated_date} • SiteAble v{version}</p>
        </header>

        <div class="summary-cards">
            <div class="card">
                <h3>📄 Pages Scanned</h3>
                <div class="value">{total_pages}</div>
            </div>
            <div class="card">
                <h3>⚠️ Total Issues</h3>
                <div class="value">{total_issues}</div>
            </div>
            <div class="card critical">
                <h3>🔴 Critical</h3>
                <div class="value">{critical_count}</div>
            </div>
            <div class="card major">
                <h3>🟡 Major</h3>
                <div class="value">{major_count}</div>
            </div>
            <div class="card minor">
                <h3>🔵 Minor</h3>
                <div class="value">{minor_count}</div>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="severityChart"></canvas>
        </div>

        <h2>📋 Pages Overview</h2>
        <table>
            <thead>
                <tr>
                    <th>Page URL</th>
                    <th class="text-center">Issues</th>
                    <th class="text-center">Critical</th>
                    <th class="text-center">Major</th>
                    <th class="text-center">Minor</th>
                </tr>
            </thead>
            <tbody>
                {page_rows}
            </tbody>
        </table>

        <h2>🔎 Issue Details</h2>
        {page_details}

        <footer>
            <p>Generated by <strong>SiteAble</strong> - Accessibility Scanner for Websites</p>
            <p>🔗 <a href="https://github.com/ghyathmoussa/SiteAble">github.com/ghyathmoussa/SiteAble</a></p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script>
        const chartData = {chart_data};
        const ctx = document.getElementById('severityChart');
        if (ctx && chartData.critical + chartData.major + chartData.minor > 0) {{
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: ['Critical', 'Major', 'Minor'],
                    datasets: [{{
                        data: [chartData.critical, chartData.major, chartData.minor],
                        backgroundColor: ['#dc3545', '#ffc107', '#17a2b8'],
                        borderWidth: 0,
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'bottom' }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>"""


def _get_single_page_template() -> str:
    """Get the HTML template for single page reports."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --color-critical: #dc3545;
            --color-major: #ffc107;
            --color-minor: #17a2b8;
            --color-success: #28a745;
            --color-bg: #f8f9fa;
            --color-card: #ffffff;
            --color-text: #212529;
            --color-text-muted: #6c757d;
            --color-border: #dee2e6;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--color-bg);
            color: var(--color-text);
            line-height: 1.6;
        }}

        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}

        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
        }}

        header h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
        header .meta {{ opacity: 0.9; font-size: 0.9rem; }}

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}

        .card {{
            background: var(--color-card);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .card h3 {{
            font-size: 0.85rem;
            color: var(--color-text-muted);
            margin-bottom: 0.5rem;
            text-transform: uppercase;
        }}

        .card .value {{ font-size: 2.5rem; font-weight: bold; }}
        .card.critical .value {{ color: var(--color-critical); }}
        .card.major .value {{ color: var(--color-major); }}
        .card.minor .value {{ color: var(--color-minor); }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--color-card);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--color-border);
        }}

        th {{
            background: #f1f3f4;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}

        tr:hover {{ background: #f8f9fa; }}

        .severity-badge {{
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
        }}

        .severity-badge.critical {{ background: #f8d7da; color: var(--color-critical); }}
        .severity-badge.major {{ background: #fff3cd; color: #856404; }}
        .severity-badge.minor {{ background: #d1ecf1; color: #0c5460; }}

        code {{
            background: #f1f3f4;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.85em;
        }}

        .chart-container {{ max-width: 250px; margin: 0 auto 2rem; }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--color-text-muted);
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {title}</h1>
            <p class="meta">Generated: {generated_date} • SiteAble v{version}</p>
        </header>

        <div class="summary-cards">
            <div class="card">
                <h3>⚠️ Total Issues</h3>
                <div class="value">{total_issues}</div>
            </div>
            <div class="card critical">
                <h3>🔴 Critical</h3>
                <div class="value">{critical_count}</div>
            </div>
            <div class="card major">
                <h3>🟡 Major</h3>
                <div class="value">{major_count}</div>
            </div>
            <div class="card minor">
                <h3>🔵 Minor</h3>
                <div class="value">{minor_count}</div>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="severityChart"></canvas>
        </div>

        <h2>🔎 Issues Found</h2>
        <table>
            <thead>
                <tr>
                    <th width="80">Severity</th>
                    <th width="180">Code</th>
                    <th width="80">WCAG</th>
                    <th>Message</th>
                    <th>Context</th>
                </tr>
            </thead>
            <tbody>
                {issue_rows}
            </tbody>
        </table>

        <footer>
            <p>Generated by <strong>SiteAble</strong></p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script>
        const chartData = {chart_data};
        const ctx = document.getElementById('severityChart');
        if (ctx && chartData.critical + chartData.major + chartData.minor > 0) {{
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: ['Critical', 'Major', 'Minor'],
                    datasets: [{{
                        data: [chartData.critical, chartData.major, chartData.minor],
                        backgroundColor: ['#dc3545', '#ffc107', '#17a2b8'],
                        borderWidth: 0,
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ legend: {{ position: 'bottom' }} }}
                }}
            }});
        }}
    </script>
</body>
</html>"""
