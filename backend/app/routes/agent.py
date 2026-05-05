"""
Agent Routes
============
POST /agent/start              - Start session, get clarification questions
POST /agent/submit             - Submit answers, begin ReAct loop
GET  /agent/stream/{id}        - SSE stream of real-time agent events
GET  /agent/status/{id}        - Current session status
GET  /agent/output/{id}        - Download generated project as ZIP
GET  /agent/preview/{id}       - Serve the generated index.html directly
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.agents.react_loop import ReActLoopController
from app.core.database import get_db
from app.models.schemas import (
    AgentPhase,
    AgentStatusResponse,
    ClarificationQA,
    ClarificationResponse,
    Session,
    StartAgentRequest,
)
from app.tools import RequirementClarificationTool

router = APIRouter()
_clarification_tool = RequirementClarificationTool()

# ── Output directory for generated projects ───────────────────
_OUTPUT_DIR = Path(__file__).parent.parent.parent / "generated_projects"
_OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
# POST /agent/start
# ─────────────────────────────────────────────────────────────

@router.post("/agent/start", response_model=ClarificationResponse)
async def start_agent(body: StartAgentRequest):
    db = get_db()
    session_id = str(uuid.uuid4())
    questions = await _clarification_tool.generate_questions(body.requirement)

    session = Session(
        session_id=session_id,
        raw_requirement=body.requirement,
        phase=AgentPhase.CLARIFICATION,
    )
    await db.sessions.insert_one(session.model_dump())
    await db.sessions.update_one(
        {"session_id": session_id},
        {"$set": {"_clarification_questions": questions}},
    )
    return ClarificationResponse(session_id=session_id, questions=questions)


# ─────────────────────────────────────────────────────────────
# POST /agent/submit
# ─────────────────────────────────────────────────────────────

@router.post("/agent/submit")
async def submit_clarifications(session_id: str, answers: dict[str, str]):
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    questions: list = doc.get("_clarification_questions", [])
    qa_pairs = [
        ClarificationQA(
            question=q,
            answer=answers.get(str(i), answers.get(q, "Not specified")),
        )
        for i, q in enumerate(questions)
    ]

    clarification_tool = RequirementClarificationTool()
    refined_data = await clarification_tool.refine_requirement(
        original=doc["raw_requirement"],
        qa_pairs=qa_pairs,
    )

    await db.sessions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "clarifications": [qa.model_dump() for qa in qa_pairs],
                "refined_requirement": refined_data.get(
                    "refined_requirement", doc["raw_requirement"]
                ),
                "_acceptance_criteria": refined_data.get("acceptance_criteria", []),
                "phase": AgentPhase.PLANNING,
                "updated_at": datetime.utcnow().isoformat(),
            }
        },
    )
    return {
        "status": "accepted",
        "session_id": session_id,
        "message": "Connect to /agent/stream/{session_id} to start",
    }


# ─────────────────────────────────────────────────────────────
# GET /agent/stream/{session_id}  – SSE
# ─────────────────────────────────────────────────────────────

@router.get("/agent/stream/{session_id}")
async def stream_agent(session_id: str):
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    doc.pop("_id", None)
    criteria = doc.pop("_acceptance_criteria", [])
    doc.pop("_clarification_questions", None)

    valid_fields = set(Session.model_fields.keys())
    clean_doc = {k: v for k, v in doc.items() if k in valid_fields}
    session = Session(**clean_doc)
    session.session_id = session_id

    controller = ReActLoopController(session_id=session_id)

    async def event_generator() -> AsyncIterator[str]:
        yield ": connected\n\n"
        async for event in controller.run(session):
            payload = {
                "event":      event.event,
                "session_id": event.session_id,
                "timestamp":  event.timestamp.isoformat(),
                "data":       event.data,
            }
            yield f"data: {json.dumps(payload)}\n\n"

            # When completed, save files to disk
            if event.event == "completed":
                _save_project_files(session_id, event.data.get("final_code", ""))

        yield 'data: {"event": "stream_end"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ─────────────────────────────────────────────────────────────
# GET /agent/status/{session_id}
# ─────────────────────────────────────────────────────────────

@router.get("/agent/status/{session_id}", response_model=AgentStatusResponse)
async def get_status(session_id: str):
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    score = doc.get("final_score", {})
    return AgentStatusResponse(
        session_id=session_id,
        phase=doc.get("phase", AgentPhase.CLARIFICATION),
        iterations=doc.get("total_iterations", 0),
        final_score=score.get("overall") if isinstance(score, dict) else None,
        success=doc.get("success", False),
        final_code=doc.get("final_code", ""),
    )


# ─────────────────────────────────────────────────────────────
# GET /agent/preview/{session_id}  – serve index.html
# ─────────────────────────────────────────────────────────────

@router.get("/agent/preview/{session_id}", response_class=HTMLResponse)
async def preview_project(session_id: str):
    """Serve the generated index.html directly in the browser."""
    project_dir = _OUTPUT_DIR / session_id
    index = project_dir / "index.html"
    if not index.exists():
        # Try fetching from DB
        db = get_db()
        doc = await db.sessions.find_one({"session_id": session_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Session not found")
        final_code = doc.get("final_code", "")
        if not final_code:
            raise HTTPException(status_code=404, detail="No generated files yet")
        _save_project_files(session_id, final_code)

    if index.exists():
        return HTMLResponse(content=index.read_text())
    raise HTTPException(status_code=404, detail="index.html not found in generated project")


# ─────────────────────────────────────────────────────────────
# GET /agent/output/{session_id}  – download ZIP
# ─────────────────────────────────────────────────────────────

@router.get("/agent/output/{session_id}")
async def download_project(session_id: str):
    """Download all generated project files as a ZIP."""
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")

    final_code = doc.get("final_code", "")
    if not final_code:
        raise HTTPException(status_code=404, detail="No generated code found")

    files = _extract_files(final_code)
    if not files:
        files = {"index.html": final_code}

    # Build ZIP in memory
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)

        # Add a README
        req = doc.get("raw_requirement", "")
        readme = f"# Generated Project\n\n**Requirement:** {req}\n\n## How to run\n\nOpen `index.html` in your browser.\n"
        zf.writestr("README.md", readme)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="project-{session_id[:8]}.zip"'
        },
    )


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _extract_files(code: str) -> dict[str, str]:
    """Extract files dict from project JSON or return single file."""
    try:
        cleaned = code.strip()
        for prefix in ("```json", "```"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        data = json.loads(cleaned.strip())
        if isinstance(data, dict) and "files" in data:
            return data["files"]
    except (json.JSONDecodeError, TypeError):
        pass

    # Single HTML file
    if "<html" in code.lower() or "<!doctype" in code.lower():
        return {"index.html": code}

    return {"solution.py": code}


def _save_project_files(session_id: str, code: str) -> None:
    """Save generated files to disk for preview/download."""
    project_dir = _OUTPUT_DIR / session_id
    project_dir.mkdir(parents=True, exist_ok=True)

    files = _extract_files(code)
    for fname, content in files.items():
        fpath = project_dir / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        fpath.write_text(content)
