from ai.accessibility.fixes import apply_fixes


def test_apply_alt_fix():
    html = '<html><body><img src="/images/logo.png"/></body></html>'
    fixed, applied = apply_fixes(html, [{'code': 'IMG_MISSING_ALT'}])
    assert 'alt=' in fixed
    assert any(a['code'] == 'IMG_MISSING_ALT' for a in applied)


def test_apply_contrast_fix():
    html = '<html><body><p style="color: #777777; background-color: #ffffff">text</p></body></html>'
    fixed, applied = apply_fixes(html, [{'code': 'LOW_CONTRAST'}])
    assert 'color:' in fixed
    assert any(a['code'] == 'LOW_CONTRAST' for a in applied)
