"""
AgentFlow API — main entry point.

WHAT IS FASTAPI?
  A Python web framework. You define functions, decorate them with @router.get/post,
  and FastAPI turns them into HTTP endpoints automatically.

WHAT IS UVICORN?
  The server that actually runs FastAPI. Think of it as the engine.

HOW TO RUN:
  cd backend
  source .venv/bin/activate
  uvicorn app.main:app --reload

  Then open: http://localhost:8000/docs  ← interactive API playground
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.agents.handlers  # noqa: F401 — register all agents on startup
from app.api.routes import auth, extract, health, pipeline, runs, upload, uploads, users, workflows
from app.logging_config import setup_logging

setup_logging()

app = FastAPI(
    title="AgentFlow API",
    description="Upload documents, describe a task, AI builds and runs a pipeline.",
    version="0.1.0",
)

# CORS — allows the Next.js frontend (different port) to call this API later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes — each router file owns a group of endpoints
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(upload.router)
app.include_router(uploads.router)
app.include_router(extract.router)
app.include_router(pipeline.router)
app.include_router(runs.router)
app.include_router(workflows.router)
