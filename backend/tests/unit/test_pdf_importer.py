import pymupdf

from app.importers.pdf_importer import (
    extract_pdf_text,
    normalize_native_pdf_text,
    pdf_text_is_sufficient,
    rasterize_pdf,
)


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


def test_rejects_overlapping_glyph_extraction_from_berlin_pdf() -> None:
    broken_header = (
        "H Hi il lf fs sr re ef fe er re en nt ti in n/ /H Hi il lf fs sr re ef fe er re en nt t "
        "D Da at te en na an na al ly ys se e ( (m m/ /w w/ /d d))"
    )
    text = "\n".join(
        [
            "Polizei Berlin",
            broken_header,
            "Die Arbeit bei der Polizei Berlin sorgt für mehr Sicherheit.",
            "Aufgaben und Anforderungen " * 30,
        ]
    )

    assert not pdf_text_is_sufficient(text, minimum_length=500)


def test_normalizes_native_pdf_layout_artifacts() -> None:
    text = (
        "Qualifikationen\n"
        "• Test-\n"
        "Driven Development und On-\n"
        "Premise-Systeme\n"
        "• Python\n"
        "&nbsp;\n"
        "Kontakt"
    )

    assert normalize_native_pdf_text(text) == (
        "Qualifikationen\n"
        "- Test-Driven Development und On-Premise-Systeme\n"
        "- Python\n\n"
        "Kontakt"
    )


def test_rasterize_pdf_removes_the_text_layer() -> None:
    source = pymupdf.open()
    page = source.new_page()
    page.insert_text((72, 72), "Broken text layer")
    content = source.tobytes()
    source.close()

    rasterized = rasterize_pdf(
        content,
        image_format="png",
        colorspace="grayscale",
        dpi=100,
        jpeg_quality=80,
        max_pages=5,
    )

    assert rasterized.startswith(b"%PDF")
    assert extract_pdf_text(rasterized) == ""
    result = pymupdf.open(stream=rasterized, filetype="pdf")
    image_xref = result[0].get_images(full=True)[0][0]
    assert pymupdf.Pixmap(result, image_xref).colorspace.n == 1
    result.close()


def test_rasterize_pdf_supports_rgb_jpeg() -> None:
    source = pymupdf.open()
    source.new_page()
    content = source.tobytes()
    source.close()

    rasterized = rasterize_pdf(
        content,
        image_format="jpeg",
        colorspace="rgb",
        dpi=72,
        jpeg_quality=75,
        max_pages=5,
    )

    result = pymupdf.open(stream=rasterized, filetype="pdf")
    image_xref = result[0].get_images(full=True)[0][0]
    assert pymupdf.Pixmap(result, image_xref).colorspace.n == 3
    result.close()
