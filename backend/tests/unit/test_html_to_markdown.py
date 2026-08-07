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


def test_prefers_detail_article_over_related_jobs_main() -> None:
    document = html_to_document(
        """
        <html><body>
          <main>
            <h1>Data Scientist</h1><p>Deutsche Welle · Bonn</p>
            <section><h2>Diese Jobs könnten Sie auch interessieren</h2>
              <h3>Unrelated Data Analyst role</h3><p>Ostbevern</p>
            </section>
          </main>
          <article>
            <h1>Data Scientist</h1>
            <h2>Ihre Aufgaben</h2><p>Sie entwickeln Datenprodukte.</p>
            <h2>Ihr Profil</h2><p>Python und Statistik.</p>
          </article>
        </body></html>
        """
    )

    assert "Sie entwickeln Datenprodukte" in document.markdown
    assert "Unrelated Data Analyst role" not in document.markdown


def test_marks_when_related_jobs_were_removed() -> None:
    document = html_to_document(
        "<html><body><main><h1>Data Scientist</h1>"
        "<section><h2>Related jobs</h2><p>Other role</p></section>"
        "</main></body></html>"
    )

    assert document.related_jobs_removed is True


def test_extracts_singlefile_iframe_srcdoc_before_removing_iframe() -> None:
    document = html_to_document(
        """
        <html><body><main><h1>Data Scientist</h1></main>
        <iframe title="Stellenanzeige" srcdoc="
          &lt;html&gt;&lt;body&gt;&lt;article&gt;
          &lt;h1&gt;Data Scientist&lt;/h1&gt;
          &lt;h2&gt;Aufgaben&lt;/h2&gt;
          &lt;p&gt;Du entwickelst produktive Python-Modelle.&lt;/p&gt;
          &lt;h2&gt;Profil&lt;/h2&gt;
          &lt;p&gt;Erfahrung mit Statistik und Datenanalyse.&lt;/p&gt;
          &lt;/article&gt;&lt;/body&gt;&lt;/html&gt;
        "></iframe></body></html>
        """
    )

    assert "Du entwickelst produktive Python-Modelle" in document.markdown
    assert "Erfahrung mit Statistik" in document.markdown


def test_repairs_directly_nested_singlefile_list_items() -> None:
    document = html_to_document(
        """
        <html><body><article><h1>Data Scientist</h1><h2>Aufgaben</h2>
        <ul><li>Modelle entwickeln<li>Daten analysieren<li>Ergebnisse erklären</li></li></li></ul>
        </article></body></html>
        """
    )

    assert "- Modelle entwickeln\n- Daten analysieren\n- Ergebnisse erklären" in document.markdown
