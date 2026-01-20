"""Test new analyzer plugins (Phase 2)."""

import pytest

from analyzers.plugins import (
    ARIAAnalyzer,
    ButtonAnalyzer,
    DocumentStructureAnalyzer,
    LanguageAnalyzer,
    MediaAnalyzer,
    SkipLinkAnalyzer,
    TableAnalyzer,
)


class TestLanguageAnalyzer:
    """Tests for LanguageAnalyzer."""

    def test_missing_lang(self):
        """Test detection of missing lang attribute."""
        html = "<html><body>Hello</body></html>"
        analyzer = LanguageAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "MISSING_LANG" for i in issues)

    def test_valid_lang(self):
        """Test no issue for valid lang attribute."""
        html = '<html lang="en"><body>Hello</body></html>'
        analyzer = LanguageAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "MISSING_LANG" for i in issues)

    def test_invalid_lang(self):
        """Test detection of invalid lang code."""
        html = '<html lang="xyz"><body>Hello</body></html>'
        analyzer = LanguageAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "INVALID_LANG" for i in issues)

    def test_lang_with_region(self):
        """Test lang with region code is valid."""
        html = '<html lang="en-US"><body>Hello</body></html>'
        analyzer = LanguageAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "INVALID_LANG" for i in issues)


class TestButtonAnalyzer:
    """Tests for ButtonAnalyzer."""

    def test_button_no_text(self):
        """Test detection of button without text."""
        html = "<html><body><button></button></body></html>"
        analyzer = ButtonAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "BUTTON_NO_TEXT" for i in issues)

    def test_button_with_text(self):
        """Test no issue for button with text."""
        html = "<html><body><button>Click me</button></body></html>"
        analyzer = ButtonAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "BUTTON_NO_TEXT" for i in issues)

    def test_button_with_aria_label(self):
        """Test no issue for button with aria-label."""
        html = '<html><body><button aria-label="Submit"></button></body></html>'
        analyzer = ButtonAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "BUTTON_NO_TEXT" for i in issues)

    def test_input_button_no_value(self):
        """Test detection of input button without value."""
        html = '<html><body><input type="button"/></body></html>'
        analyzer = ButtonAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "BUTTON_NO_TEXT" for i in issues)

    def test_role_button_no_text(self):
        """Test detection of role=button without text."""
        html = '<html><body><div role="button"></div></body></html>'
        analyzer = ButtonAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "BUTTON_NO_TEXT" for i in issues)


class TestDocumentStructureAnalyzer:
    """Tests for DocumentStructureAnalyzer."""

    def test_missing_title(self):
        """Test detection of missing title."""
        html = "<html><head></head><body>Hello</body></html>"
        analyzer = DocumentStructureAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "MISSING_TITLE" for i in issues)

    def test_missing_main(self):
        """Test detection of missing main landmark."""
        html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        analyzer = DocumentStructureAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "MISSING_MAIN" for i in issues)

    def test_multiple_h1(self):
        """Test detection of multiple h1 elements."""
        html = "<html><body><main><h1>Title 1</h1><h1>Title 2</h1></main></body></html>"
        analyzer = DocumentStructureAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "MULTIPLE_H1" for i in issues)

    def test_missing_h1(self):
        """Test detection of missing h1."""
        html = "<html><head><title>Test</title></head><body><main><h2>Subtitle</h2></main></body></html>"
        analyzer = DocumentStructureAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "MISSING_H1" for i in issues)

    def test_valid_structure(self):
        """Test no issues for valid structure."""
        html = "<html><head><title>Test</title></head><body><main><h1>Title</h1></main></body></html>"
        analyzer = DocumentStructureAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "MISSING_TITLE" for i in issues)
        assert not any(i["code"] == "MISSING_MAIN" for i in issues)
        assert not any(i["code"] == "MISSING_H1" for i in issues)


