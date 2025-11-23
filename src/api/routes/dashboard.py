from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRouter
from typing import List
from pydantic import BaseModel

from core.storage import get_scan_results

router = APIRouter(title="SiteAble Dashboard")


class ScanEntry(BaseModel):
    url: str
    issues: List[dict]
    ts: int


@router.get("/dashboard/{site}")
def dashboard(site: str):
    try:
        rows = get_scan_results('data/siteable_scans.db', site=site)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"site": site, "results": rows}
