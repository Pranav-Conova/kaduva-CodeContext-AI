"""Upload router: GitHub clone and ZIP upload endpoints."""

import logging
import traceback
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Project, Chunk
from app.services import repo_service, chunking, embedding, vector_store

router = APIRouter(prefix="/api/upload", tags=["upload"])
logger = logging.getLogger("codecontext.upload")


def _process_repo(project_id: int, repo_path: str, db_url: str):
    """
    Background task: parse, chunk, embed, and store a repository.
    Runs after the upload endpoint returns.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        # 1. Filter files
        logger.info("[Project %d] Scanning files...", project_id)
        files = repo_service.filter_files(repo_path)
        project.total_files = len(files)
        db.commit()

        if not files:
            project.status = "ready"
            project.total_chunks = 0
            db.commit()
            return

        # 2. Chunk all files
        logger.info("[Project %d] Chunking %d files...", project_id, len(files))
        all_chunks: list[chunking.CodeChunk] = []
        for f in files:
            file_chunks = chunking.chunk_file(f.relative_path, f.content, f.language)
            all_chunks.extend(file_chunks)

        if not all_chunks:
            project.status = "ready"
            db.commit()
            return

        # 3. Embed all chunks
        logger.info("[Project %d] Embedding %d chunks...", project_id, len(all_chunks))
        texts = [
            f"File: {c.file_path}\nSymbol: {c.symbol}\nLanguage: {c.language}\n\n{c.code}"
            for c in all_chunks
        ]
        embeddings = embedding.embed_texts(texts)

        # 4. Store in vector DB
        logger.info("[Project %d] Storing in vector DB...", project_id)
        ids = [f"chunk_{project_id}_{i}" for i in range(len(all_chunks))]
        documents = [c.code for c in all_chunks]
        metadatas = [
            {
                "file_path": c.file_path,
                "symbol": c.symbol,
                "language": c.language,
                "start_line": c.start_line or 0,
                "end_line": c.end_line or 0,
            }
            for c in all_chunks
        ]
        vector_store.add_chunks(project_id, ids, documents, embeddings, metadatas)

        # 5. Store chunk records in SQLite
        for i, c in enumerate(all_chunks):
            db.add(Chunk(
                project_id=project_id,
                file_path=c.file_path,
                symbol=c.symbol,
                content=c.code,
                language=c.language,
                start_line=c.start_line,
                end_line=c.end_line,
                chunk_index=i,
            ))

        project.total_chunks = len(all_chunks)
        project.status = "ready"
        db.commit()
        logger.info("[Project %d] ✅ Processing complete — %d chunks indexed", project_id, len(all_chunks))

    except Exception:
        logger.error("[Project %d] Processing failed", project_id)
        traceback.print_exc()
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = "error"
            db.commit()
    finally:
        db.close()


@router.post("/github")
def upload_github(
    url: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Clone a GitHub repo and start processing it."""
    try:
        repo_path = repo_service.clone_repo(url)
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="Failed to clone repository")

    name = url.rstrip("/").split("/")[-1].replace(".git", "")

    project = Project(
        name=name,
        source_type="github",
        source_url=url,
        repo_path=repo_path,
        status="processing",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    from app.config import settings
    background_tasks.add_task(_process_repo, project.id, repo_path, settings.DATABASE_URL)

    return {
        "project_id": project.id,
        "name": project.name,
        "status": "processing",
        "message": "Repository cloned. Processing started in background.",
    }


@router.post("/zip")
async def upload_zip(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
):
    """Upload and process a ZIP file."""
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Please upload a .zip file.")

    try:
        content = await file.read()
        repo_path = repo_service.extract_zip(content, file.filename)
    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail="Failed to extract ZIP")

    name = file.filename.replace(".zip", "")

    project = Project(
        name=name,
        source_type="zip",
        repo_path=repo_path,
        status="processing",
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    from app.config import settings
    background_tasks.add_task(_process_repo, project.id, repo_path, settings.DATABASE_URL)

    return {
        "project_id": project.id,
        "name": project.name,
        "status": "processing",
        "message": "ZIP extracted. Processing started in background.",
    }
