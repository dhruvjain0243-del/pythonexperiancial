from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

import fitz
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import DATA_DIR, get_db
from ..models import Chunk, Document, PageText
from ..schemas import (
    DeleteDocumentResponse,
    DocumentDetailResponse,
    DocumentResponse,
    IndexAllResponse,
    IndexDocumentResponse,
    PageTextResponse,
)
from ..services import chunk_service, embedding_service, search_service
from ..services.chunk_service import create_chunk_drafts_for_document, save_chunks
from ..services.embedding_service import build_document_faiss_index, document_index_exists, remove_document_faiss_files
from ..services.search_service import delete_document_chunks, fts_entry_count, insert_chunk_fts_entries

router = APIRouter(prefix="/documents", tags=["Documents"])
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(filename: str | None) -> str:
    original = Path(filename or "document.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", original).strip("._")
    return cleaned or "document.pdf"


def extraction_message_for(status_name: str, filename: str) -> str | None:
    if status_name == "warning":
        return f"No searchable text was found in {filename}. It may be scanned or image-based."
    if status_name == "failed":
        return f"{filename} could not be read as a valid PDF."
    return None


def store_upload(upload: UploadFile) -> tuple[Path, str]:
    filename = safe_filename(upload.filename)
    stored_name = f"{uuid.uuid4().hex}_{filename}"
    target = UPLOAD_DIR / stored_name
    with target.open("wb") as output:
        shutil.copyfileobj(upload.file, output)
    return target, stored_name


def extract_pdf(path: Path) -> tuple[int, list[tuple[int, str]], str | None]:
    try:
        with fitz.open(path) as pdf:
            if pdf.needs_pass:
                return 0, [], "This PDF is password-protected and cannot be extracted locally."
            page_text: list[tuple[int, str]] = []
            for index, page in enumerate(pdf, start=1):
                text = (page.get_text("text") or "").strip()
                page_text.append((index, text))
            return len(pdf), page_text, None
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        return 0, [], f"The PDF could not be read safely: {exc.__class__.__name__}."


@router.post("/upload", response_model=list[DocumentResponse], status_code=status.HTTP_201_CREATED, summary="Upload one or more PDF documents")
def upload_documents(files: list[UploadFile] = File(...), db: Session = Depends(get_db)) -> list[Document]:
    if not files:
        raise HTTPException(status_code=400, detail="Select at least one PDF file to upload.")

    created: list[Document] = []
    for upload in files:
        filename = safe_filename(upload.filename)
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"{filename} is not a supported PDF.")

        path, stored_name = store_upload(upload)
        page_count, extracted_pages, extraction_error = extract_pdf(path)
        has_text = any(bool(text) for _, text in extracted_pages)
        if extraction_error:
            extraction_status = "failed" if page_count == 0 else "warning"
            message = extraction_error
        elif not has_text:
            extraction_status = "warning"
            message = extraction_message_for("warning", filename)
        else:
            extraction_status = "completed"
            message = None

        document = Document(
            filename=filename,
            stored_filename=stored_name,
            page_count=page_count,
            extracted_page_count=sum(bool(text) for _, text in extracted_pages),
            has_extractable_text=has_text,
            extraction_status=extraction_status,
            extraction_message=message,
        )
        db.add(document)
        db.flush()
        for page_number, text in extracted_pages:
            db.add(PageText(document_id=document.id, page_number=page_number, text=text, character_count=len(text)))
        created.append(document)

    db.commit()
    for document in created:
        db.refresh(document)
    return created


def _document_response(db: Session, document: Document) -> DocumentResponse:
    chunks_count = int(db.scalar(select(func.count()).select_from(Chunk).where(Chunk.document_id == document.id)) or 0)
    faiss_exists, metadata_exists = document_index_exists(document.id)
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        page_count=document.page_count,
        has_extractable_text=document.has_extractable_text,
        extraction_status=document.extraction_status,
        extraction_message=document.extraction_message,
        uploaded_at=document.uploaded_at,
        extracted_page_count=document.extracted_page_count,
        is_indexed=chunks_count > 0 and (faiss_exists or fts_entry_count(db, document.id) > 0),
        chunks_count=chunks_count,
        faiss_index_exists=faiss_exists,
        metadata_exists=metadata_exists,
    )


