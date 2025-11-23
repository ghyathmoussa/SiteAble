import sqlite3
import json
from typing import List, Dict, Optional
from pathlib import Path
import time


def init_db(db_path: str) -> None:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site TEXT NOT NULL,
            url TEXT NOT NULL,
            issues_json TEXT,
            ts INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def save_scan_result(db_path: str, site: str, url: str, issues: List[Dict]) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO scans (site, url, issues_json, ts) VALUES (?, ?, ?, ?)",
        (site, url, json.dumps(issues), int(time.time())),
    )
    conn.commit()
    conn.close()


def get_scan_results(db_path: str, site: Optional[str] = None) -> List[Dict]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if site:
        cur.execute("SELECT url, issues_json, ts FROM scans WHERE site = ? ORDER BY ts DESC", (site,))
    else:
        cur.execute("SELECT site, url, issues_json, ts FROM scans ORDER BY ts DESC")
    rows = cur.fetchall()
    conn.close()
    out = []
    for r in rows:
        if site:
            url, issues_json, ts = r
            out.append({"url": url, "issues": json.loads(issues_json), "ts": ts})
        else:
            site_, url, issues_json, ts = r
            out.append({"site": site_, "url": url, "issues": json.loads(issues_json), "ts": ts})
    return out
