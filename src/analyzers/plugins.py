"""Plugin analyzers for accessibility checks."""
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup

from core.analyzer import Analyzer


class AltTextAnalyzer(Analyzer):
    """Check for missing alt text on images and images in links."""

    @property
    def name(self) -> str:
        return "alt_text"

    @property
    def description(self) -> str:
        return "Detect missing alt text on images and linked images"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Images must have alt
        for img in soup.find_all("img"):
            alt = img.get("alt")
            if not alt or not alt.strip():
                issues.append({
                    "code": "IMG_MISSING_ALT",
                    "message": "Image element missing descriptive alt text.",
                    "context": str(img)[:200],
                })

        # Links with images should have alt text
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

        return issues


class FormLabelAnalyzer(Analyzer):
    """Check for missing labels on form controls."""

    @property
    def name(self) -> str:
        return "form_labels"

    @property
    def description(self) -> str:
        return "Detect form controls without accessible labels"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

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


class HeadingOrderAnalyzer(Analyzer):
    """Check for heading level jumps."""

    @property
    def name(self) -> str:
        return "heading_order"

    @property
    def description(self) -> str:
        return "Detect heading level jumps that confuse screen readers"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

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

        return issues


class ContrastAnalyzer(Analyzer):
    """Check for low contrast text in inline styles."""

    @property
    def name(self) -> str:
        return "contrast"

    @property
    def description(self) -> str:
        return "Detect low contrast in inline style colors"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        def _parse_color(value: str):
            if not value:
                return None
            v = value.strip()
            m = re.match(r"#([0-9a-fA-F]{3,6})", v)
            if m:
                hexv = m.group(0)
                if len(m.group(1)) == 3:
                    h = m.group(1)
                    hexv = "#" + ''.join([c*2 for c in h])
                return hexv.lower()
            m = re.match(r"rgba?\(([^)]+)\)", v)
            if m:
                try:
                    parts = [int(p.strip().split('%')[0]) for p in m.group(1).split(',')[:3]]
                    return '#%02x%02x%02x' % tuple(parts)
                except Exception:
                    pass
            return None

        def hex_to_rgb(hexstr: str):
            h = hexstr.lstrip('#')
            return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

        def relative_luminance(rgb):
            def chan(c):
                s = c / 255.0
                return s/12.92 if s <= 0.03928 else ((s+0.055)/1.055) ** 2.4
            r, g, b = rgb
            return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)

        def contrast_ratio(hex1: str, hex2: str) -> float:
            l1 = relative_luminance(hex_to_rgb(hex1))
            l2 = relative_luminance(hex_to_rgb(hex2))
            lighter = max(l1, l2)
            darker = min(l1, l2)
            return (lighter + 0.05) / (darker + 0.05)

        for el in soup.find_all(True):
            style = el.get('style')
            if not style:
                continue
            color = None
            bgcolor = None
            for part in style.split(';'):
                if ':' not in part:
                    continue
                k, v = part.split(':', 1)
                k = k.strip().lower()
                v = v.strip()
                if k == 'color':
                    color = _parse_color(v)
                if k in ('background-color', 'background'):
                    bgcolor = _parse_color(v)
            if color and bgcolor:
                try:
                    ratio = contrast_ratio(color, bgcolor)
                    if ratio < 4.5:
                        issues.append({
                            'code': 'LOW_CONTRAST',
                            'message': f'Low contrast ratio ({ratio:.2f}): text may be hard to read.',
                            'context': str(el)[:200],
                        })
                except Exception:
                    pass

        return issues


class LinkTextAnalyzer(Analyzer):
    """Check for links without accessible names."""

    @property
    def name(self) -> str:
        return "link_text"

    @property
    def description(self) -> str:
        return "Detect links missing accessible text"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        for a in soup.find_all("a"):
            text = a.get_text(strip=True)
            if not text:
                imgs = a.find_all("img")
                if not imgs:
                    issues.append({
                        "code": "LINK_NO_TEXT",
                        "message": "Link has no accessible name (no text and no labelled content).",
                        "context": str(a)[:200],
                    })

        return issues
