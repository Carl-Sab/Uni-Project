"""Chat session/message persistence.

Message history is stored as plain (role, content) text turns rather than
pydantic-ai's native message format (which would also encode tool calls and
their results). That's a deliberate simplification: a follow-up like "what
about next term?" only needs the previous turns' visible text to resolve -
the tool calls that produced an earlier answer don't need to be replayed
for the model to understand what "next term" refers to. Keeping storage to
plain text also means chat history survives a change in which tools exist
without needing migration.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatSession

HISTORY_TURNS = 10


async def get_or_create_session(
    session: AsyncSession, student_id: str, session_id: int | None
) -> ChatSession | None:
    """Returns None if session_id was given but doesn't belong to
    student_id - the caller must treat that as "not found," never fall
    back to creating a new session (that would silently let a student
    probe for the existence of someone else's session id).
    """
    if session_id is not None:
        chat_session = (
            await session.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id, ChatSession.student_id == student_id
                )
            )
        ).scalar_one_or_none()
        return chat_session

    now = datetime.now(timezone.utc)
    chat_session = ChatSession(student_id=student_id, created_at=now, updated_at=now)
    session.add(chat_session)
    await session.flush()
    return chat_session


async def save_message(session: AsyncSession, session_id: int, role: str, content: str) -> None:
    session.add(
        ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
    )
    chat_session = await session.get(ChatSession, session_id)
    chat_session.updated_at = datetime.now(timezone.utc)


async def get_recent_messages(session: AsyncSession, session_id: int) -> list[ChatMessage]:
    """Last HISTORY_TURNS user/assistant turns (up to 2*HISTORY_TURNS
    messages), oldest first - ready to hand to the model as history.
    """
    rows = (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.desc())
            .limit(HISTORY_TURNS * 2)
        )
    ).scalars().all()
    return list(reversed(rows))


def to_model_message_history(messages: list[ChatMessage]) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for m in messages:
        if m.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=m.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=m.content)]))
    return history


@dataclass(frozen=True)
class SessionSummary:
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


async def list_sessions(session: AsyncSession, student_id: str) -> list[SessionSummary]:
    sessions = (
        await session.execute(
            select(ChatSession)
            .where(ChatSession.student_id == student_id)
            .order_by(ChatSession.updated_at.desc())
        )
    ).scalars().all()

    summaries = []
    for cs in sessions:
        first_user_message = (
            await session.execute(
                select(ChatMessage.content)
                .where(ChatMessage.session_id == cs.id, ChatMessage.role == "user")
                .order_by(ChatMessage.id.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        title = (first_user_message or "New conversation")[:80]
        summaries.append(
            SessionSummary(id=cs.id, title=title, created_at=cs.created_at, updated_at=cs.updated_at)
        )
    return summaries


async def get_session_messages(
    session: AsyncSession, student_id: str, session_id: int
) -> list[ChatMessage] | None:
    """None means the session doesn't exist or doesn't belong to this
    student - the route must turn that into a 404, not a 403, so a student
    probing session ids learns nothing about which ids are valid for
    someone else.
    """
    chat_session = (
        await session.execute(
            select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.student_id == student_id
            )
        )
    ).scalar_one_or_none()
    if chat_session is None:
        return None

    return (
        await session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.id.asc())
        )
    ).scalars().all()
