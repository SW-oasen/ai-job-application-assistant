from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["home"])
HOME_PAGE = Path(__file__).resolve().parents[2] / "static" / "home.html"
MANAGE_PAGE = Path(__file__).resolve().parents[2] / "static" / "manage.html"
JOBS_PAGE = Path(__file__).resolve().parents[2] / "static" / "jobs.html"
JOB_PAGE = Path(__file__).resolve().parents[2] / "static" / "job-detail.html"
BROWSER_IMPORT_PAGE = Path(__file__).resolve().parents[2] / "static" / "browser-import.html"
BROWSER_RECEIVER_PAGE = (
    Path(__file__).resolve().parents[2] / "static" / "browser-import-receiver.html"
)


@router.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(HOME_PAGE)


@router.get("/manage", include_in_schema=False)
async def manage() -> FileResponse:
    return FileResponse(MANAGE_PAGE)


@router.get("/jobs", include_in_schema=False)
async def jobs() -> FileResponse:
    return FileResponse(JOBS_PAGE)


@router.get("/jobs/{job_id}", include_in_schema=False)
async def job_detail(job_id: str) -> FileResponse:
    return FileResponse(JOB_PAGE)


@router.get("/browser-import", include_in_schema=False)
async def browser_import() -> FileResponse:
    return FileResponse(BROWSER_IMPORT_PAGE)


@router.get("/browser-import/receive", include_in_schema=False)
async def browser_import_receiver() -> FileResponse:
    return FileResponse(BROWSER_RECEIVER_PAGE)
