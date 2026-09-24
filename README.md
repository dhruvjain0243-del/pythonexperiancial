# StudyVerse Offline

**A personal offline academic study assistant** — Upload your PDFs, build a searchable knowledge base, and use spaced repetition to study smarter.

## Stack

| Layer | Technology |
|-------|------------|
| **UI** | Streamlit (`app.py`) |
| **API** | FastAPI (`backend/app/main.py`) |
| **DB** | SQLite via SQLAlchemy |
| **PDF** | PyMuPDF (fitz) |
| **Search** | FAISS (semantic) + FTS5 BM25 (keyword) |
| **Spaced Rep** | SM-2 algorithm |

---

## Quick Start

### 1. Install backend dependencies
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start everything (Windows)
```bash
# From the project root — opens two windows:
start.bat
```

Or manually:

```bash
# Terminal 1 — FastAPI backend
cd backend
.venv\Scripts\uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Streamlit UI
# From project root:
backend\.venv\Scripts\streamlit run app.py
```

### 3. Open in browser
- **UI**: http://localhost:8501
- **API docs**: http://127.0.0.1:8000/docs

---

## Pages

| Page | What it does |
|------|--------------|
| 📚 **Library** | Upload PDFs, extract text, index for search |
| 🔍 **Search Notes** | Hybrid / semantic / keyword search across indexed docs |
| 🎯 **Practice Arena** | Auto-generate quiz cards from documents |
| 🔁 **Revision Hub** | SM-2 spaced repetition review of due flashcards |
| 📈 **Progress** | Streak, mastery breakdown, and retention stats |

---

## Tests

```bash
cd backend
.venv\Scripts\python -m pytest app/tests/ -v
# Expected: 11 passed
```

---

## Project Structure

```
studyverse/
├── app.py                    # Streamlit UI (all 5 pages)
├── start.bat                 # One-click launcher
├── requirements.txt          # Streamlit + requests
└── backend/
    ├── requirements.txt      # FastAPI, SQLAlchemy, PyMuPDF, FAISS, etc.
    └── app/
        ├── main.py           # FastAPI app + router registration
        ├── database.py       # SQLAlchemy engine + session
        ├── models.py         # Document, PageText, Chunk, Flashcard, StudyLog
        ├── schemas.py        # Pydantic request/response schemas
        ├── routers/
        │   ├── documents.py  # Upload, index, delete
        │   ├── search.py     # Hybrid/semantic/keyword search
        │   ├── practice.py   # Flashcard generation + management
        │   ├── revision.py   # SM-2 due-card review
        │   ├── progress.py   # Analytics summary
        │   └── health.py     # /health endpoint
        └── services/
            ├── pdf_service.py          # PyMuPDF text extraction
            ├── chunk_service.py        # Sliding-window chunking
            ├── embedding_service.py    # Sentence-transformer embeddings + FAISS
            ├── search_service.py       # FTS5 + FAISS + hybrid merge
            ├── quiz_service.py         # Regex-based concept card extraction
            └── spaced_repetition_service.py  # SM-2 algorithm
```
