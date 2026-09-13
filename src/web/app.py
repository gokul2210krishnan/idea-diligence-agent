"""
FastAPI demo UI for the Idea Diligence Agent.

    python -m src.main --web
    python -m src.web
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.demo_data import load_sample_investigation
from src.report import render_markdown_report


STATIC_DIR = Path(__file__).resolve().parent / "static"

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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "idea-diligence-agent", "phase": "3-4"}


@app.get("/api/demo", response_model=DiligenceResponse)
def demo() -> DiligenceResponse:
    state, scope, budget = load_sample_investigation()
    return _pack(state, scope, budget)


@app.post("/api/diligence", response_model=DiligenceResponse)
def diligence(request: IdeaRequest) -> DiligenceResponse:
    idea = request.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Idea cannot be empty.")

    if request.demo:
        state, scope, budget = load_sample_investigation()
        return _pack(state, scope, budget)

    from src.agents.orchestrator import run_diligence

    _formatted, state, scope, budget = run_diligence(idea)
    if not scope.is_valid:
        return _pack(
            state,
            scope,
            budget,
            rejected=True,
            reason=scope.rejection_reason,
        )
    return _pack(state, scope, budget)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
