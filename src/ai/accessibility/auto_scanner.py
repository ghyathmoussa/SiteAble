from typing import Dict, List
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import time

from .analyzer import analyze_html


def _same_domain(start_netloc: str, url: str) -> bool:
    try:
        return urlparse(url).netloc == start_netloc
    except Exception:
        return False


def scan_site(start_url: str, max_pages: int = 20, delay: float = 0.1) -> Dict[str, List[Dict]]:
    """Basic domain-limited crawler that scans pages and returns issues per URL.

    This is intentionally simple and safe for small websites.
    """
    headers = {"User-Agent": "SiteAble-Accessibility-Scanner/1.0"}
    to_visit = [start_url]
    seen = set()
    issues_map = {}
    start_netloc = urlparse(start_url).netloc

    while to_visit and len(seen) < max_pages:
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            html = resp.text
        except Exception:
            continue

        issues = analyze_html(html)
        issues_map[url] = issues

        soup = BeautifulSoup(html, 'lxml')
        for a in soup.find_all('a', href=True):
            href = a['href']
            full = urljoin(url, href)
            if _same_domain(start_netloc, full) and full not in seen and full not in to_visit:
                to_visit.append(full)

        time.sleep(delay)

    return issues_map
