"""Chat endpoints. POST /api/chat streams via SSE; GET /api/me/chats* let a
student revisit past conversations. Every route here is scoped by
get_current_student - see app/auth.py and app/agent.py for why no route
anywhere accepts a student_id or another student's session_id from the
client.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.agent import AgentDeps, agent, build_agent_model, build_system_prompt
from app.auth import get_current_student
from app.db import async_session, get_db
from app.models import AssistantConfig
from app.schemas import (
    AppointmentApprovalResponse,
    AppointmentResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatSessionSummary,
)
from app.services.appointments import approve_appointment, list_appointments
from app.services.chat import (
    get_or_create_session,
    get_recent_messages,
    get_session_messages,
    list_sessions,
    save_message,
    to_model_message_history,
)

router = APIRouter(tags=["chat"])


@router.post("/api/chat")
async def chat(
    body: ChatRequest, student_id: str = Depends(get_current_student)
) -> EventSourceResponse:
    async def event_stream():
        # A DB session opened here (not via FastAPI's Depends) so it stays
        # alive for the full duration of the stream - EventSourceResponse
        # iterates this generator after the route handler has already
        # returned, by which point a request-scoped Depends(get_db) session
        # would already be closed.
        async with async_session() as db_session:
            chat_session = await get_or_create_session(db_session, student_id, body.session_id)
            if chat_session is None:
                yield {
                    "event": "error",
                    "data": json.dumps({"detail": "Session not found"}),
                }
                return

            config = await db_session.get(AssistantConfig, 1)
            history_messages = await get_recent_messages(db_session, chat_session.id)
            message_history = to_model_message_history(history_messages)

            deps = AgentDeps(student_id=student_id, session=db_session, config=config)
            model = build_agent_model(config)

            collected_text: list[str] = []

            def emit_text(chunk: str, *, is_new_part: bool):
                """A single logical answer is streamed across MULTIPLE
                separate TextParts whenever a tool call interrupts it (the
                pre-tool-call narration - "I'll check your schedule..." -
                and the post-tool-call answer are different parts, possibly
                from different model responses entirely). Nothing
                guarantees the model leaves a trailing space at the end of
                one part or a leading space at the start of the next, so a
                naive "".join can glue "...student may" directly onto
                "not register..." into "maynot". Insert a boundary space
                whenever a NEW part starts and neither side already has
                whitespace there.
                """
                nonlocal collected_text
                if (
                    is_new_part
                    and collected_text
                    and chunk
                    and not collected_text[-1][-1:].isspace()
                    and not chunk[:1].isspace()
                ):
                    chunk = " " + chunk
                if not chunk:
                    return
                collected_text.append(chunk)
                return chunk

            async with agent.run_stream_events(
                body.message,
                deps=deps,
                model=model,
                message_history=message_history,
                instructions=build_system_prompt(config),
                model_settings={"temperature": float(config.temperature)},
            ) as events:
                async for event in events:
                    if isinstance(event, FunctionToolCallEvent):
                        yield {
                            "event": "tool_call",
                            "data": json.dumps({"tool": event.part.tool_name, "args": event.part.args_as_dict()}),
                        }
                    elif isinstance(event, FunctionToolResultEvent):
                        # Tool return values are already JSON-serializable
                        # dicts/lists (see app/agent.py's _jsonable helper).
                        # The frontend needs the actual content - not just
                        # the tool name - to render e.g. an appointment
                        # proposal's id/reason/time as an approval card.
                        yield {
                            "event": "tool_result",
                            "data": json.dumps({"tool": event.part.tool_name, "content": event.part.content}),
                        }
                    elif isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
                        # A new text part's initial content arrives here,
                        # not through PartDeltaEvent - missing this drops
                        # the first chunk of every text part (e.g. "I'll"
                        # in "I'll check your degree progress...").
                        emitted = emit_text(event.part.content, is_new_part=True)
                        if emitted:
                            yield {"event": "text_delta", "data": json.dumps({"content": emitted})}
                    elif isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
                        emitted = emit_text(event.delta.content_delta, is_new_part=False)
                        if emitted:
                            yield {"event": "text_delta", "data": json.dumps({"content": emitted})}

            final_text = "".join(collected_text)
            await save_message(db_session, chat_session.id, "user", body.message)
            await save_message(db_session, chat_session.id, "assistant", final_text)
            await db_session.commit()

            yield {
                "event": "done",
                "data": json.dumps({"session_id": chat_session.id}),
            }

    # ping=2: the tool-call + LLM-thinking phase before the first
    # text_delta can easily take 5-10s with zero bytes sent otherwise -
    # long enough to trip Node/Vite dev server's default 5s keep-alive
    # socket timeout in front of this (observed in testing: the browser's
    # fetch was silently aborted mid-stream on every request that took
    # longer than ~5s to produce a first byte). A ping every 2s keeps the
    # connection visibly alive well within that window.
    return EventSourceResponse(event_stream(), ping=2)


@router.get("/api/me/chats", response_model=list[ChatSessionSummary])
async def get_chats(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[ChatSessionSummary]:
    summaries = await list_sessions(session, student_id)
    return [ChatSessionSummary(**vars(s)) for s in summaries]


@router.get("/api/me/chats/{session_id}", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    session_id: int,
    student_id: str = Depends(get_current_student),
    session: AsyncSession = Depends(get_db),
) -> list[ChatMessageResponse]:
    messages = await get_session_messages(session, student_id, session_id)
    if messages is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return [
        ChatMessageResponse(role=m.role, content=m.content, created_at=m.created_at) for m in messages
    ]


@router.get("/api/me/appointments", response_model=list[AppointmentResponse])
async def get_appointments(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[AppointmentResponse]:
    appointments = await list_appointments(session, student_id)
    return [
        AppointmentResponse(
            id=a.id, status=a.status, reason=a.reason, preferred_time=a.preferred_time,
            created_at=a.created_at,
        )
        for a in appointments
    ]


@router.post("/api/me/appointments/{appointment_id}/approve", response_model=AppointmentApprovalResponse)
async def approve_appointment_route(
    appointment_id: int,
    student_id: str = Depends(get_current_student),
    session: AsyncSession = Depends(get_db),
) -> AppointmentApprovalResponse:
    appointment = await approve_appointment(session, student_id, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    await session.commit()
    return AppointmentApprovalResponse(
        id=appointment.id,
        status=appointment.status,
        reason=appointment.reason,
        preferred_time=appointment.preferred_time,
    )
