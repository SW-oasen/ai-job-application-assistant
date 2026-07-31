from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ControlledImportError(BaseModel):
    code: str
    message: str
    details: dict | None = None


class UrlImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=2048)
    force_browser: bool = False


class UrlImportResponse(BaseModel):
    success: bool
    source_type: Literal["url"] = "url"
    source_url: str
    retrieval_method: Literal["http", "browser"]
    title: str | None
    raw_html: str
    markdown: str
    content_hash: str
    text_length: int
    quality_sufficient: bool
    browser_fallback_recommended: bool
    warnings: list[str]
    job_id: str | None = None
    duplicate: bool = False
    error: ControlledImportError | None = None


class PdfImportResponse(BaseModel):
    success: bool
    source_type: Literal["pdf"] = "pdf"
    filename: str
    extraction_method: Literal["native_pdf", "mineru"]
    markdown: str
    text_length: int
    content_hash: str
    mineru_task_id: str | None = None
    warnings: list[str]
    job_id: str | None = None
    duplicate: bool = False
    reimported: bool = False


class HtmlImportResponse(BaseModel):
    success: bool
    source_type: Literal["html"] = "html"
    filename: str
    extraction_method: Literal["native_html"] = "native_html"
    title: str | None
    markdown: str
    text_length: int
    content_hash: str
    warnings: list[str]
    job_id: str | None = None
    duplicate: bool = False


class BrowserCaptureRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_url: str = Field(min_length=1, max_length=2048)
    html: str = Field(min_length=20)


class JobReimportResponse(BaseModel):
    success: bool = True
    job_id: UUID
    source_type: Literal["url", "pdf", "html"]
    retrieval_method: str
    language: Literal["de", "en"] | None = None
    warnings: list[str]
    reimported: bool = True
