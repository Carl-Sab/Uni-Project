"""assistant config, appointments, chat sessions and messages

Revision ID: b01cdf4fa1fe
Revises: b337a8eac4da
Create Date: 2026-08-13 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b01cdf4fa1fe'
down_revision: Union[str, Sequence[str], None] = 'b337a8eac4da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "assistant_config",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("persona", sa.Text, nullable=False),
        sa.Column("model_provider", sa.String(20), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("response_length", sa.String(20), nullable=False),
        sa.Column("temperature", sa.Numeric(2, 1), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Seed the single row (id=1) with sensible defaults - Claude Sonnet 4.5,
    # a friendly persona, detailed responses. An admin edits this row in
    # place; nothing ever inserts a second one.
    op.execute(
        """
        INSERT INTO assistant_config (id, persona, model_provider, model_name, response_length, temperature, updated_at)
        VALUES (1, 'friendly and encouraging, but precise about policy', 'anthropic', 'claude-sonnet-4-5', 'detailed', 0.3, now())
        """
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "student_id", sa.String(20), sa.ForeignKey("students.student_id"), nullable=False
        ),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("preferred_time", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_appointments_student_id", "appointments", ["student_id"])

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "student_id", sa.String(20), sa.ForeignKey("students.student_id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_sessions_student_id", "chat_sessions", ["student_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_student_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_index("ix_appointments_student_id", table_name="appointments")
    op.drop_table("appointments")
    op.drop_table("assistant_config")
