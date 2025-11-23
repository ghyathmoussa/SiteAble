"""Test plugin-based analyzers."""
from analyzers.plugins import (
    AltTextAnalyzer,
    FormLabelAnalyzer,
    HeadingOrderAnalyzer,
    ContrastAnalyzer,
    LinkTextAnalyzer,
)


def test_alt_text_analyzer():
    html = '<html><body><img src="logo.png"/></body></html>'
    analyzer = AltTextAnalyzer()
    issues = analyzer.analyze(html)
    assert any(i['code'] == 'IMG_MISSING_ALT' for i in issues)


def test_form_label_analyzer():
    html = '<html><body><form><input type="text" id="name" /></form></body></html>'
    analyzer = FormLabelAnalyzer()
    issues = analyzer.analyze(html)
    assert any(i['code'] == 'FORM_CONTROL_NO_LABEL' for i in issues)


def test_heading_order_analyzer():
    html = '<html><body><h1>Title</h1><h3>Subtitle</h3></body></html>'
    analyzer = HeadingOrderAnalyzer()
    issues = analyzer.analyze(html)
    assert any(i['code'] == 'HEADING_ORDER' for i in issues)


def test_contrast_analyzer():
    html = '<html><body><p style="color: #777777; background-color: #ffffff">text</p></body></html>'
    analyzer = ContrastAnalyzer()
    issues = analyzer.analyze(html)
    assert any(i['code'] == 'LOW_CONTRAST' for i in issues)


def test_link_text_analyzer():
    html = '<html><body><a href="/"></a></body></html>'
    analyzer = LinkTextAnalyzer()
    issues = analyzer.analyze(html)
    assert any(i['code'] == 'LINK_NO_TEXT' for i in issues)
