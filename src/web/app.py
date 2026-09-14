"""
FastAPI demo UI for the Idea Diligence Agent.

    python -m src.main --web
    python -m src.web
"""

from __future__ import annotations

import logging
import sys
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.demo_data import load_sample_investigation
from src.report import render_markdown_report


STATIC_DIR = Path(__file__).resolve().parent / "static"
_LIVE_RUNS = threading.Semaphore(2)
_JOBS_LOCK = threading.Lock()
_MAX_JOBS = 32
_MAX_EVENTS = 200
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Idea Diligence Agent",
    description="Evidence-backed GO / MODIFY / KILL verdicts for product ideas.",
    version="3.0.0",
)


class IdeaRequest(BaseModel):
    idea: str = Field(min_length=1, description="Product idea to investigate")
    demo: bool = Field(default=False, description="If true, return the canned sample")


class DiligenceResponse(BaseModel):
    rejected: bool
    rejection_reason: Optional[str] = None
    verdict: Optional[dict[str, Any]] = None
    report_markdown: str = ""
    state: dict[str, Any] = Field(default_factory=dict)
    scope: dict[str, Any] = Field(default_factory=dict)
    budget: dict[str, Any] = Field(default_factory=dict)


class DiligenceJobResponse(BaseModel):
    job_id: str
    status: Literal["running", "done", "error"]
    error: Optional[str] = None
    result: Optional[DiligenceResponse] = None
    phase: str = "safety"
    events: list[dict[str, Any]] = Field(default_factory=list)


@dataclass
class _Job:
    job_id: str
    status: str = "running"
    error: Optional[str] = None
    result: Optional[DiligenceResponse] = None
    phase: str = "safety"
    events: list[dict[str, Any]] = field(default_factory=list)


_JOBS: dict[str, _Job] = {}


def configure_stdio() -> None:
    """Avoid UnicodeEncodeError when specialists print into a Windows console."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def _pack(state, scope_result, budget_status, rejected: bool = False, reason: str | None = None) -> DiligenceResponse:
    return DiligenceResponse(
        rejected=rejected,
        rejection_reason=reason,
        verdict=state.verdict.model_dump(mode="json") if state.verdict else None,
        report_markdown=render_markdown_report(state, scope_result, budget_status),
        state=state.model_dump(mode="json"),
        scope=scope_result.model_dump(mode="json"),
        budget=budget_status or {},
    )


def _snapshot(job: _Job) -> DiligenceJobResponse:
    return DiligenceJobResponse(
        job_id=job.job_id,
        status=job.status,  # type: ignore[arg-type]
        error=job.error,
        result=job.result,
        phase=job.phase,
        events=list(job.events),
    )


def _store_job(job: _Job) -> None:
    with _JOBS_LOCK:
        _JOBS[job.job_id] = job
        extra = len(_JOBS) - _MAX_JOBS
        if extra <= 0:
            return
        for job_id, stored in list(_JOBS.items()):
            if stored.status == "running":
                continue
            del _JOBS[job_id]
            extra -= 1
            if extra <= 0:
                break


def _get_job(job_id: str) -> _Job | None:
    with _JOBS_LOCK:
        return _JOBS.get(job_id)


def _append_event(job_id: str, event: dict[str, Any]) -> None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        job.events.append(event)
        if len(job.events) > _MAX_EVENTS:
            job.events = job.events[-_MAX_EVENTS:]
        job.phase = str(event.get("phase") or job.phase)


def _finish_job(job_id: str, **updates: Any) -> None:
    with _JOBS_LOCK:
        job = _JOBS.get(job_id)
        if job is None:
            return
        for key, value in updates.items():
            setattr(job, key, value)


def _run_live_job(job_id: str, idea: str) -> None:
    configure_stdio()

    def on_progress(event: dict[str, Any]) -> None:
        _append_event(job_id, event)

    try:
        from src.agents.orchestrator import run_diligence

        _formatted, state, scope, budget = run_diligence(idea, on_progress=on_progress)
        result = _pack(
            state,
            scope,
            budget,
            rejected=not scope.is_valid,
            reason=scope.rejection_reason,
        )
        _finish_job(job_id, status="done", result=result, phase="done")
    except Exception as exc:
        logger.exception("Live investigation %s failed", job_id)
        _append_event(job_id, {
            "at": "",
            "phase": "done",
            "level": "error",
            "message": f"{type(exc).__name__}: {exc}",
            "agent": None,
            "tool": None,
            "evidence_count": None,
        })
        _finish_job(
            job_id,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
            phase="done",
        )
    finally:
        _LIVE_RUNS.release()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "idea-diligence-agent",
        "phase": "3-4",
        "live": "jobs",
    }


@app.get("/api/demo", response_model=DiligenceResponse)
def demo() -> DiligenceResponse:
    state, scope, budget = load_sample_investigation()
    return _pack(state, scope, budget)


@app.post("/api/diligence")
def diligence(request: IdeaRequest):
    idea = request.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Idea cannot be empty.")

    if request.demo:
        state, scope, budget = load_sample_investigation()
        return _pack(state, scope, budget)

    if not _LIVE_RUNS.acquire(blocking=False):
        raise HTTPException(
            status_code=429,
            detail="Too many live investigations. Load the demo dossier or retry shortly.",
        )

    job_id = str(uuid.uuid4())
    _store_job(_Job(job_id=job_id))
    try:
        threading.Thread(
            target=_run_live_job,
            args=(job_id, idea),
            name=f"diligence-{job_id[:8]}",
            daemon=True,
        ).start()
    except Exception:
        _LIVE_RUNS.release()
        _finish_job(
            job_id,
            status="error",
            error="Could not start the investigation thread.",
            phase="done",
        )
        raise HTTPException(status_code=500, detail="Could not start the investigation.")

    job = _get_job(job_id)
    return JSONResponse(
        status_code=202,
        content=jsonable_encoder(_snapshot(job) if job else {"job_id": job_id, "status": "running"}),
    )


@app.get("/api/diligence/{job_id}", response_model=DiligenceJobResponse)
def diligence_job(job_id: str) -> DiligenceJobResponse:
    job = _get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown investigation.")
    return _snapshot(job)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
