from io import BytesIO

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

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 20:
        short_lines = sum(len(line) <= 45 for line in lines)
        average_line_length = sum(len(line) for line in lines) / len(lines)
        if short_lines / len(lines) >= 0.65 and average_line_length < 55:
            return False
    return True
