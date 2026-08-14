"""Ingest the two source PDFs in data/ into documents/doc_chunks.

Usage: uv run python -m app.scripts.ingest_documents

Safe to run on every container boot (see docker-entrypoint.sh): skips a
document entirely if it's already indexed with a matching checksum, so a
plain `docker compose up` restart doesn't re-run embeddings (a real cost,
not just time) for content that hasn't changed.
"""

import asyncio
from pathlib import Path

from sqlalchemy import select

from app.db import async_session, engine
from app.models import Document
from app.services.ingestion import _checksum, ingest_document

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

DOCUMENTS = [
    ("Eurisko_University_Student_Handbook_2026-2027.pdf", "handbook"),
    ("Eurisko_University_Course_Catalogue_2026-2027.pdf", "catalogue"),
]


async def _already_indexed(filename: str, path: Path) -> bool:
    checksum = _checksum(path)
    async with async_session() as session:
        doc = (
            await session.execute(select(Document).where(Document.filename == filename))
        ).scalar_one_or_none()
    return doc is not None and doc.status == "indexed" and doc.checksum == checksum


async def main() -> None:
    for filename, doc_type in DOCUMENTS:
        path = DATA_DIR / filename
        if await _already_indexed(filename, path):
            print(f"Skipping {filename} - already indexed, checksum unchanged.")
            continue
        print(f"Ingesting {filename} ({doc_type}) ...")
        document_id = await ingest_document(filename, str(path), doc_type)
        print(f"  -> document_id={document_id}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
