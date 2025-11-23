import asyncio
from httpx import AsyncClient, Request, Response
from httpx._transports.mock import MockTransport

from crawler.crawler_scanner import scan_site_enhanced


def make_mock_transport():
    # Prepare simple site with robots, sitemap and two pages
    robots = """
User-agent: *
Disallow: /private
Crawl-delay: 0
"""
    sitemap = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>http://test.local/</loc></url>
      <url><loc>http://test.local/about</loc></url>
    </urlset>
    """
    page_index = "<html><body><img src='logo.png'/><a href='/about'>About</a></body></html>"
    page_about = "<html><body><h1>About</h1><p style='color:#777777;background-color:#ffffff'>text</p></body></html>"

    async def handler(request: Request):
        url = str(request.url)
        if url.endswith('/robots.txt'):
            return Response(200, text=robots)
        if url.endswith('/sitemap.xml'):
            return Response(200, text=sitemap)
        if url.endswith('/'):
            return Response(200, text=page_index)
        if url.endswith('/about'):
            return Response(200, text=page_about)
        return Response(404, text='')

    return MockTransport(handler)


def test_scan_site_enhanced_basic():
    transport = make_mock_transport()
    async def run():
        async with AsyncClient(transport=transport, base_url='http://test.local') as client:
            # monkeypatch client usage inside httpx AsyncClient by passing custom client via patching httpx.AsyncClient
            # Instead of patching module-level client we call scan_site_enhanced via a small wrapper that uses the real network.
            # To use the MockTransport we temporarily replace httpx.AsyncClient in the crawler module.
            import crawler.crawler_scanner as cs
            original_async_client = cs.httpx.AsyncClient

            class DummyAsyncClient:
                def __init__(self, *args, **kwargs):
                    self._client = client
                async def __aenter__(self):
                    return self._client
                async def __aexit__(self, exc_type, exc, tb):
                    return False

            cs.httpx.AsyncClient = DummyAsyncClient
            try:
                result = await scan_site_enhanced('http://test.local/', max_pages=10, concurrency=2, delay=0.0)
            finally:
                cs.httpx.AsyncClient = original_async_client
            return result

    res = asyncio.run(run())
    assert 'http://test.local/' in res
    assert 'http://test.local/about' in res
    # index should have IMG_MISSING_ALT
    assert any(i.get('code') == 'IMG_MISSING_ALT' for i in res['http://test.local/'])
