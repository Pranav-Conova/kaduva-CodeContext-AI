"""Repository ingestion: clone GitHub repos, extract ZIPs, and filter files."""

import os
import logging
import shutil
import tempfile
import zipfile
import uuid
import re
from pathlib import Path
from dataclasses import dataclass

from app.config import settings

logger = logging.getLogger("codecontext.repo")


@dataclass
class FileInfo:
    """Represents a discovered source file."""
    path: str           # absolute path on disk
    relative_path: str  # path relative to repo root
    language: str       # detected language
    content: str        # file content (masked if .env)


EXTENSION_LANGUAGE_MAP = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".go": "go",
    ".java": "java", ".json": "json", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".md": "markdown",
    ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".cs": "csharp", ".cpp": "cpp", ".c": "c",
    ".h": "c", ".hpp": "cpp", ".swift": "swift", ".kt": "kotlin",
}


def clone_repo(github_url: str) -> str:
    """Clone a GitHub repository (shallow) and return the local path."""
    import git

    repo_id = str(uuid.uuid4())[:8]
    dest = os.path.join(settings.REPOS_DIR, repo_id)
    os.makedirs(dest, exist_ok=True)

    # Sanitize URL
    url = github_url.strip()
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS GitHub URLs are supported.")

    logger.info("Cloning %s → %s", url, dest)
    git.Repo.clone_from(url, dest, depth=1)
    logger.info("Clone complete → %s", dest)
    return dest


def extract_zip(file_bytes: bytes, original_filename: str) -> str:
    """Extract an uploaded ZIP file and return the extraction path."""
    repo_id = str(uuid.uuid4())[:8]
    dest = os.path.join(settings.REPOS_DIR, repo_id)
    os.makedirs(dest, exist_ok=True)

    logger.info("Extracting ZIP '%s' (%d bytes) → %s", original_filename, len(file_bytes), dest)

    zip_path = os.path.join(dest, "upload.zip")
    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)

    os.remove(zip_path)

    # If ZIP contained a single root folder, use that as the repo root
    entries = [e for e in os.listdir(dest) if not e.startswith(".")]
    if len(entries) == 1 and os.path.isdir(os.path.join(dest, entries[0])):
        final_path = os.path.join(dest, entries[0])
        logger.info("ZIP extracted (single root dir) → %s", final_path)
        return final_path

    logger.info("ZIP extracted → %s", dest)
    return dest


def _should_ignore_dir(dirname: str) -> bool:
    """Check if a directory should be skipped."""
    return dirname in settings.IGNORED_DIRS or dirname.startswith(".")


def _mask_env_content(content: str) -> str:
    """Mask sensitive values in .env files."""
    masked_lines = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0]
            masked_lines.append(f"{key}=***MASKED***")
        else:
            masked_lines.append(line)
    return "\n".join(masked_lines)


def filter_files(repo_path: str) -> list[FileInfo]:
    """
    Walk the repo directory and return a list of FileInfo for allowed files.
    Ignores specified directories, filters by extension, masks .env files.
    """
    files: list[FileInfo] = []
    repo_path = os.path.abspath(repo_path)
    skipped = 0

    for root, dirs, filenames in os.walk(repo_path):
        # Prune ignored directories in-place
        pruned = [d for d in dirs if _should_ignore_dir(d)]
        if pruned:
            logger.debug("Pruning ignored dirs: %s in %s", pruned, root)
        dirs[:] = [d for d in dirs if not _should_ignore_dir(d)]

        for filename in filenames:
            filepath = os.path.join(root, filename)
            ext = os.path.splitext(filename)[1].lower()

            # Allow .env files (will be masked)
            if filename == ".env" or filename.startswith(".env."):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    files.append(FileInfo(
                        path=filepath,
                        relative_path=os.path.relpath(filepath, repo_path).replace("\\", "/"),
                        language="env",
                        content=_mask_env_content(content),
                    ))
                    logger.debug("Masked .env file: %s", filepath)
                except Exception:
                    pass
                continue

            if ext not in settings.ALLOWED_EXTENSIONS:
                skipped += 1
                continue

            language = EXTENSION_LANGUAGE_MAP.get(ext, "unknown")

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Skip very large files (> 500KB)
                if len(content) > 500_000:
                    logger.warning("Skipping large file (%d bytes): %s", len(content), filepath)
                    continue

                files.append(FileInfo(
                    path=filepath,
                    relative_path=os.path.relpath(filepath, repo_path).replace("\\", "/"),
                    language=language,
                    content=content,
                ))
            except Exception as e:
                logger.warning("Failed to read %s: %s", filepath, e)
                continue

    logger.info("Filtered %d source files (%d skipped by extension)", len(files), skipped)
    return files


def get_file_tree(repo_path: str) -> dict:
    """Build a nested file tree structure for the frontend."""
    repo_path = os.path.abspath(repo_path)
    tree: dict = {"name": os.path.basename(repo_path), "type": "directory", "children": []}

    def _build(current_path: str, node: dict):
        try:
            entries = sorted(os.listdir(current_path))
        except PermissionError:
            return

        for entry in entries:
            full_path = os.path.join(current_path, entry)

            if os.path.isdir(full_path):
                if _should_ignore_dir(entry):
                    continue
                child = {"name": entry, "type": "directory", "children": []}
                _build(full_path, child)
                node["children"].append(child)
            else:
                ext = os.path.splitext(entry)[1].lower()
                if ext in settings.ALLOWED_EXTENSIONS or entry.startswith(".env"):
                    rel = os.path.relpath(full_path, repo_path).replace("\\", "/")
                    node["children"].append({
                        "name": entry,
                        "type": "file",
                        "path": rel,
                        "language": EXTENSION_LANGUAGE_MAP.get(ext, "unknown"),
                    })

    _build(repo_path, tree)
    return tree
