"""Plugin analyzers for accessibility checks.

This module contains all built-in accessibility analyzers that implement
the Analyzer interface. Each analyzer checks for specific WCAG violations.
"""

import re
from typing import Any, Dict, List, Optional, Set

from bs4 import BeautifulSoup, Tag

from core.analyzer import Analyzer


# =============================================================================
# VALID ARIA ROLES (WCAG 4.1.2)
# =============================================================================

VALID_ARIA_ROLES: Set[str] = {
    # Landmark roles
    "banner", "complementary", "contentinfo", "form", "main", "navigation",
    "region", "search",
    # Document structure roles
    "article", "cell", "columnheader", "definition", "directory", "document",
    "feed", "figure", "group", "heading", "img", "list", "listitem", "math",
    "none", "note", "presentation", "row", "rowgroup", "rowheader", "separator",
    "table", "term", "toolbar", "tooltip",
    # Widget roles
    "alert", "alertdialog", "button", "checkbox", "combobox", "dialog",
    "gridcell", "link", "listbox", "log", "marquee", "menu", "menubar",
    "menuitem", "menuitemcheckbox", "menuitemradio", "option", "progressbar",
    "radio", "radiogroup", "scrollbar", "searchbox", "slider", "spinbutton",
    "status", "switch", "tab", "tablist", "tabpanel", "textbox", "timer",
    "tree", "treegrid", "treeitem",
    # Live region roles
    "alert", "log", "marquee", "status", "timer",
    # Window roles
    "alertdialog", "dialog",
    # Abstract roles (shouldn't be used directly but may appear)
    "command", "composite", "input", "landmark", "range", "roletype",
    "section", "sectionhead", "select", "structure", "widget", "window",
    # Application role
    "application",
    # Generic role
    "generic",
}

# Valid language codes (ISO 639-1)
VALID_LANG_CODES: Set[str] = {
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az",
    "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs", "ca", "ce",
    "ch", "co", "cr", "cs", "cu", "cv", "cy", "da", "de", "dv", "dz", "ee",
    "el", "en", "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr",
    "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr",
    "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik", "io", "is",
    "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn",
    "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln",
    "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms",
    "mt", "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv",
    "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu",
    "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk",
    "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta",
    "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw",
    "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh", "yi",
    "yo", "za", "zh", "zu",
}


# =============================================================================
# ORIGINAL ANALYZERS
# =============================================================================


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
            if alt is None or (isinstance(alt, str) and not alt.strip()):
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
            if ctype in ("hidden", "submit", "button", "image", "reset"):
                continue
            has_label = False
            id_ = control.get("id")
            if id_ and soup.find("label", attrs={"for": id_}):
                has_label = True
            if control.get("aria-label") or control.get("aria-labelledby"):
                has_label = True
            if control.get("title"):
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
                        "message": f"Heading level jumps from h{prev} to h{h} (may confuse screen readers).",
                        "context": f"sequence: {headings[:20]}",
                    })
                    break
                prev = h

        return issues


