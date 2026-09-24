from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import Chunk
from app.routers import documents
from app.services import embedding_service
from app.services.search_service import ensure_fts_table


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    # Create the FTS5 virtual table that init_db() would normally build
    with session_factory() as _init_session:
        ensure_fts_table(_init_session)


    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    original_upload_dir = documents.UPLOAD_DIR
    original_index_dir = embedding_service.INDEX_DIR
    documents.UPLOAD_DIR = tmp_path / "uploads"
    documents.UPLOAD_DIR.mkdir()
    embedding_service.INDEX_DIR = tmp_path / "indexes"
    embedding_service.INDEX_DIR.mkdir()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    documents.UPLOAD_DIR = original_upload_dir
    embedding_service.INDEX_DIR = original_index_dir


def pdf_bytes(text: str) -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    rect = fitz.Rect(50, 50, 550, 750)
    page.insert_textbox(rect, text)
    data = pdf.tobytes()
    pdf.close()
    return data


def upload_document(client: TestClient, text: str = "A permutation is an arrangement of objects in a particular order. The nPr formula counts arrangements where order matters."):
    response = client.post("/documents/upload", files={"files": ("math.pdf", io.BytesIO(pdf_bytes(text)), "application/pdf")})
    assert response.status_code == 201
    return response.json()[0]


def test_search_validation_errors(client: TestClient):
    blank = client.post("/search", json={"query": " ", "mode": "hybrid", "top_k": 5, "min_score": 0})
    assert blank.status_code == 422
    bad_mode = client.post("/search", json={"query": "x", "mode": "bad", "top_k": 5, "min_score": 0})
    assert bad_mode.status_code == 422
    bad_top_k = client.post("/search", json={"query": "x", "mode": "hybrid", "top_k": 11, "min_score": 0})
    assert bad_top_k.status_code == 422
    bad_min = client.post("/search", json={"query": "x", "mode": "hybrid", "top_k": 5, "min_score": 1.5})
    assert bad_min.status_code == 422


def test_search_without_indexed_documents_returns_clear_message(client: TestClient):
    response = client.post("/search", json={"query": "permutation", "mode": "keyword", "top_k": 5, "min_score": 0})
    assert response.status_code == 200
    assert response.json()["results"] == []
    assert "No indexed documents" in response.json()["message"]


def test_indexing_replaces_chunks_and_keyword_search_finds_formula(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.routers.documents.build_document_faiss_index", lambda document, chunks: True)
    document = upload_document(client, " ".join(["The nPr formula is used for permutation arrangements where order matters."] * 40))

    first = client.post(f"/documents/{document['id']}/index")
    second = client.post(f"/documents/{document['id']}/index")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["chunks_created"] == second.json()["chunks_created"]

    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        chunks = list(db.scalars(select(Chunk).where(Chunk.document_id == document["id"])).all())
    finally:
        try:
            next(generator)
        except StopIteration:
            pass
    assert len(chunks) == second.json()["chunks_created"]

    response = client.post("/search", json={"query": "nPr", "mode": "keyword", "top_k": 5, "min_score": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["results"]
    assert body["results"][0]["filename"] == "math.pdf"
    assert body["results"][0]["page_number"] == 1
    assert "<script" not in body["results"][0]["snippet"].lower()


def test_malformed_fts_query_does_not_crash(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.routers.documents.build_document_faiss_index", lambda document, chunks: True)
    document = upload_document(client, " ".join(["Factorial notation appears in permutation formulas."] * 40))
    assert client.post(f"/documents/{document['id']}/index").status_code == 200
    response = client.post("/search", json={"query": '" nPr * )', "mode": "keyword", "top_k": 5, "min_score": 0})
    assert response.status_code == 200


def test_delete_document_removes_chunks_and_fts_entries(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.routers.documents.build_document_faiss_index", lambda document, chunks: True)
    document = upload_document(client, " ".join(["Newton described force and acceleration relationships."] * 40))
    assert client.post(f"/documents/{document['id']}/index").status_code == 200
    deleted = client.delete(f"/documents/{document['id']}")
    assert deleted.status_code == 200
    debug = client.get(f"/search/debug/document/{document['id']}")
    assert debug.status_code == 404
