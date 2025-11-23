"""Enhanced website scanner: async crawler with robots.txt, sitemap discovery, concurrency limits.

This module provides `scan_site_enhanced(start_url, max_pages, concurrency)` which returns
a mapping of URL -> list of issues (as produced by ai.accessibility.analyzer.analyze_html).
"""
from typing import Dict, List, Set, Optional, Tuple
from urllib.parse import urljoin, urlparse
import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from ai.accessibility.analyzer_plugin import analyze_html


async def _fetch_text(client: httpx.AsyncClient, url: str, timeout: float = 10.0) -> Optional[str]:
    try:
        resp = await client.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


async def _fetch_robots(client: httpx.AsyncClient, base_url: str, ua: str = "SiteAble-Scanner") -> Tuple[List[str], float]:
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    text = await _fetch_text(client, robots_url)
    if not text:
        return [], 0.0

    # Parse robots.txt into user-agent groups. We respect the first matching group for our UA,
    # otherwise fall back to '*' directives. We collect Disallow paths and Crawl-delay.
    groups = []
    current = {"user_agents": [], "disallow": [], "crawl_delay": None}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        m_ua = re.match(r"User-agent:\s*(.*)", line, re.I)
        if m_ua:
            # start new group if current has directives
            if current["user_agents"] or current["disallow"] or current["crawl_delay"] is not None:
                groups.append(current)
                current = {"user_agents": [], "disallow": [], "crawl_delay": None}
            current["user_agents"].append(m_ua.group(1).strip())
            continue
        m_dis = re.match(r"Disallow:\s*(.*)", line, re.I)
        if m_dis:
            current["disallow"].append(m_dis.group(1).strip())
            continue
        m_cd = re.match(r"Crawl-delay:\s*(.*)", line, re.I)
        if m_cd:
            try:
                current["crawl_delay"] = float(m_cd.group(1).strip())
            except Exception:
                pass
            continue

    # append last
    if current["user_agents"] or current["disallow"] or current["crawl_delay"] is not None:
        groups.append(current)

    # find best matching group: exact UA, substring match, then '*'
    chosen = None
    ua_lower = ua.lower()
    for g in groups:
        for gu in g["user_agents"]:
            if gu and gu.lower() == ua_lower:
                chosen = g
                break
        if chosen:
            break
    if not chosen:
        # substring match
        for g in groups:
            for gu in g["user_agents"]:
                if gu and gu != '*' and gu.lower() in ua_lower:
                    chosen = g
                    break
            if chosen:
                break
    if not chosen:
        for g in groups:
            if '*' in [u for u in g["user_agents"]]:
                chosen = g
                break

    if not chosen:
        return [], 0.0

    disallows = chosen.get("disallow", [])
    crawl_delay = chosen.get("crawl_delay") or 0.0
    return disallows, float(crawl_delay)


async def _fetch_sitemap_urls(client: httpx.AsyncClient, base_url: str) -> List[str]:
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    text = await _fetch_text(client, sitemap_url)
    if not text:
        return []
    soup = BeautifulSoup(text, 'lxml')
    urls = [loc.get_text(strip=True) for loc in soup.find_all('loc')]
    return urls


def _same_domain(start_netloc: str, url: str) -> bool:
    try:
        return urlparse(url).netloc == start_netloc
    except Exception:
        return False


async def scan_site_enhanced(start_url: str, max_pages: int = 200, concurrency: int = 10, delay: float = 0.0, db_path: str = None, exclude_analyzers: List[str] = None) -> Dict[str, List[Dict]]:
    """Crawl same-domain pages (polite) and analyze each page.

    - Respects basic robots `Disallow` rules (path prefixes) if robots.txt is present.
    - Discovers `sitemap.xml` and seeds URLs from there.
    - Uses an async queue with a concurrency limit.
    - exclude_analyzers: list of analyzer names to skip (e.g., ['contrast', 'alt_text'])
    """
    start_parsed = urlparse(start_url)
    start_netloc = start_parsed.netloc

    limits: Set[str] = set()
    seen: Set[str] = set()
    to_visit: asyncio.Queue = asyncio.Queue()
    issues_map: Dict[str, List[Dict]] = {}

    async with httpx.AsyncClient(follow_redirects=True, headers={"User-Agent": "SiteAble-Scanner/1.0"}) as client:
        # fetch robots and sitemap(s)
        disallows, crawl_delay = await _fetch_robots(client, start_url)
        sitemap_urls = await _fetch_sitemap_urls(client, start_url)

        # seed queue
        await to_visit.put(start_url)
        for s in sitemap_urls:
            if _same_domain(start_netloc, s):
                await to_visit.put(s)

        sem = asyncio.Semaphore(concurrency)

        async def worker():
            while len(seen) < max_pages:
                try:
                    url = await asyncio.wait_for(to_visit.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    break
                if url in seen:
                    to_visit.task_done()
                    continue
                # check robots
                path = urlparse(url).path or '/'
                blocked = any(d and path.startswith(d) for d in disallows)
                if blocked:
                    seen.add(url)
                    issues_map[url] = []
                    to_visit.task_done()
                    continue

                async with sem:
                    text = await _fetch_text(client, url)
                    seen.add(url)
                    if not text:
                        issues_map[url] = []
                        to_visit.task_done()
                        continue
                    # analyze
                    try:
                        issues = analyze_html(text, exclude_analyzers=exclude_analyzers)
                        issues_map[url] = issues
                    except Exception:
                        issues_map[url] = []

                    # persist if requested
                    if db_path:
                        try:
                            from core.storage import save_scan_result

                            save_scan_result(db_path, start_netloc, url, issues_map[url])
                        except Exception:
                            pass

                    # discover links
                    soup = BeautifulSoup(text, 'lxml')
                    for a in soup.find_all('a', href=True):
                        href = a['href']
                        full = urljoin(url, href)
                        if not _same_domain(start_netloc, full):
                            continue
                        if full not in seen:
                            await to_visit.put(full)

                    # obey crawl-delay if specified for the site, otherwise use configured delay
                    await asyncio.sleep(crawl_delay if crawl_delay and crawl_delay > 0 else delay)
                    to_visit.task_done()

        # start workers
        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await asyncio.gather(*workers)

    return issues_map


def scan_site(start_url: str, max_pages: int = 200, concurrency: int = 10, delay: float = 0.0, db_path: str = None, exclude_analyzers: List[str] = None) -> Dict[str, List[Dict]]:
    """Synchronous wrapper for convenience."""
    return asyncio.run(scan_site_enhanced(start_url, max_pages=max_pages, concurrency=concurrency, delay=delay, db_path=db_path, exclude_analyzers=exclude_analyzers))
