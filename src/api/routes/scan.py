"""API routes for triggering and managing scans."""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, HttpUrl

# In-memory scan storage (in production, use Redis or database)
_scans: Dict[str, dict] = {}

router = APIRouter()


class ScanRequest(BaseModel):
    """Request body for starting a new scan."""

    url: HttpUrl
    scan_site: bool = False
    max_pages: int = 100
    concurrency: int = 5
    exclude_analyzers: Optional[List[str]] = None


class ScanResponse(BaseModel):
    """Response for scan creation."""

    scan_id: str
    status: str
    message: str


class ScanStatus(BaseModel):
    """Status of a scan."""

    scan_id: str
    status: str  # pending, running, completed, failed
    url: str
    pages_scanned: int = 0
    total_issues: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    results: Optional[dict] = None
    error: Optional[str] = None


async def _run_scan(scan_id: str, request: ScanRequest) -> None:
    """Background task to run a scan."""
    from ai.accessibility.analyzer import analyze_html
    from ai.accessibility.utils import fetch_url
    from core.severity import enrich_issues, summarize_by_severity
    from crawler.crawler_scanner import scan_site

    _scans[scan_id]["status"] = "running"
    _scans[scan_id]["started_at"] = datetime.now().isoformat()

    try:
        url = str(request.url)

        if request.scan_site:
            # Site scan
            def on_progress(scanned: int, total: int, current_url: str):
                _scans[scan_id]["pages_scanned"] = scanned

            issues_map = scan_site(
                url,
                max_pages=request.max_pages,
                concurrency=request.concurrency,
                exclude_analyzers=request.exclude_analyzers,
            )

            # Process results
            all_issues = []
            pages_results = {}

            for page_url, issues in issues_map.items():
                enriched = enrich_issues(issues)
                all_issues.extend(enriched)
                pages_results[page_url] = {
                    "issues": enriched,
                    "issue_count": len(enriched),
                }

            _scans[scan_id]["results"] = {
                "pages": pages_results,
                "total_pages": len(pages_results),
                "total_issues": len(all_issues),
                "severity_summary": summarize_by_severity(all_issues),
            }
            _scans[scan_id]["pages_scanned"] = len(pages_results)
            _scans[scan_id]["total_issues"] = len(all_issues)

        else:
            # Single page scan
            html = fetch_url(url)
            issues = analyze_html(html, exclude_analyzers=request.exclude_analyzers)
            enriched = enrich_issues(issues)

            _scans[scan_id]["results"] = {
                "url": url,
                "issues": enriched,
                "total_issues": len(enriched),
                "severity_summary": summarize_by_severity(enriched),
            }
            _scans[scan_id]["pages_scanned"] = 1
            _scans[scan_id]["total_issues"] = len(enriched)

        _scans[scan_id]["status"] = "completed"
        _scans[scan_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        _scans[scan_id]["status"] = "failed"
        _scans[scan_id]["error"] = str(e)
        _scans[scan_id]["completed_at"] = datetime.now().isoformat()


@router.post("/scan", response_model=ScanResponse)
async def create_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Start a new accessibility scan.

    The scan runs in the background. Use the returned scan_id to check status.
    """
    scan_id = str(uuid.uuid4())

    _scans[scan_id] = {
        "scan_id": scan_id,
        "status": "pending",
        "url": str(request.url),
        "pages_scanned": 0,
        "total_issues": 0,
        "started_at": None,
        "completed_at": None,
        "results": None,
        "error": None,
    }

    # Run scan in background
    background_tasks.add_task(_run_scan, scan_id, request)

    return ScanResponse(
        scan_id=scan_id,
        status="pending",
        message="Scan started. Use GET /api/scan/{scan_id} to check status.",
    )


@router.get("/scan/{scan_id}", response_model=ScanStatus)
async def get_scan_status(scan_id: str):
    """Get the status and results of a scan."""
    if scan_id not in _scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanStatus(**_scans[scan_id])


@router.get("/scans", response_model=List[ScanStatus])
async def list_scans(limit: int = 10):
    """List recent scans."""
    scans = list(_scans.values())
    # Sort by started_at descending
    scans.sort(key=lambda x: x.get("started_at") or "", reverse=True)
    return [ScanStatus(**s) for s in scans[:limit]]


@router.delete("/scan/{scan_id}")
async def delete_scan(scan_id: str):
    """Delete a scan and its results."""
    if scan_id not in _scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    del _scans[scan_id]
    return {"message": "Scan deleted"}
