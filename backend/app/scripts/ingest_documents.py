"""Ingest the two source PDFs in data/ into documents/doc_chunks.

Usage: uv run python -m app.scripts.ingest_documents
"""

import asyncio
from pathlib import Path

from app.db import engine
from app.services.ingestion import ingest_document

DATA_DIR = Path(__file__).resolve().parents[3] / "data"

DOCUMENTS = [
    ("Eurisko_University_Student_Handbook_2026-2027.pdf", "handbook"),
    ("Eurisko_University_Course_Catalogue_2026-2027.pdf", "catalogue"),
]


async def main() -> None:
    for filename, doc_type in DOCUMENTS:
        path = DATA_DIR / filename
        print(f"Ingesting {filename} ({doc_type}) ...")
        document_id = await ingest_document(filename, str(path), doc_type)
        print(f"  -> document_id={document_id}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
