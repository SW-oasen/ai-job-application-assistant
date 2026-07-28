from app.parsers.markdown_renderer import render_safe_markdown


def test_renders_markdown_and_removes_unsafe_html() -> None:
    rendered = render_safe_markdown(
        "# Stelle\n\n- Python\n- SQL\n\n"
        "[Arbeitgeber](https://example.com)\n\n"
        '<script>alert("x")</script>'
    )

    assert "<h1>Stelle</h1>" in rendered
    assert "<li>Python</li>" in rendered
    assert 'href="https://example.com"' in rendered
    assert "<script" not in rendered
