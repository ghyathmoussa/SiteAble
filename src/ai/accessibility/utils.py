import requests

def fetch_url(url: str, timeout: int = 10) -> str:
    """Fetch a URL and return its text. Raises requests.HTTPError on bad status."""
    headers = {"User-Agent": "SiteAble-Accessibility-Checker/1.0"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text
