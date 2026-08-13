"""documents and doc_chunks

Revision ID: b337a8eac4da
Revises: 15b11f4213a1
Create Date: 2026-08-13 21:52:21.801610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'b337a8eac4da'
down_revision: Union[str, Sequence[str], None] = '15b11f4213a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    """Upgrade schema."""
    # Already created by postgres-init/01-init-extensions.sql on first
    # container start, but idempotent here too so this migration is
    # self-contained against any Postgres that already has pgvector
    # available.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(64), nullable=False),
    )

    op.create_table(
        "doc_chunks",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("section_number", sa.String(50), nullable=True),
        sa.Column("section_title", sa.String(300), nullable=True),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("tsv", postgresql.TSVECTOR, nullable=False),
    )
    op.create_index("ix_doc_chunks_document_id", "doc_chunks", ["document_id"])
    op.execute(
        "CREATE INDEX ix_doc_chunks_embedding_ivfflat ON doc_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute("CREATE INDEX ix_doc_chunks_tsv_gin ON doc_chunks USING gin (tsv)")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_doc_chunks_tsv_gin", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_embedding_ivfflat", table_name="doc_chunks")
    op.drop_index("ix_doc_chunks_document_id", table_name="doc_chunks")
    op.drop_table("doc_chunks")
    op.drop_table("documents")
