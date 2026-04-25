from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from celery import chord
from celery.result import AsyncResult
import pathlib

from schemas import JobRequest, JobSubmittedResponse, JobStatusResponse
from tasks import celery_app, compute_single, aggregate_results

app = FastAPI(
    title="Parallel Job Demo",
    description="Demonstrates FastAPI + Celery + Redis for distributed background computation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = pathlib.Path("/app/frontend")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """Serve the single-page frontend."""
    html_path = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(), status_code=200)


@app.post(
    "/start-job",
    response_model=JobSubmittedResponse,
    status_code=202,
    summary="Submit a parallel computation job",
)
def start_job(payload: JobRequest):
    if not payload.numbers:
        raise HTTPException(status_code=422, detail="'numbers' list must not be empty.")
    if len(payload.numbers) > 50:
        raise HTTPException(status_code=422, detail="Maximum 50 numbers per job.")

    job = chord(
        [compute_single.s(n, payload.operation) for n in payload.numbers],
    )(aggregate_results.s())
    return JobSubmittedResponse(job_id=job.id, total_tasks=len(payload.numbers))


@app.get(
    "/job-status/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll the status and result of a submitted job",
)
def job_status(job_id: str):
    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        return JobStatusResponse(job_id=job_id, status="pending")

    if result.state == "FAILURE":
        return JobStatusResponse(
            job_id=job_id,
            status="failed",
            error=str(result.info),
        )

    if result.state == "SUCCESS":
        data = result.get()
        return JobStatusResponse(
            job_id=job_id,
            status="success",
            results=data.get("results"),
            summary=data.get("summary"),
        )

    return JobStatusResponse(job_id=job_id, status=result.state.lower())