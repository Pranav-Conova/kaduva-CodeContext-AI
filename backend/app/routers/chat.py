"""Chat router: Q&A endpoint with repo context."""

import logging
import traceback
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, ChatMessage
from app.services.retrieval import retrieve, build_context_prompt
from app.services.llm_service import ask_question

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger("codecontext.chat")


class ChatRequest(BaseModel):
    question: str
    provider: str = "gemini"


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]


@router.post("/{project_id}", response_model=ChatResponse)
def chat_with_project(
    project_id: int,
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """Ask a question about a project's codebase."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.status != "ready":
        raise HTTPException(status_code=400, detail=f"Project is still {project.status}. Please wait.")

    provider = request.provider if request.provider in ("gemini", "grok", "kimi") else "gemini"
    logger.info("[Project %d] Chat via %s: '%s'", project_id, provider, request.question[:80])

    # 1. Retrieve relevant chunks
    chunks = retrieve(project_id, request.question)

    # 2. Build context
    context = build_context_prompt(chunks)

    # 3. Ask LLM
    try:
        answer = ask_question(context, request.question, provider=provider)
    except Exception:
        logger.error("LLM error (%s)", provider)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="LLM call failed")

    # 4. Build sources list
    sources = []
    seen_files = set()
    for chunk in chunks:
        if chunk.file_path not in seen_files:
            sources.append({
                "file_path": chunk.file_path,
                "symbol": chunk.symbol,
                "language": chunk.language,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
            })
            seen_files.add(chunk.file_path)

    # 5. Save to chat history
    db.add(ChatMessage(project_id=project_id, role="user", content=request.question))
    db.add(ChatMessage(project_id=project_id, role="assistant", content=answer, sources=sources))
    db.commit()

    return ChatResponse(answer=answer, sources=sources)


@router.get("/{project_id}/history")
def get_chat_history(project_id: int, db: Session = Depends(get_db)):
    """Get chat history for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]
