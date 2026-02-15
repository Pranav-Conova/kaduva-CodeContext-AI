# CodeContext AI

A self-hosted AI code intelligence system. Upload a repository, ask questions about it, and get AI-powered code edits — powered by **Gemini 2.0 Flash**, **Grok**, and **Kimi**.

![License](https://img.shields.io/badge/license-MIT-blue)

## Features

- **📁 Upload** — Clone from GitHub URL or upload ZIP
- **🔍 Smart Indexing** — AST-based code chunking + vector embeddings
- **💬 AI Chat** — Ask questions about the codebase with source references
- **✏️ Code Edits** — AI-generated modifications with unified diff preview
- **📄 File Browser** — Interactive file tree with syntax-highlighted preview
- **🔀 Multi-Provider** — Switch between Gemini, Grok (xAI), and Kimi

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- API keys for at least one LLM provider (Gemini / Grok / Kimi)

### 1. Clone & Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Setup Frontend

```bash
cd frontend
npm install
```

### 3. Run Everything

```powershell
# From the project root:
.\run.ps1            # Start both backend + frontend
.\run.ps1 stop       # Stop all processes
```

Or start manually:

```bash
# Terminal 1 — Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### 4. Open the App

Navigate to **http://localhost:5173**

## Architecture

```
┌──────────────────┐      ┌──────────────────────────┐
│  React Frontend  │─────▶│   FastAPI Backend         │
│  (Vite :5173)    │      │   (Uvicorn :8000)         │
└──────────────────┘      │                            │
                          │  Repo Service (Clone/ZIP)  │
                          │         ▼                  │
                          │  Chunking (AST / Regex)    │
                          │         ▼                  │
                          │  Embeddings (MiniLM-L6-v2) │
                          │         ▼                  │
                          │  Vector Store (NumPy)      │
                          │         ▼                  │
                          │  LLM (Gemini / Grok / Kimi)│
                          └──────────────────────────┘
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/providers` | List available LLM providers |
| `GET` | `/api/projects` | List all projects |
| `GET` | `/api/projects/:id` | Project details + file tree |
| `GET` | `/api/projects/:id/file?path=...` | Read a file |
| `POST` | `/api/upload/github` | Clone a GitHub repo |
| `POST` | `/api/upload/zip` | Upload a ZIP file |
| `POST` | `/api/chat/:id` | Ask a question |
| `GET` | `/api/chat/:id/history` | Chat history |
| `POST` | `/api/edit/:id` | Generate code edit |
| `POST` | `/api/edit/:id/apply` | Apply edit to disk |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + Uvicorn |
| Database | SQLite (SQLAlchemy) |
| Vector Store | NumPy cosine similarity |
| Embeddings | all-MiniLM-L6-v2 |
| LLM | Gemini 2.0 Flash / Grok / Kimi |
| Frontend | React 19 + Vite 7 |
| Styling | Vanilla CSS (dark glassmorphism) |

## Project Structure

```
kaduva/
├── backend/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Settings from .env
│   │   ├── database.py       # SQLite setup
│   │   ├── models.py         # ORM models
│   │   ├── routers/
│   │   │   ├── upload.py     # Upload endpoints
│   │   │   ├── chat.py       # Chat endpoints
│   │   │   └── edit.py       # Edit endpoints
│   │   └── services/
│   │       ├── repo_service.py    # Clone / ZIP extraction
│   │       ├── chunking.py        # AST / regex chunking
│   │       ├── embedding.py       # Sentence-transformer embeddings
│   │       ├── vector_store.py    # NumPy vector search
│   │       ├── retrieval.py       # Query → top-K retrieval
│   │       ├── llm_service.py     # Multi-provider LLM calls
│   │       └── patch_service.py   # Unified diff generation
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── run.ps1                   # Start / stop script
└── .gitignore
```

## License

MIT
