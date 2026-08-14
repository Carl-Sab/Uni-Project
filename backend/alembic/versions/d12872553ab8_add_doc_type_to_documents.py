"""add doc_type to documents

Revision ID: d12872553ab8
Revises: b01cdf4fa1fe
Create Date: 2026-08-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd12872553ab8'
down_revision: Union[str, Sequence[str], None] = 'b01cdf4fa1fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("documents", sa.Column("doc_type", sa.String(20), nullable=True))
    # Backfill the two seed documents from the existing chunks they already
    # produced - every chunk from a given document was tagged with the same
    # doc_type at ingestion time (see app/services/chunking.py).
    op.execute(
        """
        UPDATE documents d
        SET doc_type = sub.doc_type
        FROM (
            SELECT DISTINCT ON (document_id) document_id, doc_type
            FROM doc_chunks
            ORDER BY document_id, id
        ) sub
        WHERE d.id = sub.document_id
        """
    )
    # Any document with no chunks yet (never successfully indexed) has no
    # doc_type to infer - default it to "handbook" so the column can go
    # NOT NULL; an admin re-uploading picks the real type going forward.
    op.execute("UPDATE documents SET doc_type = 'handbook' WHERE doc_type IS NULL")
    op.alter_column("documents", "doc_type", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("documents", "doc_type")
