"""Document ingestion: parse -> chunk -> embed -> store.

Designed to run as a background task: `start_ingestion` creates the
`documents` row (or reuses an existing one for the same filename) and
returns immediately with its id and status="pending", scheduling the actual
parse/embed/store work as an asyncio task. An admin polls GET
/api/admin/documents/{id} (admin panel, not built in this pass) to watch
status move pending -> indexing -> indexed | failed.

Re-ingesting: `_replace_chunks` deletes the document's old chunks and
inserts the new ones inside one transaction, so a reader never observes a
half-updated document (all-old, all-new, never a mix). Deleting a document
outright cascades to its chunks via the doc_chunks.document_id FK's
ON DELETE CASCADE (see the b337a8eac4da migration) - the row disappearing
from `documents` is enough to make it disappear from retrieval entirely,
no separate chunk cleanup needed.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

# Where admin-uploaded PDFs land, named "{document_id}_{original filename}"
# so a re-index can find the file again from the documents row alone -
# nothing else needs to remember where an upload was written.
UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session
from app.models import DocChunk, Document
from app.services.chunking import chunk_units
from app.services.concatenation_check import check_chunks_for_concatenation
from app.services.embeddings import embed_texts
from app.services.pdf_parsing import parse_catalogue, parse_handbook
from app.services.retrieval import flush_retrieval_cache

logger = logging.getLogger(__name__)

PARSERS = {
    "handbook": parse_handbook,
    "catalogue": parse_catalogue,
}


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def _get_or_create_document(
    session: AsyncSession, filename: str, doc_type: str, checksum: str
) -> Document:
    existing = (
        await session.execute(select(Document).where(Document.filename == filename))
    ).scalar_one_or_none()
    if existing is not None:
        existing.checksum = checksum
        existing.doc_type = doc_type
        existing.status = "pending"
        existing.uploaded_at = datetime.now(timezone.utc)
        return existing

    doc = Document(
        filename=filename,
        doc_type=doc_type,
        uploaded_at=datetime.now(timezone.utc),
        indexed_at=None,
        status="pending",
        chunk_count=0,
        checksum=checksum,
    )
    session.add(doc)
    await session.flush()
    return doc


async def _replace_chunks(session: AsyncSession, document_id: int, doc_type: str, path: str) -> int:
    parser = PARSERS[doc_type]
    units = parser(path)
    chunks = chunk_units(units, doc_type)

    # Surface a word-joining regression here, at ingestion, rather than
    # letting it reach a chat answer and its citations. This never blocks
    # ingestion - it's a heuristic with a known false-positive rate (real
    # compound words like "outstanding" get flagged too) - just logged
    # loudly enough that a real regression (e.g. "maynot", "youmay") stands
    # out against the noise.
    warnings = check_chunks_for_concatenation([c.content for c in chunks])
    for w in warnings:
        logger.warning(
            "possible missing-space concatenation in %s (%s): %r  context: %r",
            path,
            w.kind,
            w.token,
            w.context,
        )

    embeddings = await embed_texts([c.content for c in chunks])

    async with session.begin():
        await session.execute(delete(DocChunk).where(DocChunk.document_id == document_id))
        for chunk, embedding in zip(chunks, embeddings):
            session.add(
                DocChunk(
                    document_id=document_id,
                    content=chunk.content,
                    page=chunk.page,
                    section_number=chunk.section_number,
                    section_title=chunk.section_title,
                    doc_type=chunk.doc_type,
                    embedding=embedding,
                    tsv=func.to_tsvector("english", chunk.content),
                )
            )
    return len(chunks)


async def ingest_document(filename: str, path: str, doc_type: str) -> int:
    """Runs the full pipeline for one document and returns its document_id.
    Safe to call directly (e.g. from a script) or schedule as a background
    task (see start_ingestion) - it opens its own session rather than
    borrowing a request-scoped one, since a background task must outlive
    the request that triggered it.
    """
    checksum = _checksum(Path(path))

    async with async_session() as session:
        async with session.begin():
            doc = await _get_or_create_document(session, filename, doc_type, checksum)
            document_id = doc.id
            doc.status = "indexing"

    try:
        async with async_session() as session:
            chunk_count = await _replace_chunks(session, document_id, doc_type, path)
    except Exception:
        async with async_session() as session:
            async with session.begin():
                doc = await session.get(Document, document_id)
                doc.status = "failed"
        raise

    async with async_session() as session:
        async with session.begin():
            doc = await session.get(Document, document_id)
            doc.status = "indexed"
            doc.chunk_count = chunk_count
            doc.indexed_at = datetime.now(timezone.utc)

    # Covers both upload and re-index (reindex_document calls this same
    # function) - the chunk set just changed, so every cached retrieval
    # result is potentially stale.
    await flush_retrieval_cache()

    return document_id


def start_ingestion(filename: str, path: str, doc_type: str) -> "asyncio.Task[int]":
    """Fire-and-forget entry point for an admin route: create/mark the
    document row, then run parsing/embedding/storage in the background so
    the request returns immediately with a pollable status.
    """
    return asyncio.create_task(ingest_document(filename, path, doc_type))


async def delete_document(document_id: int) -> None:
    async with async_session() as session:
        async with session.begin():
            doc = await session.get(Document, document_id)
            filename = doc.filename if doc is not None else None
            if doc is not None:
                await session.delete(doc)  # cascades to doc_chunks in the DB

    if filename is not None:
        upload_path = upload_path_for(filename)
        if upload_path.exists():
            upload_path.unlink()
        await flush_retrieval_cache()


def upload_path_for(filename: str) -> Path:
    # Keyed by filename, not document_id: the document row's id doesn't
    # exist yet at the moment a fresh upload is first written to disk (the
    # row and the file are created in that order), and ingestion's own
    # find-or-create-by-filename dedup (_get_or_create_document) already
    # treats filename as the unique key, so reusing it here avoids a
    # chicken-and-egg id dependency for no benefit.
    return UPLOADS_DIR / filename


async def reindex_document(document_id: int) -> None:
    """Re-run the pipeline for a document already on disk under
    UPLOADS_DIR, using its previously recorded doc_type.
    """
    async with async_session() as session:
        doc = await session.get(Document, document_id)
        if doc is None:
            raise ValueError(f"No document with id {document_id}")
        filename, doc_type = doc.filename, doc.doc_type

    path = upload_path_for(filename)
    if not path.exists():
        raise FileNotFoundError(f"Uploaded file for document {document_id} not found at {path}")

    await ingest_document(filename, str(path), doc_type)


def start_reindex(document_id: int) -> "asyncio.Task[None]":
    return asyncio.create_task(reindex_document(document_id))
