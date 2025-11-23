from ai.accessibility.analyzer import analyze_html


def test_detects_missing_alt_and_form_label():
    html = """
    <html>
      <body>
        <img src="logo.png" />
        <a href="/"> </a>
        <form>
          <input type="text" id="name" />
        </form>
      </body>
    </html>
    """
    issues = analyze_html(html)
    codes = {i['code'] for i in issues}
    assert 'IMG_MISSING_ALT' in codes
    assert 'LINK_NO_TEXT' in codes
    assert 'FORM_CONTROL_NO_LABEL' in codes
