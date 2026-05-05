"""
Autonomous Requirement-to-Code Refinement Agent - FastAPI Entry Point
ReAct Architecture: Reason → Act → Observe → Evaluate → Refine → Loop
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_db, disconnect_db
from app.routes import agent, sessions, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle management."""
    await connect_db()
    yield
    await disconnect_db()


app = FastAPI(
    title="ReAct Code Refinement Agent",
    description="Autonomous agent that iteratively refines code using ReAct architecture",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(agent.router, prefix="/api/v1", tags=["Agent"])
app.include_router(sessions.router, prefix="/api/v1", tags=["Sessions"])


@app.get("/")
async def root():
    return {
        "service": "ReAct Code Refinement Agent",
        "version": "1.0.0",
        "architecture": "Reason → Act → Observe → Evaluate → Refine",
    }
