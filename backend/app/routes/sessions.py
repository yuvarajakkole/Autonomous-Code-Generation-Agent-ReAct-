"""
Sessions Routes
===============
GET /sessions          - List recent sessions
GET /sessions/{id}     - Get full session detail with all iterations
DELETE /sessions/{id}  - Delete a session
"""

from fastapi import APIRouter, HTTPException
from app.core.database import get_db

router = APIRouter()


@router.get("/sessions")
async def list_sessions(limit: int = 20, skip: int = 0):
    db = get_db()
    cursor = db.sessions.find(
        {},
        {
            "session_id": 1,
            "raw_requirement": 1,
            "phase": 1,
            "total_iterations": 1,
            "success": 1,
            "created_at": 1,
            "final_score": 1,
        },
    ).sort("created_at", -1).skip(skip).limit(limit)

    sessions = []
    async for doc in cursor:
        doc.pop("_id", None)
        sessions.append(doc)

    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    db = get_db()
    doc = await db.sessions.find_one({"session_id": session_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Session not found")
    doc.pop("_id", None)
    doc.pop("_clarification_questions", None)
    return doc


@router.get("/sessions/{session_id}/iterations")
async def get_iterations(session_id: str):
    db = get_db()
    cursor = db.iterations.find(
        {"session_id": session_id}
    ).sort("iteration_number", 1)
    iterations = []
    async for doc in cursor:
        doc.pop("_id", None)
        iterations.append(doc)
    return {"iterations": iterations}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    db = get_db()
    result = await db.sessions.delete_one({"session_id": session_id})
    await db.iterations.delete_many({"session_id": session_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True, "session_id": session_id}
