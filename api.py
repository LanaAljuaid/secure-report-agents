"""
FastAPI layer for the AI Agents Report Generator
--------------------------------------------------
Thin HTTP wrapper around the existing LangGraph pipeline defined in
agent_report.py. This file does NOT duplicate any agent logic -- it imports
the already-compiled `report_manager` graph and just builds a fresh
ReportState per request, using the topic supplied by the caller instead of
a hardcoded/env-var default.

Run locally:
    uvicorn api:app --reload

Run in Docker: see Dockerfile (this is the default CMD).
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_report import report_manager, ReportState


app = FastAPI(
    title="AI Agents Report Generator",
    description="Multi-agent pipeline (Security -> Research -> Summarize -> Write -> Review) "
                 "coordinated by a LangGraph Report Manager.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class ReportRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The subject to generate a report on.",
        examples=["The impact of AI agents on enterprise productivity in 2026"],
    )


class ReportResponse(BaseModel):
    topic: str
    security_status: str
    blocked_reason: Optional[str] = None
    research_notes: str
    summary: str
    draft_report: str
    final_report: str
    log: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Simple liveness check."""
    return {"status": "ok"}


@app.post("/generate-report", response_model=ReportResponse)
def generate_report(request: ReportRequest):
    """
    Run the full agent pipeline for a caller-supplied topic.

    The Security Agent always runs first (see agent_report.py). If it blocks
    the topic, this still returns a 200 response with security_status =
    "blocked" and the other fields empty, rather than raising an error --
    that mirrors how the pipeline itself behaves (it stops gracefully, it
    doesn't crash).
    """
    initial_state: ReportState = {
        "topic": request.topic,
        "research_notes": "",
        "summary": "",
        "draft_report": "",
        "final_report": "",
        "log": [],
        "security_status": "",
        "blocked_reason": None,
    }

    try:
        result = report_manager.invoke(initial_state)
    except Exception as exc:
        # Something went wrong in one of the agents (e.g. an upstream API
        # error) -- surface it as a 502 rather than a raw stack trace.
        raise HTTPException(status_code=502, detail=f"Pipeline error: {exc}") from exc

    return ReportResponse(
        topic=result["topic"],
        security_status=result["security_status"],
        blocked_reason=result["blocked_reason"],
        research_notes=result["research_notes"],
        summary=result["summary"],
        draft_report=result["draft_report"],
        final_report=result["final_report"],
        log=result["log"],
    )
