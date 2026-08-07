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
RELATED_JOBS_PATTERN = re.compile(
    r"\b(?:related jobs|similar jobs|recommended jobs|"
    r"diese jobs k(?:ö|Ã¶)nnten sie auch interessieren|"
    r"weitere stellenangebote)\b",
    re.IGNORECASE,
)
JOB_DETAIL_PATTERN = re.compile(
    r"\b(?:aufgaben|tätigkeiten|anforderungen|qualifikationen|profil|"
    r"stellenbeschreibung|what you(?:'|’)ll do|responsibilities|"
    r"requirements|qualifications|about the role)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedDocument:
    title: str | None
    markdown: str
    plain_text: str
    related_jobs_removed: bool = False


def html_to_document(html: str) -> ParsedDocument:
    soup = BeautifulSoup(html, "html.parser")
    title = _extract_title(soup)
    _expand_embedded_documents(soup)

    for element in soup.find_all(REMOVABLE_TAGS):
        element.decompose()
    for element in soup.find_all(attrs={"aria-hidden": "true"}):
        element.decompose()
    for element in soup.find_all(class_=NOISE_PATTERN):
        element.decompose()
    for element in soup.find_all(id=NOISE_PATTERN):
        element.decompose()

    content = _select_job_content(soup)
    related_jobs_removed = _remove_related_job_sections(content)
    _normalize_malformed_lists(content)
    rendered = markdownify(str(content), heading_style="ATX", bullets="-")
    rendered = re.sub(r"\n[ \t]+\n", "\n\n", rendered)
    rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip()
    plain_text = " ".join(content.stripped_strings)
    return ParsedDocument(
        title=title,
        markdown=rendered,
        plain_text=plain_text,
        related_jobs_removed=related_jobs_removed,
    )


def _expand_embedded_documents(soup: BeautifulSoup) -> None:
    """Expose SingleFile's embedded job document before removing iframes.

    Some portals render the complete advertisement in an iframe. SingleFile
    preserves it in the iframe's ``srcdoc`` attribute, so treating every iframe
    as noise would discard the only copy of the job description.
    """
    for frame in list(soup.find_all("iframe", srcdoc=True)):
        source = frame.get("srcdoc")
        if not isinstance(source, str) or not source.strip():
            continue
        embedded_soup = BeautifulSoup(source, "html.parser")
        embedded_root = embedded_soup.body or embedded_soup
        wrapper = soup.new_tag("div", attrs={"data-embedded-document": "true"})
        for child in list(embedded_root.contents):
            wrapper.append(child.extract())
        frame.replace_with(wrapper)


def _select_job_content(soup: BeautifulSoup):
    """Choose the element most likely to contain the actual advertisement.

    Portals frequently put a short job header and a long recommendation list in
    ``main`` while the description lives in an ``article`` or a sibling panel.
    Selecting the first ``main`` therefore made recommendation cards look like
    the imported job.
    """
    candidates = soup.select("main, article, [role='main']")
    if not candidates:
        return soup.body or soup

    def score(element) -> int:
        text = element.get_text(" ", strip=True)
        headings = " ".join(
            heading.get_text(" ", strip=True)
            for heading in element.find_all(["h1", "h2", "h3"])
        )
        return (
            min(len(text), 12_000) // 40
            + (300 if element.find("h1") else 0)
            + (500 if JOB_DETAIL_PATTERN.search(headings) else 0)
            - 700 * len(RELATED_JOBS_PATTERN.findall(headings))
        )

    return max(candidates, key=score)


def _remove_related_job_sections(content) -> bool:
    """Drop recommendation blocks before Markdown conversion.

    The heading is intentionally matched in the rendered DOM, so this also
    works for browser captures whose class names are minified or unstable.
    """
    removed = False
    for heading in list(content.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])):
        if not RELATED_JOBS_PATTERN.search(heading.get_text(" ", strip=True)):
            continue
        container = heading.find_parent(["section", "aside", "div", "ul", "ol"])
        if container is not None and container is not content:
            container.decompose()
        else:
            heading.decompose()
        removed = True
    return removed


def _normalize_malformed_lists(content) -> None:
    """Lift directly nested list items produced by malformed saved HTML.

    Browsers visually render ``<li>one<li>two`` as sibling items. Python's
    built-in HTML parser nests them, however, and markdownify then merges the
    entire list into one line. Only direct li-in-li children are lifted; valid
    nested lists using an intervening ul/ol remain untouched.
    """
    while True:
        nested = next(
            (
                child
                for item in content.find_all("li")
                for child in item.find_all("li", recursive=False)
            ),
            None,
        )
        if nested is None:
            return
        parent_item = nested.parent
        nested.extract()
        parent_item.insert_after(nested)


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