class TestTableAnalyzer:
    """Tests for TableAnalyzer."""

    def test_table_no_headers(self):
        """Test detection of table without headers."""
        html = """
        <html><body>
            <table>
                <tr><td>Data 1</td><td>Data 2</td></tr>
                <tr><td>Data 3</td><td>Data 4</td></tr>
            </table>
        </body></html>
        """
        analyzer = TableAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "TABLE_NO_HEADERS" for i in issues)

    def test_table_with_headers(self):
        """Test no issue for table with headers."""
        html = """
        <html><body>
            <table>
                <caption>Test Table</caption>
                <tr><th scope="col">Header 1</th><th scope="col">Header 2</th></tr>
                <tr><td>Data 1</td><td>Data 2</td></tr>
            </table>
        </body></html>
        """
        analyzer = TableAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "TABLE_NO_HEADERS" for i in issues)

    def test_layout_table_ignored(self):
        """Test layout tables are ignored."""
        html = """
        <html><body>
            <table role="presentation">
                <tr><td>Layout</td><td>Content</td></tr>
            </table>
        </body></html>
        """
        analyzer = TableAnalyzer()
        issues = analyzer.analyze(html)
        assert len(issues) == 0


class TestARIAAnalyzer:
    """Tests for ARIAAnalyzer."""

    def test_invalid_role(self):
        """Test detection of invalid ARIA role."""
        html = '<html><body><div role="foobar">Content</div></body></html>'
        analyzer = ARIAAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "INVALID_ARIA_ROLE" for i in issues)

    def test_valid_role(self):
        """Test no issue for valid ARIA role."""
        html = '<html><body><div role="button">Click</div></body></html>'
        analyzer = ARIAAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "INVALID_ARIA_ROLE" for i in issues)

    def test_aria_hidden_focusable(self):
        """Test detection of aria-hidden on focusable element."""
        html = '<html><body><button aria-hidden="true">Hidden Button</button></body></html>'
        analyzer = ARIAAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "ARIA_HIDDEN_FOCUSABLE" for i in issues)


class TestSkipLinkAnalyzer:
    """Tests for SkipLinkAnalyzer."""

    def test_broken_skip_link(self):
        """Test detection of broken skip link."""
        html = """
        <html><body>
            <a href="#nonexistent">Skip to main</a>
            <nav>Navigation</nav>
            <main>Main content</main>
        </body></html>
        """
        analyzer = SkipLinkAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "BROKEN_SKIP_LINK" for i in issues)

    def test_valid_skip_link(self):
        """Test no issue for valid skip link."""
        html = """
        <html><body>
            <a href="#main">Skip to main</a>
            <nav>Navigation</nav>
            <main id="main">Main content</main>
        </body></html>
        """
        analyzer = SkipLinkAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "BROKEN_SKIP_LINK" for i in issues)


class TestMediaAnalyzer:
    """Tests for MediaAnalyzer."""

    def test_video_no_captions(self):
        """Test detection of video without captions."""
        html = '<html><body><video src="video.mp4"></video></body></html>'
        analyzer = MediaAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "VIDEO_NO_CAPTIONS" for i in issues)

    def test_video_with_captions(self):
        """Test no issue for video with captions."""
        html = """
        <html><body>
            <video src="video.mp4">
                <track kind="captions" src="captions.vtt"/>
            </video>
        </body></html>
        """
        analyzer = MediaAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "VIDEO_NO_CAPTIONS" for i in issues)

    def test_autoplay_no_controls(self):
        """Test detection of autoplay without controls."""
        html = '<html><body><video src="video.mp4" autoplay></video></body></html>'
        analyzer = MediaAnalyzer()
        issues = analyzer.analyze(html)
        assert any(i["code"] == "AUTOPLAY_NO_CONTROLS" for i in issues)

    def test_autoplay_muted(self):
        """Test no issue for muted autoplay."""
        html = '<html><body><video src="video.mp4" autoplay muted></video></body></html>'
        analyzer = MediaAnalyzer()
        issues = analyzer.analyze(html)
        assert not any(i["code"] == "AUTOPLAY_NO_CONTROLS" for i in issues)
