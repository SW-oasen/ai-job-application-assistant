import re
from dataclasses import dataclass

from bs4 import BeautifulSoup
from markdownify import markdownify

REMOVABLE_TAGS = {
    "script",
    "style",
    "svg",
    "noscript",
    "iframe",
    "nav",
    "footer",
    "header",
    "form",
    "aside",
}
NOISE_PATTERN = re.compile(
    r"(cookie|consent|privacy-banner|navigation|breadcrumb|social-share|newsletter)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedDocument:
    title: str | None
    markdown: str
    plain_text: str


def html_to_document(html: str) -> ParsedDocument:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)

    for element in soup.find_all(REMOVABLE_TAGS):
        element.decompose()
    for element in soup.find_all(attrs={"aria-hidden": "true"}):
        element.decompose()
    for element in soup.find_all(class_=NOISE_PATTERN):
        element.decompose()
    for element in soup.find_all(id=NOISE_PATTERN):
        element.decompose()

    content = soup.find("main") or soup.find("article") or soup.body or soup
    rendered = markdownify(str(content), heading_style="ATX", bullets="-")
    rendered = re.sub(r"\n[ \t]+\n", "\n\n", rendered)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip()
    plain_text = " ".join(content.stripped_strings)
    return ParsedDocument(title=title, markdown=rendered, plain_text=plain_text)


def _extract_title(soup: BeautifulSoup) -> str | None:
    heading = soup.find("h1")
    if heading and heading.get_text(" ", strip=True):
        return heading.get_text(" ", strip=True)

    for attribute, value in (("property", "og:title"), ("name", "twitter:title")):
        meta = soup.find("meta", attrs={attribute: value})
        if meta and meta.get("content"):
            return str(meta["content"]).strip()

    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None

