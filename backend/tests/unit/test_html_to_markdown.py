from app.parsers.html_to_markdown import html_to_document


def test_extracts_main_content_and_removes_noise() -> None:
    document = html_to_document(
        """
        <html>
          <head><title>Portal title</title><script>bad()</script></head>
          <body>
            <nav>Navigation</nav>
            <main>
              <h1>Data Engineer</h1>
              <p>Build reliable data platforms.</p>
              <div class="cookie-banner">Accept cookies</div>
            </main>
            <footer>Footer links</footer>
          </body>
        </html>
        """
    )

    assert document.title == "Data Engineer"
    assert "# Data Engineer" in document.markdown
    assert "Build reliable data platforms." in document.markdown
    assert "Navigation" not in document.markdown
    assert "Accept cookies" not in document.markdown

