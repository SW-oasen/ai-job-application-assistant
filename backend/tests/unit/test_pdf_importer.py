from app.importers.pdf_importer import pdf_text_is_sufficient


def test_accepts_meaningful_pdf_text() -> None:
    assert pdf_text_is_sufficient("Data Engineer " * 50, minimum_length=500)


def test_rejects_short_or_garbled_pdf_text() -> None:
    assert not pdf_text_is_sufficient("short", minimum_length=500)
    assert not pdf_text_is_sufficient("!" * 600, minimum_length=500)
    assert not pdf_text_is_sufficient(
        ("Scientific qualification benefits " * 30) + ("\ufffd" * 4),
        minimum_length=500,
    )


def test_rejects_fragmented_multicolumn_text() -> None:
    fragmented_lines = [
        f"Kurze Spaltenzeile {index}"
        for index in range(40)
    ]

    assert not pdf_text_is_sufficient(
        "\n".join(fragmented_lines),
        minimum_length=500,
    )
