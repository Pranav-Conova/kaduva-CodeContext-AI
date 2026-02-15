"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """Global application settings loaded from .env file."""

    GEMINI_API_KEY: str = ""
    GROK_API_KEY: str = ""
    KIMI_API_KEY: str = ""
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    DATABASE_URL: str = "sqlite:///./codecontext.db"
    REPOS_DIR: str = "./repos"

    # Chunking
    MAX_CHUNK_LINES: int = 200
    FALLBACK_CHUNK_LINES: int = 150

    # Embedding
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 64

    # Retrieval
    DEFAULT_TOP_K: int = 20

    # LLM
    LLM_MODEL: str = "gemini-2.0-flash"
    GROK_MODEL: str = "grok-3-mini-fast"
    KIMI_MODEL: str = "moonshotai/kimi-k2-instruct"
    LLM_CODE_TEMPERATURE: float = 0.2
    LLM_CHAT_TEMPERATURE: float = 0.7

    # File filtering
    IGNORED_DIRS: list[str] = [
        "node_modules", ".git", "dist", "build", "venv",
        "__pycache__", ".next", ".venv", "env", ".idea",
        ".vscode", "coverage", ".tox", "egg-info",
    ]
    ALLOWED_EXTENSIONS: list[str] = [
        ".py", ".ts", ".tsx", ".js", ".jsx", ".go",
        ".java", ".json", ".yaml", ".yml", ".toml",
        ".md", ".rs", ".rb", ".php", ".cs", ".cpp",
        ".c", ".h", ".hpp", ".swift", ".kt",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
Path(settings.REPOS_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