class ContrastAnalyzer(Analyzer):
    """Check for low contrast text in inline styles."""

    # WCAG contrast thresholds
    WCAG_AA_THRESHOLD = 4.5
    WCAG_AAA_THRESHOLD = 7.0

    # Named colors to hex mapping (common colors)
    NAMED_COLORS: Dict[str, str] = {
        "white": "#ffffff", "black": "#000000", "red": "#ff0000",
        "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
        "cyan": "#00ffff", "magenta": "#ff00ff", "gray": "#808080",
        "grey": "#808080", "silver": "#c0c0c0", "maroon": "#800000",
        "olive": "#808000", "lime": "#00ff00", "aqua": "#00ffff",
        "teal": "#008080", "navy": "#000080", "fuchsia": "#ff00ff",
        "purple": "#800080", "orange": "#ffa500", "pink": "#ffc0cb",
    }

    @property
    def name(self) -> str:
        return "contrast"

    @property
    def description(self) -> str:
        return "Detect low contrast in inline style colors"

    def _parse_color(self, value: str) -> Optional[str]:
        """Parse color value to hex format."""
        if not value:
            return None
        v = value.strip().lower()

        # Named color
        if v in self.NAMED_COLORS:
            return self.NAMED_COLORS[v]

        # Hex format
        m = re.match(r"#([0-9a-fA-F]{3,6})", v)
        if m:
            hexv = m.group(0)
            if len(m.group(1)) == 3:
                h = m.group(1)
                hexv = "#" + "".join([c * 2 for c in h])
            return hexv.lower()

        # RGB/RGBA format
        m = re.match(r"rgba?\(([^)]+)\)", v)
        if m:
            try:
                parts = [int(p.strip().split("%")[0]) for p in m.group(1).split(",")[:3]]
                return "#%02x%02x%02x" % tuple(parts)
            except Exception:
                pass

        # HSL format (basic support)
        m = re.match(r"hsla?\(([^)]+)\)", v)
        if m:
            try:
                parts = m.group(1).split(",")
                h = float(parts[0].strip()) / 360
                s = float(parts[1].strip().replace("%", "")) / 100
                lum = float(parts[2].strip().replace("%", "")) / 100
                # HSL to RGB conversion
                if s == 0:
                    r = g = b = int(lum * 255)
                else:
                    def hue_to_rgb(p, q, t):
                        if t < 0:
                            t += 1
                        if t > 1:
                            t -= 1
                        if t < 1/6:
                            return p + (q - p) * 6 * t
                        if t < 1/2:
                            return q
                        if t < 2/3:
                            return p + (q - p) * (2/3 - t) * 6
                        return p

                    q = lum * (1 + s) if lum < 0.5 else lum + s - lum * s
                    p = 2 * lum - q
                    r = int(hue_to_rgb(p, q, h + 1/3) * 255)
                    g = int(hue_to_rgb(p, q, h) * 255)
                    b = int(hue_to_rgb(p, q, h - 1/3) * 255)
                return "#%02x%02x%02x" % (r, g, b)
            except Exception:
                pass

        return None

    def _hex_to_rgb(self, hexstr: str) -> tuple:
        h = hexstr.lstrip("#")
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))

    def _relative_luminance(self, rgb: tuple) -> float:
        def chan(c):
            s = c / 255.0
            return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4

        r, g, b = rgb
        return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)

    def _contrast_ratio(self, hex1: str, hex2: str) -> float:
        l1 = self._relative_luminance(self._hex_to_rgb(hex1))
        l2 = self._relative_luminance(self._hex_to_rgb(hex2))
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        for el in soup.find_all(True):
            style = el.get("style")
            if not style:
                continue

            color = None
            bgcolor = None

            for part in style.split(";"):
                if ":" not in part:
                    continue
                k, v = part.split(":", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "color":
                    color = self._parse_color(v)
                if k in ("background-color", "background"):
                    bgcolor = self._parse_color(v)

            if color and bgcolor:
                try:
                    ratio = self._contrast_ratio(color, bgcolor)
                    if ratio < self.WCAG_AA_THRESHOLD:
                        issues.append({
                            "code": "LOW_CONTRAST",
                            "message": f"Low contrast ratio ({ratio:.2f}:1): text may be hard to read. "
                                      f"WCAG AA requires at least {self.WCAG_AA_THRESHOLD}:1.",
                            "context": str(el)[:200],
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
            # Check for accessible name
            text = a.get_text(strip=True)
            aria_label = a.get("aria-label", "").strip()
            aria_labelledby = a.get("aria-labelledby", "").strip()
            title = a.get("title", "").strip()

            has_accessible_name = bool(text or aria_label or aria_labelledby or title)

            if not has_accessible_name:
                # Check for images with alt
                imgs = a.find_all("img")
                if imgs:
                    # If there are images, alt_text analyzer handles this
                    continue
                issues.append({
                    "code": "LINK_NO_TEXT",
                    "message": "Link has no accessible name (no text and no labelled content).",
                    "context": str(a)[:200],
                })

        return issues


# =============================================================================
# NEW ANALYZERS - PHASE 2
# =============================================================================


class LanguageAnalyzer(Analyzer):
    """Check for missing or invalid lang attribute on HTML element."""

    @property
    def name(self) -> str:
        return "language"

    @property
    def description(self) -> str:
        return "Detect missing or invalid lang attribute on HTML element"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        html_tag = soup.find("html")
        if html_tag:
            lang = html_tag.get("lang", "").strip()
            if not lang:
                issues.append({
                    "code": "MISSING_LANG",
                    "message": "HTML element is missing the 'lang' attribute. "
                              "Screen readers use this to determine pronunciation.",
                    "context": str(html_tag)[:100],
                })
            else:
                # Validate language code (check primary subtag)
                primary_lang = lang.split("-")[0].lower()
                if primary_lang not in VALID_LANG_CODES:
                    issues.append({
                        "code": "INVALID_LANG",
                        "message": f"Invalid language code '{lang}'. "
                                  "Use a valid ISO 639-1 language code.",
                        "context": str(html_tag)[:100],
                    })

        return issues


class ButtonAnalyzer(Analyzer):
    """Check for buttons without accessible names."""

    @property
    def name(self) -> str:
        return "button"

    @property
    def description(self) -> str:
        return "Detect buttons without accessible names"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Check <button> elements
        for button in soup.find_all("button"):
            if not self._has_accessible_name(button):
                issues.append({
                    "code": "BUTTON_NO_TEXT",
                    "message": "Button element has no accessible name.",
                    "context": str(button)[:200],
                })

        # Check <input type="button"> and <input type="submit">
        for inp in soup.find_all("input", type=["button", "submit", "reset"]):
            value = inp.get("value", "").strip()
            aria_label = inp.get("aria-label", "").strip()
            aria_labelledby = inp.get("aria-labelledby", "").strip()
            title = inp.get("title", "").strip()

            if not any([value, aria_label, aria_labelledby, title]):
                # Submit buttons have default text, so only flag if explicitly empty
                if inp.get("type") != "submit" or inp.get("value") == "":
                    issues.append({
                        "code": "BUTTON_NO_TEXT",
                        "message": f"Input type='{inp.get('type')}' has no accessible name.",
                        "context": str(inp)[:200],
                    })

        # Check elements with role="button"
        for el in soup.find_all(attrs={"role": "button"}):
            if not self._has_accessible_name(el):
                issues.append({
                    "code": "BUTTON_NO_TEXT",
                    "message": "Element with role='button' has no accessible name.",
                    "context": str(el)[:200],
                })

        return issues

    def _has_accessible_name(self, element: Tag) -> bool:
        """Check if element has an accessible name."""
        # Text content
        text = element.get_text(strip=True)
        if text:
            return True

        # ARIA attributes
        if element.get("aria-label", "").strip():
            return True
        if element.get("aria-labelledby", "").strip():
            return True

        # Title attribute
        if element.get("title", "").strip():
            return True

        # Image with alt inside button
        img = element.find("img")
        if img and img.get("alt", "").strip():
            return True

        return False


class DocumentStructureAnalyzer(Analyzer):
    """Check for document structure issues."""

    @property
    def name(self) -> str:
        return "document_structure"

    @property
    def description(self) -> str:
        return "Detect document structure issues (missing landmarks, multiple h1, etc.)"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Check for missing <title>
        title = soup.find("title")
        if not title or not title.get_text(strip=True):
            issues.append({
                "code": "MISSING_TITLE",
                "message": "Page is missing a <title> element. "
                          "Titles help users identify pages in tabs and bookmarks.",
                "context": "<head>...</head>",
            })

        # Check for missing <main> landmark
        main = soup.find("main")
        main_role = soup.find(attrs={"role": "main"})
        if not main and not main_role:
            issues.append({
                "code": "MISSING_MAIN",
                "message": "Page is missing a <main> landmark. "
                          "Screen reader users use landmarks to navigate.",
                "context": "<body>...</body>",
            })

        # Check for multiple <h1> elements
        h1_elements = soup.find_all("h1")
        if len(h1_elements) > 1:
            issues.append({
                "code": "MULTIPLE_H1",
                "message": f"Page has {len(h1_elements)} <h1> elements. "
                          "Best practice is to have one h1 per page.",
                "context": ", ".join(str(h)[:50] for h in h1_elements[:3]),
            })

        # Check for missing h1
        if len(h1_elements) == 0:
            issues.append({
                "code": "MISSING_H1",
                "message": "Page is missing an <h1> element. "
                          "The h1 should describe the main content of the page.",
                "context": "<body>...</body>",
            })

        return issues


class TableAnalyzer(Analyzer):
    """Check for table accessibility issues."""

    @property
    def name(self) -> str:
        return "table"

    @property
    def description(self) -> str:
        return "Detect table accessibility issues (missing headers, captions)"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        for table in soup.find_all("table"):
            # Skip layout tables (tables with role="presentation" or role="none")
            role = table.get("role", "").lower()
            if role in ("presentation", "none"):
                continue

            # Check if it's likely a data table (has th or more than 1 row)
            rows = table.find_all("tr")
            if len(rows) <= 1:
                continue  # Probably not a data table

            # Check for headers
            headers = table.find_all("th")
            if not headers:
                issues.append({
                    "code": "TABLE_NO_HEADERS",
                    "message": "Data table is missing header cells (<th>). "
                              "Headers help screen reader users understand table structure.",
                    "context": str(table)[:200],
                })

            # Check for caption or accessible name
            caption = table.find("caption")
            aria_label = table.get("aria-label", "").strip()
            aria_labelledby = table.get("aria-labelledby", "").strip()
            summary = table.get("summary", "").strip()  # Deprecated but still valid

            if not any([caption, aria_label, aria_labelledby, summary]):
                issues.append({
                    "code": "TABLE_NO_CAPTION",
                    "message": "Data table is missing a caption or accessible name. "
                              "Use <caption> or aria-label to describe the table.",
                    "context": str(table)[:200],
                })

            # Check for scope on headers
            for th in headers:
                scope = th.get("scope", "").strip()
                if not scope and len(headers) > 1:
                    # Only flag if table has multiple headers and scope is missing
                    issues.append({
                        "code": "TABLE_MISSING_SCOPE",
                        "message": "Table header is missing 'scope' attribute. "
                                  "Use scope='col' or scope='row' to clarify header relationships.",
                        "context": str(th)[:200],
                    })
                    break  # Only report once per table

        return issues


class ARIAAnalyzer(Analyzer):
    """Check for ARIA usage issues."""

    @property
    def name(self) -> str:
        return "aria"

    @property
    def description(self) -> str:
        return "Detect ARIA usage issues (invalid roles, aria-hidden on focusable)"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Check for invalid ARIA roles
        for el in soup.find_all(attrs={"role": True}):
            role = el.get("role", "").strip().lower()
            if role and role not in VALID_ARIA_ROLES:
                issues.append({
                    "code": "INVALID_ARIA_ROLE",
                    "message": f"Invalid ARIA role '{role}'. Use a valid WAI-ARIA role.",
                    "context": str(el)[:200],
                })

        # Check for aria-hidden="true" on focusable elements
        for el in soup.find_all(attrs={"aria-hidden": "true"}):
            if self._is_focusable(el):
                issues.append({
                    "code": "ARIA_HIDDEN_FOCUSABLE",
                    "message": "Element with aria-hidden='true' is focusable. "
                              "This creates a confusing experience for keyboard users.",
                    "context": str(el)[:200],
                })

            # Check for focusable descendants
            for child in el.find_all(True):
                if self._is_focusable(child):
                    issues.append({
                        "code": "ARIA_HIDDEN_FOCUSABLE",
                        "message": "Element with aria-hidden='true' contains focusable content. "
                                  "Keyboard users can focus invisible elements.",
                        "context": str(el)[:200],
                    })
                    break  # Only report once per aria-hidden element

        return issues

    def _is_focusable(self, element: Tag) -> bool:
        """Check if element is focusable."""
        # Inherently focusable elements
        focusable_tags = {"a", "button", "input", "select", "textarea", "iframe"}
        if element.name in focusable_tags:
            # Links need href to be focusable
            if element.name == "a" and not element.get("href"):
                return False
            # Disabled elements are not focusable
            if element.get("disabled") is not None:
                return False
            return True

        # Elements with tabindex
        tabindex = element.get("tabindex")
        if tabindex is not None:
            try:
                return int(tabindex) >= 0
            except ValueError:
                pass

        # Elements with contenteditable
        if element.get("contenteditable") == "true":
            return True

        return False


class SkipLinkAnalyzer(Analyzer):
    """Check for skip navigation links."""

    @property
    def name(self) -> str:
        return "skip_link"

    @property
    def description(self) -> str:
        return "Detect missing or broken skip navigation links"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Look for skip links (typically first links in the document)
        body = soup.find("body")
        if not body:
            return issues

        # Common skip link patterns
        skip_link_patterns = [
            r"skip.*main",
            r"skip.*content",
            r"skip.*nav",
            r"jump.*content",
            r"jump.*main",
        ]

        # Find all links
        links = body.find_all("a", href=True)
        skip_link_found = False

        for link in links[:10]:  # Check first 10 links
            href = link.get("href", "")
            text = link.get_text(strip=True).lower()
            aria_label = link.get("aria-label", "").lower()

            # Check if this looks like a skip link
            combined_text = f"{text} {aria_label}"
            is_skip_link = any(
                re.search(pattern, combined_text, re.I)
                for pattern in skip_link_patterns
            )

            if is_skip_link or href.startswith("#main") or href.startswith("#content"):
                skip_link_found = True

                # Check if target exists
                if href.startswith("#"):
                    target_id = href[1:]
                    target = soup.find(id=target_id)
                    if not target:
                        issues.append({
                            "code": "BROKEN_SKIP_LINK",
                            "message": f"Skip link target '#{target_id}' does not exist.",
                            "context": str(link)[:200],
                        })
                break

        # Only flag missing skip link if page has navigation
        nav = body.find("nav") or body.find(attrs={"role": "navigation"})
        if nav and not skip_link_found:
            # Check if there's significant content before main
            main = body.find("main") or body.find(attrs={"role": "main"})
            if main:
                issues.append({
                    "code": "NO_SKIP_LINK",
                    "message": "Page has navigation but no skip link. "
                              "Keyboard users must tab through all navigation.",
                    "context": "<body><nav>...</nav></body>",
                })

        return issues


class MediaAnalyzer(Analyzer):
    """Check for media accessibility issues."""

    @property
    def name(self) -> str:
        return "media"

    @property
    def description(self) -> str:
        return "Detect media accessibility issues (missing captions, transcripts)"

    def analyze(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, "lxml")
        issues = []

        # Check video elements
        for video in soup.find_all("video"):
            # Check for captions track
            tracks = video.find_all("track")
            has_captions = any(
                track.get("kind") in ("captions", "subtitles")
                for track in tracks
            )

            if not has_captions:
                issues.append({
                    "code": "VIDEO_NO_CAPTIONS",
                    "message": "Video element is missing captions. "
                              "Add <track kind='captions'> for deaf/hard-of-hearing users.",
                    "context": str(video)[:200],
                })

            # Check for autoplay without controls
            if video.get("autoplay") is not None:
                if video.get("muted") is None and video.get("controls") is None:
                    issues.append({
                        "code": "AUTOPLAY_NO_CONTROLS",
                        "message": "Video autoplays with sound but has no controls. "
                                  "Users cannot pause or mute the video.",
                        "context": str(video)[:200],
                    })

        # Check audio elements
        for audio in soup.find_all("audio"):
            # Note: We can't easily check for transcripts as they're usually in
            # surrounding content. Flag for manual review if no aria-describedby
            if not audio.get("aria-describedby"):
                pass  # Could add a warning, but might be too noisy

            # Check for autoplay without controls
            if audio.get("autoplay") is not None:
                if audio.get("muted") is None and audio.get("controls") is None:
                    issues.append({
                        "code": "AUTOPLAY_NO_CONTROLS",
                        "message": "Audio autoplays with sound but has no controls. "
                                  "Users cannot pause or mute the audio.",
                        "context": str(audio)[:200],
                    })

        return issues
