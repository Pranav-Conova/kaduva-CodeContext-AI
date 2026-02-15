"""Edit router: code modification and patch generation."""

import os
import logging
import traceback
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project
from app.services.retrieval import retrieve, build_context_prompt
from app.services.llm_service import generate_code_edit
from app.services.patch_service import generate_patch

router = APIRouter(prefix="/api/edit", tags=["edit"])
logger = logging.getLogger("codecontext.edit")


class EditRequest(BaseModel):
    instruction: str
    file_path: str
    provider: str = "gemini"


class EditResponse(BaseModel):
    file_path: str
    original_code: str
    modified_code: str
    patch: str


@router.post("/{project_id}", response_model=EditResponse)
def edit_file(
    project_id: int,
    request: EditRequest,
    db: Session = Depends(get_db),
):
    """Generate a code edit for a specific file."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.status != "ready":
        raise HTTPException(status_code=400, detail=f"Project is still {project.status}. Please wait.")

    provider = request.provider if request.provider in ("gemini", "grok", "kimi") else "gemini"

    full_path = os.path.join(project.repo_path, request.file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to read file")

    logger.info("[Project %d] Edit via %s for %s: '%s'", project_id, provider, request.file_path, request.instruction[:80])
    chunks = retrieve(project_id, f"{request.instruction} in {request.file_path}")
    context = build_context_prompt(chunks)

    try:
        modified_code = generate_code_edit(
            context=context,
            file_content=original_code,
            file_path=request.file_path,
            instruction=request.instruction,
            provider=provider,
        )
    except Exception:
        logger.error("LLM edit error (%s)", provider)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="LLM call failed")

    patch = generate_patch(original_code, modified_code, request.file_path)

    return EditResponse(
        file_path=request.file_path,
        original_code=original_code,
        modified_code=modified_code,
        patch=patch,
    )


@router.post("/{project_id}/apply")
def apply_edit(
    project_id: int,
    request: EditRequest,
    db: Session = Depends(get_db),
):
    """Apply a code edit by writing the modified content to disk."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    provider = request.provider if request.provider in ("gemini", "grok", "kimi") else "gemini"

    full_path = os.path.join(project.repo_path, request.file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    try:
        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            original_code = f.read()

        chunks = retrieve(project_id, f"{request.instruction} in {request.file_path}")
        context = build_context_prompt(chunks)

        modified_code = generate_code_edit(
            context=context,
            file_content=original_code,
            file_path=request.file_path,
            instruction=request.instruction,
            provider=provider,
        )

        with open(full_path, "w", encoding="utf-8") as f:
            f.write(modified_code)

        logger.info("[Project %d] ✅ Applied edit to %s via %s", project_id, request.file_path, provider)

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to apply edit")

    return {"message": "Edit applied successfully.", "file_path": request.file_path}
