import os
import re
from typing import List, Dict, Any

from bs4 import BeautifulSoup

try:
    import openai
except Exception:
    openai = None


def analyze_html(html: str, exclude_analyzers: List[str] = None) -> List[Dict[str, Any]]:
    """Analyze HTML using plugin-based analyzers.
    
    Falls back to the old implementation if analyzers are not available.
    exclude_analyzers: list of analyzer names to skip
    """
    try:
        from .analyzer_plugin import analyze_html as plugin_analyze
        return plugin_analyze(html, exclude_analyzers=exclude_analyzers)
    except Exception:
        # fallback to legacy implementation
        soup = BeautifulSoup(html, "lxml")
        issues: List[Dict[str, Any]] = []

        # Images must have alt
        for img in soup.find_all("img"):
            alt = img.get("alt")
            if not alt or not alt.strip():
                issues.append({
                    "code": "IMG_MISSING_ALT",
                    "message": "Image element missing descriptive alt text.",
                    "context": str(img)[:200],
                })

        # Links should have text or image with alt
        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            if not text:
                imgs = a.find_all("img")
                if imgs:
                    first_alt = imgs[0].get("alt") or ""
                    if not first_alt.strip():
                        issues.append({
                            "code": "LINK_IMG_MISSING_ALT",
                            "message": "Link contains image(s) without alt text.",
                            "context": str(a)[:200],
                        })
                else:
                    issues.append({
                        "code": "LINK_NO_TEXT",
                        "message": "Link has no accessible name (no text and no labelled content).",
                        "context": str(a)[:200],
                    })

        # Heading order (simple check for jumps)
        headings = [int(tag.name[1]) for tag in soup.find_all(re.compile(r"^h[1-6]$"))]
        if headings:
            prev = headings[0]
            for h in headings[1:]:
                if h - prev > 1:
                    issues.append({
                        "code": "HEADING_ORDER",
                        "message": "Heading level jumps (may confuse screen readers).",
                        "context": f"sequence: {headings[:20]}",
                    })
                    break
                prev = h

        # Form controls should have labels or aria-labels
        for control in soup.find_all(["input", "textarea", "select"]):
            ctype = (control.get("type") or "").lower()
            if ctype in ("hidden", "submit", "button", "image"):
                continue
            has_label = False
            id_ = control.get("id")
            if id_ and soup.find("label", attrs={"for": id_}):
                has_label = True
            if control.get("aria-label") or control.get("aria-labelledby"):
                has_label = True
            parent = control.find_parent("label")
            if parent is not None:
                has_label = True
            if not has_label:
                issues.append({
                    "code": "FORM_CONTROL_NO_LABEL",
                    "message": "Form control is missing an accessible label.",
                    "context": str(control)[:200],
                })

        return issues


def summarize_issues(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for it in issues:
        counts[it.get("code", "UNKNOWN")] = counts.get(it.get("code", "UNKNOWN"), 0) + 1
    return counts


def suggest_fixes_with_ai(html: str, issues: List[Dict[str, Any]], model: str = "gpt-3.5-turbo") -> str:
    """If OpenAI credentials are available, return suggested fixes as text.

    This is optional; function will return a helpful message if OpenAI is not available.
    """
    if openai is None:
        return "AI suggestions not available: `openai` package is not installed."

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "AI suggestions not available: set OPENAI_API_KEY environment variable."

    openai.api_key = api_key
    prompt = (
        "You are an accessibility expert. Given the site HTML and list of issues, provide concise, actionable fixes for each issue.\n\n"
        f"Found issues: {issues}\n\nHTML snippet (truncated):\n" + html[:4000]
    )

    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.2,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"AI suggestion failed: {e}"