def _index_one_document(db: Session, document: Document) -> IndexDocumentResponse:
    pages_with_text = int(
        db.scalar(
            select(func.count())
            .select_from(PageText)
            .where(PageText.document_id == document.id, PageText.character_count > 0)
        )
        or 0
    )
    if document.extraction_status != "completed" or not document.has_extractable_text or pages_with_text == 0:
        raise HTTPException(
            status_code=400,
            detail="This document has no searchable text. It may be scanned or image-based.",
        )

    # Stage 2: Proper Cleanup and Re-indexing
    delete_document_chunks(db, document.id)
    remove_document_faiss_files(document.id)
    
    drafts = create_chunk_drafts_for_document(db, document.id)
    if not drafts:
        raise HTTPException(
            status_code=400,
            detail="This document has no searchable chunks. Try a longer readable text-based PDF.",
        )
    
    chunks = save_chunks(db, drafts)
    insert_chunk_fts_entries(db, chunks)
    
    try:
        faiss_created = build_document_faiss_index(document, chunks)
    except ImportError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Semantic indexing dependencies are not installed. Install backend requirements and try again.",
        ) from None
    
    db.commit()
    return IndexDocumentResponse(
        document_id=document.id,
        filename=document.filename,
        status="indexed",
        pages_with_text=pages_with_text,
        chunks_created=len(chunks),
        faiss_index_created=faiss_created,
        keyword_index_created=fts_entry_count(db, document.id) == len(chunks),
        message=f"Indexed {document.filename} with {len(chunks)} chunks.",
    )


@router.post("/index-all", response_model=IndexAllResponse, summary="Index all eligible documents")
def index_all_documents(db: Session = Depends(get_db)) -> IndexAllResponse:
    documents = list(db.scalars(select(Document).order_by(Document.uploaded_at.desc())).all())
    results: list[IndexDocumentResponse] = []
    failures = 0
    for document in documents:
        try:
            results.append(_index_one_document(db, document))
        except HTTPException as exc:
            db.rollback()
            failures += 1
            results.append(
                IndexDocumentResponse(
                    document_id=document.id,
                    filename=document.filename,
                    status="warning",
                    pages_with_text=0,
                    chunks_created=0,
                    faiss_index_created=False,
                    keyword_index_created=False,
                    message=str(exc.detail),
                )
            )
    return IndexAllResponse(
        results=results,
        indexed_document_count=sum(1 for item in results if item.status == "indexed"),
        failed_or_warning_count=failures,
        total_chunks_created=sum(item.chunks_created for item in results),
    )


@router.post("/{document_id}/index", response_model=IndexDocumentResponse, summary="Index a document for keyword and semantic search")
def index_document(document_id: int, db: Session = Depends(get_db)) -> IndexDocumentResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _index_one_document(db, document)


@router.get("", response_model=list[DocumentResponse], summary="List all uploaded documents")
def list_documents(db: Session = Depends(get_db)) -> list[DocumentResponse]:
    documents = list(db.scalars(select(Document).order_by(Document.uploaded_at.desc())).all())
    return [_document_response(db, document) for document in documents]


@router.get("/{document_id}", response_model=DocumentDetailResponse, summary="Get document details by ID")
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return _document_response(db, document)


@router.get("/{document_id}/pages", response_model=list[PageTextResponse], summary="Get extracted pages for a document")
def get_document_pages(document_id: int, include_text: bool = True, db: Session = Depends(get_db)) -> list[PageTextResponse]:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    pages = list(db.scalars(select(PageText).where(PageText.document_id == document_id).order_by(PageText.page_number)).all())
    if include_text:
        return [PageTextResponse.model_validate(page) for page in pages]
    return [PageTextResponse(page_number=page.page_number, character_count=page.character_count, text=None) for page in pages]


@router.delete("/{document_id}", response_model=DeleteDocumentResponse, summary="Delete a document and its extracted text")
def delete_document(document_id: int, db: Session = Depends(get_db)) -> DeleteDocumentResponse:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    
    # Stage 2: Comprehensive Cleanup
    chunks_deleted = fts_deleted = True
    try:
        delete_document_chunks(db, document_id)
    except Exception:
        chunks_deleted = fts_deleted = False
        
    index_cleanup = remove_document_faiss_files(document_id)
    
    file_path = UPLOAD_DIR / document.stored_filename
    file_deleted = False
    if file_path.exists():
        try:
            file_path.unlink()
            file_deleted = True
        except OSError:
            file_deleted = False
            
    db.delete(document)
    db.commit()
    
    return DeleteDocumentResponse(
        message="Document, extracted page text, chunks, and search indexes deleted.",
        document_id=document_id,
        file_deleted=file_deleted,
        chunks_deleted=chunks_deleted,
        keyword_entries_deleted=fts_deleted,
        faiss_index_deleted=index_cleanup["faiss_index_deleted"],
        metadata_deleted=index_cleanup["metadata_deleted"],
    )
