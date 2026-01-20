"""Enhanced website scanner: async crawler with robots.txt, sitemap discovery, concurrency limits.

This module provides `scan_site_enhanced(start_url, max_pages, concurrency)` which returns
a mapping of URL -> list of issues (as produced by ai.accessibility.analyzer.analyze_html).
"""

import asyncio
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai.accessibility.analyzer_plugin import analyze_html
from crawler.rate_limiter import RateLimiter

logger = logging.getLogger("siteable.crawler")


# Retry configuration
RETRY_EXCEPTIONS = (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError)


@retry(
    retry=retry_if_exception_type(RETRY_EXCEPTIONS),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _fetch_text_with_retry(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """Fetch URL text content with retry logic.

    Args:
        client: HTTP client
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response text or None if failed
    """
    try:
        resp = await client.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except httpx.HTTPStatusError as e:
        # Don't retry on 4xx errors (except 429)
        if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
            logger.debug(f"Client error fetching {url}: {e.response.status_code}")
            return None
        raise
    except Exception as e:
        logger.debug(f"Error fetching {url}: {e}")
        raise


async def _fetch_text(
    client: httpx.AsyncClient,
    url: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """Fetch URL text content with error handling.

    Args:
        client: HTTP client
        url: URL to fetch
        timeout: Request timeout in seconds

    Returns:
        Response text or None if failed
    """
    try:
        return await _fetch_text_with_retry(client, url, timeout)
    except Exception as e:
        logger.debug(f"Failed to fetch {url} after retries: {e}")
        return None


async def _fetch_robots(
    client: httpx.AsyncClient,
    base_url: str,
    ua: str = "SiteAble-Scanner",
) -> Tuple[List[str], float]:
    """Fetch and parse robots.txt.

    Args:
        client: HTTP client
        base_url: Base URL of the site
        ua: User-Agent string for matching rules

    Returns:
        Tuple of (disallow_paths, crawl_delay)
    """
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    text = await _fetch_text(client, robots_url)

    if not text:
        return [], 0.0

    # Parse robots.txt into user-agent groups
    groups = []
    current = {"user_agents": [], "disallow": [], "crawl_delay": None}

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        m_ua = re.match(r"User-agent:\s*(.*)", line, re.I)
        if m_ua:
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

    # Append last group
    if current["user_agents"] or current["disallow"] or current["crawl_delay"] is not None:
        groups.append(current)

    # Find best matching group
    chosen = None
    ua_lower = ua.lower()

    # Exact match
    for g in groups:
        for gu in g["user_agents"]:
            if gu and gu.lower() == ua_lower:
                chosen = g
                break
        if chosen:
            break

    # Substring match
    if not chosen:
        for g in groups:
            for gu in g["user_agents"]:
                if gu and gu != "*" and gu.lower() in ua_lower:
                    chosen = g
                    break
            if chosen:
                break

    # Wildcard match
    if not chosen:
        for g in groups:
            if "*" in g["user_agents"]:
                chosen = g
                break

    if not chosen:
        return [], 0.0

    disallows = chosen.get("disallow", [])
    crawl_delay = chosen.get("crawl_delay") or 0.0
    return disallows, float(crawl_delay)


async def _fetch_sitemap_urls(client: httpx.AsyncClient, base_url: str) -> List[str]:
    """Fetch URLs from sitemap.xml.

    Args:
        client: HTTP client
        base_url: Base URL of the site

    Returns:
        List of URLs from sitemap
    """
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    text = await _fetch_text(client, sitemap_url)

    if not text:
        return []

    soup = BeautifulSoup(text, "lxml")
    urls = [loc.get_text(strip=True) for loc in soup.find_all("loc")]
    return urls


def _same_domain(start_netloc: str, url: str) -> bool:
    """Check if URL is on the same domain."""
    try:
        return urlparse(url).netloc == start_netloc
    except Exception:
        return False


def _is_blocked(path: str, disallows: List[str]) -> bool:
    """Check if path is blocked by robots.txt rules."""
    if not disallows:
        return False
    return any(d and path.startswith(d) for d in disallows)


async def scan_site_enhanced(
    start_url: str,
    max_pages: int = 200,
    concurrency: int = 10,
    delay: float = 0.0,
    db_path: Optional[str] = None,
    exclude_analyzers: Optional[List[str]] = None,
    rate_limit: float = 0.0,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Crawl same-domain pages (polite) and analyze each page.

    Args:
        start_url: URL to start crawling from
        max_pages: Maximum number of pages to scan
        concurrency: Number of concurrent workers
        delay: Delay between requests (in addition to crawl-delay)
        db_path: Optional database path to persist results
        exclude_analyzers: List of analyzer names to skip
        rate_limit: Maximum requests per second (0 = unlimited)
        on_progress: Optional callback (pages_scanned, total_found, current_url)

    Returns:
        Dictionary mapping URLs to lists of issues
    """
    start_parsed = urlparse(start_url)
    start_netloc = start_parsed.netloc

    seen: Set[str] = set()
    to_visit: asyncio.Queue = asyncio.Queue()
    issues_map: Dict[str, List[Dict]] = {}
    total_found = 0

    # Initialize rate limiter
    rate_limiter = RateLimiter(rate_limit) if rate_limit > 0 else None

    headers = {
        "User-Agent": "SiteAble-Scanner/1.0 (+https://github.com/ghyathmoussa/SiteAble)",
    }

    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        # Fetch robots and sitemap
        logger.info(f"Fetching robots.txt and sitemap.xml for {start_netloc}")
        disallows, crawl_delay = await _fetch_robots(client, start_url)
        sitemap_urls = await _fetch_sitemap_urls(client, start_url)

        logger.info(f"Found {len(sitemap_urls)} URLs in sitemap, {len(disallows)} disallow rules")

        # Seed queue
        await to_visit.put(start_url)
        total_found = 1

        for s in sitemap_urls:
            if _same_domain(start_netloc, s) and s not in seen:
                await to_visit.put(s)
                total_found += 1

        sem = asyncio.Semaphore(concurrency)

        async def worker():
            nonlocal total_found

            while len(seen) < max_pages:
                try:
                    url = await asyncio.wait_for(to_visit.get(), timeout=2.0)
                except asyncio.TimeoutError:
                    break

                if url in seen:
                    to_visit.task_done()
                    continue

                # Check robots rules
                path = urlparse(url).path or "/"
                if _is_blocked(path, disallows):
                    seen.add(url)
                    issues_map[url] = []
                    logger.debug(f"Blocked by robots.txt: {url}")
                    to_visit.task_done()
                    continue

                async with sem:
                    # Apply rate limiting
                    if rate_limiter:
                        await rate_limiter.acquire()

                    start_time = time.monotonic()
                    text = await _fetch_text(client, url)
                    elapsed = time.monotonic() - start_time

                    seen.add(url)

                    if not text:
                        issues_map[url] = []
                        to_visit.task_done()
                        continue

                    # Analyze
                    try:
                        issues = analyze_html(text, exclude_analyzers=exclude_analyzers)
                        issues_map[url] = issues
                        logger.debug(f"Scanned {url}: {len(issues)} issues ({elapsed:.2f}s)")
                    except Exception as e:
                        logger.warning(f"Error analyzing {url}: {e}")
                        issues_map[url] = []

                    # Progress callback
                    if on_progress:
                        try:
                            on_progress(len(seen), total_found, url)
                        except Exception:
                            pass

                    # Persist if requested
                    if db_path:
                        try:
                            from core.storage import save_scan_result
                            save_scan_result(db_path, start_netloc, url, issues_map[url])
                        except Exception as e:
                            logger.warning(f"Failed to save scan result: {e}")

                    # Discover links
                    soup = BeautifulSoup(text, "lxml")
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        full = urljoin(url, href)

                        # Clean URL (remove fragments)
                        full = full.split("#")[0]

                        if not _same_domain(start_netloc, full):
                            continue
                        if full not in seen and full not in [str(u) for u in list(to_visit._queue)]:
                            await to_visit.put(full)
                            total_found += 1

                    # Respect crawl-delay
                    effective_delay = max(crawl_delay, delay)
                    if effective_delay > 0:
                        await asyncio.sleep(effective_delay)

                    to_visit.task_done()

        # Start workers
        logger.info(f"Starting {concurrency} workers, max {max_pages} pages")
        workers = [asyncio.create_task(worker()) for _ in range(concurrency)]
        await asyncio.gather(*workers)

        logger.info(f"Scan complete: {len(seen)} pages scanned")

    return issues_map


def scan_site(
    start_url: str,
    max_pages: int = 200,
    concurrency: int = 10,
    delay: float = 0.0,
    db_path: Optional[str] = None,
    exclude_analyzers: Optional[List[str]] = None,
    rate_limit: float = 0.0,
) -> Dict[str, List[Dict]]:
    """Synchronous wrapper for scan_site_enhanced.

    Args:
        start_url: URL to start crawling from
        max_pages: Maximum number of pages to scan
        concurrency: Number of concurrent workers
        delay: Delay between requests
        db_path: Optional database path to persist results
        exclude_analyzers: List of analyzer names to skip
        rate_limit: Maximum requests per second (0 = unlimited)

    Returns:
        Dictionary mapping URLs to lists of issues
    """
    return asyncio.run(
        scan_site_enhanced(
            start_url,
            max_pages=max_pages,
            concurrency=concurrency,
            delay=delay,
            db_path=db_path,
            exclude_analyzers=exclude_analyzers,
            rate_limit=rate_limit,
        )
    )
