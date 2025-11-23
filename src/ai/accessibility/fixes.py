from typing import List, Dict, Tuple, Optional
from bs4 import BeautifulSoup
import re


def _parse_color(value: str) -> Optional[str]:
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
        parts = [int(p.strip().split('%')[0]) for p in m.group(1).split(',')[:3]]
        return '#%02x%02x%02x' % tuple(parts)
    return None


def _hex_to_rgb(hexstr: str) -> Tuple[int, int, int]:
    h = hexstr.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    def chan(c):
        s = c / 255.0
        return s/12.92 if s <= 0.03928 else ((s+0.055)/1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b)


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _relative_luminance(_hex_to_rgb(hex1))
    l2 = _relative_luminance(_hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _recommend_foreground(bg_hex: str) -> str:
    # choose black or white depending on contrast
    black = '#000000'
    white = '#ffffff'
    if _contrast_ratio(black, bg_hex) >= 4.5:
        return black
    return white


def apply_fixes(html: str, issues: List[Dict], ai_alt_map: Dict[str, str] = None) -> Tuple[str, List[Dict]]:
    """Apply basic fixes to the HTML string.

    - Add alt attributes to images flagged as missing (uses ai_alt_map by `src` or fallback to filename)
    - For low contrast, replace inline `color` with recommended foreground color
    Returns (fixed_html, applied_fixes)
    """
    ai_alt_map = ai_alt_map or {}
    soup = BeautifulSoup(html, 'lxml')
    applied = []

    # Fix missing alt
    for img in soup.find_all('img'):
        alt = img.get('alt')
        if not alt or not alt.strip():
            src = img.get('src') or ''
            suggestion = ai_alt_map.get(src) or ai_alt_map.get(img.get('id') or '')
            if not suggestion:
                # derive from filename
                filename = src.split('/')[-1] if '/' in src else src
                suggestion = filename or 'image'
            img['alt'] = suggestion
            applied.append({'code': 'IMG_MISSING_ALT', 'fix': f"set alt='{suggestion}'", 'context': str(img)[:200]})

    # Fix low contrast by adjusting color in inline style
    for el in soup.find_all(True):
        style = el.get('style')
        if not style:
            continue
        parts = [p for p in style.split(';') if p.strip()]
        new_parts = parts.copy()
        color = None
        bgcolor = None
        for i, part in enumerate(parts):
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
                ratio = _contrast_ratio(color, bgcolor)
                if ratio < 4.5:
                    new_fg = _recommend_foreground(bgcolor)
                    # replace color part
                    replaced = False
                    for i, part in enumerate(new_parts):
                        if ':' not in part:
                            continue
                        k, v = part.split(':', 1)
                        if k.strip().lower() == 'color':
                            new_parts[i] = f"color: {new_fg}"
                            replaced = True
                            break
                    if not replaced:
                        new_parts.append(f"color: {new_fg}")
                    el['style'] = '; '.join(new_parts)
                    applied.append({'code': 'LOW_CONTRAST', 'fix': f"set color={new_fg}", 'context': str(el)[:200]})
            except Exception:
                pass

    return str(soup), applied
