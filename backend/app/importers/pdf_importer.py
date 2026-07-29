import re
from io import BytesIO
from itertools import pairwise
from typing import Literal

import pymupdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.core.errors import ApplicationError


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
    except (PdfReadError, OSError, ValueError) as exception:
        raise ApplicationError(
            "The uploaded PDF could not be read.",
            code="invalid_pdf",
            status_code=422,
        ) from exception
    return "\n\n".join(page for page in pages if page).strip()


def pdf_text_is_sufficient(text: str, *, minimum_length: int) -> bool:
    normalized = " ".join(text.split())
    if len(normalized) < minimum_length:
        return False
    replacement_characters = normalized.count("\ufffd")
    if replacement_characters >= 3 and replacement_characters / len(normalized) >= 0.001:
        return False
    visible_characters = [character for character in normalized if not character.isspace()]
    if not visible_characters:
        return False
    meaningful = sum(character.isalnum() for character in visible_characters)
    if meaningful / len(visible_characters) < 0.5:
        return False
    if pdf_text_has_broken_glyphs(text):
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 20:
        short_lines = sum(len(line) <= 45 for line in lines)
        average_line_length = sum(len(line) for line in lines) / len(lines)
        if short_lines / len(lines) >= 0.65 and average_line_length < 55:
            return False
    return True


def pdf_text_has_broken_glyphs(text: str) -> bool:
    """Detect broken PDF font mappings such as ``H Hi il lf fs...``."""
    for line in text.splitlines():
        tokens = re.findall(r"[^\W\d_]+", line, flags=re.UNICODE)
        longest_run = 1
        for previous, current in pairwise(tokens):
            if (
                len(previous) <= 2
                and len(current) == 2
                and previous[-1].casefold() == current[0].casefold()
            ):
                longest_run += 1
                if longest_run >= 6:
                    return True
            else:
                longest_run = 1
    return False


def normalize_native_pdf_text(text: str) -> str:
    """Clean layout artifacts without flattening metadata fields and headings."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"-[ \t]*\n[ \t]*(?=[^\W\d_])", "-", normalized)
    normalized = re.sub(r"(?m)^[ \t]*(?:&nbsp;|\xa0)[ \t]*$", "", normalized)
    normalized = re.sub(r"(?m)^[ \t]*[•●▪][ \t]+", "- ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def rasterize_pdf(
    content: bytes,
    *,
    image_format: Literal["png", "jpeg"],
    colorspace: Literal["grayscale", "rgb"],
    dpi: int,
    jpeg_quality: int,
    max_pages: int,
) -> bytes:
    """Replace every PDF page with a rendered image, discarding its text layer."""
    try:
        source = pymupdf.open(stream=content, filetype="pdf")
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exception:
        raise ApplicationError(
            "The uploaded PDF could not be rasterized.",
            code="invalid_pdf",
            status_code=422,
        ) from exception

    try:
        if source.page_count > max_pages:
            raise ApplicationError(
                "The PDF has too many pages for image-based OCR.",
                code="pdf_raster_page_limit_exceeded",
                status_code=422,
                details={"max_pages": max_pages, "page_count": source.page_count},
            )

        target = pymupdf.open()
        try:
            scale = dpi / 72
            matrix = pymupdf.Matrix(scale, scale)
            render_colorspace = (
                pymupdf.csGRAY if colorspace == "grayscale" else pymupdf.csRGB
            )
            for source_page in source:
                pixmap = source_page.get_pixmap(
                    matrix=matrix,
                    colorspace=render_colorspace,
                    alpha=False,
                )
                if image_format == "jpeg":
                    image = pixmap.tobytes("jpeg", jpg_quality=jpeg_quality)
                else:
                    image = pixmap.tobytes("png")
                target_page = target.new_page(
                    width=source_page.rect.width,
                    height=source_page.rect.height,
                )
                target_page.insert_image(target_page.rect, stream=image)
            return target.tobytes(garbage=4, deflate=True)
        finally:
            target.close()
    except ApplicationError:
        raise
    except (RuntimeError, ValueError, MemoryError) as exception:
        raise ApplicationError(
            "The PDF could not be converted for image-based OCR.",
            code="pdf_rasterization_failed",
            status_code=422,
        ) from exception
    finally:
        source.close()
