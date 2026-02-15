"""CodeContext AI — FastAPI Application Entry Point."""

import os
import sys
import time
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.models import Project
from app.routers import upload, chat, edit
from app.services import repo_service

# ── Logging setup ───────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
    force=True,
)
# Silence noisy third-party loggers
for _name in (
    "urllib3", "httpcore", "httpx", "chromadb",
    "sentence_transformers", "openai", "google",
    "uvicorn.access", "watchfiles",
):
    logging.getLogger(_name).setLevel(logging.WARNING)

logger = logging.getLogger("codecontext")


# ── Lifespan ────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 CodeContext AI starting up...")
    init_db()
    logger.info("✅ Database initialized")
    yield
    logger.info("👋 CodeContext AI shutting down")


app = FastAPI(
    title="CodeContext AI",
    description="Self-hosted AI code intelligence — upload repos, ask questions, generate edits.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ──────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info("%s %s → %d (%.0fms)", request.method, request.url.path, response.status_code, elapsed)
        return response
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        logger.error("%s %s → UNHANDLED (%.0fms)", request.method, request.url.path, elapsed)
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Global exception handler ───────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {exc}"},
    )


# ── Routers ─────────────────────────────────────────────────
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(edit.router)


# ── Routes ──────────────────────────────────────────────────

@app.get("/")
def root():
    return {"app": "CodeContext AI", "version": "0.1.0", "docs": "/docs"}


@app.get("/api/providers")
def list_providers():
    """Return available LLM providers based on configured API keys."""
    providers = []
    if settings.GEMINI_API_KEY:
        providers.append({"id": "gemini", "name": "Google Gemini", "model": settings.LLM_MODEL})
    if settings.GROK_API_KEY:
        providers.append({"id": "grok", "name": "xAI Grok", "model": settings.GROK_MODEL})
    if settings.KIMI_API_KEY:
        providers.append({"id": "kimi", "name": "Kimi", "model": settings.KIMI_MODEL})
    return {"providers": providers, "default": providers[0]["id"] if providers else None}


@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    """List all projects."""
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "source_type": p.source_type,
            "source_url": p.source_url,
            "status": p.status,
            "total_files": p.total_files,
            "total_chunks": p.total_chunks,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in projects
    ]


@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project details including file tree."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    result = {
        "id": project.id,
        "name": project.name,
        "source_type": project.source_type,
        "source_url": project.source_url,
        "status": project.status,
        "total_files": project.total_files,
        "total_chunks": project.total_chunks,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }

    if project.status == "ready" and os.path.isdir(project.repo_path):
        result["file_tree"] = repo_service.get_file_tree(project.repo_path)

    return result


@app.get("/api/projects/{project_id}/file")
def get_file_content(project_id: int, path: str, db: Session = Depends(get_db)):
    """Read a specific file from the project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    full_path = os.path.join(project.repo_path, path)

    # Security: prevent path traversal
    abs_repo = os.path.abspath(project.repo_path)
    abs_file = os.path.abspath(full_path)
    if not abs_file.startswith(abs_repo):
        raise HTTPException(status_code=403, detail="Access denied.")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to read file.")

    ext = os.path.splitext(path)[1].lower()
    language = repo_service.EXTENSION_LANGUAGE_MAP.get(ext, "text")

    return {"path": path, "content": content, "language": language}
