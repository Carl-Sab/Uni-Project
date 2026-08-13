"""CLI for testing the assistant without a frontend.

Usage:
    uv run python -m app.scripts.chat <student_id> "<question>"
    uv run python -m app.scripts.chat <student_id> "<question>" --session <id>

Prints which tools were called during the turn, then the final answer.
Without --session a new chat session is created and its id is printed so a
follow-up question can be sent in the same session with --session <id> -
this is how a "what about next term?"-style follow-up is tested from the
CLI without a frontend.
"""

import asyncio
import io
import sys

# Windows terminals often default stdout to cp1252, which can't encode
# emoji or the section-sign character (§) the assistant's citations use.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from app.agent import AgentDeps, agent, build_agent_model, build_system_prompt
from app.db import async_session, engine
from app.models import AssistantConfig
from app.services.chat import get_or_create_session, get_recent_messages, save_message, to_model_message_history


async def run(student_id: str, question: str, session_id: int | None) -> None:
    async with async_session() as db_session:
        chat_session = await get_or_create_session(db_session, student_id, session_id)
        if chat_session is None:
            print(f"No such session {session_id} for student {student_id}")
            return

        config = await db_session.get(AssistantConfig, 1)
        history_messages = await get_recent_messages(db_session, chat_session.id)
        message_history = to_model_message_history(history_messages)

        deps = AgentDeps(student_id=student_id, session=db_session, config=config)
        model = build_agent_model(config)

        result = await agent.run(
            question,
            deps=deps,
            model=model,
            message_history=message_history,
            instructions=build_system_prompt(config),
            model_settings={"temperature": float(config.temperature)},
        )

        tools_called = [
            part.tool_name
            for message in result.new_messages()
            for part in message.parts
            if part.part_kind == "tool-call"
        ]

        await save_message(db_session, chat_session.id, "user", question)
        await save_message(db_session, chat_session.id, "assistant", result.output)
        await db_session.commit()

        print(f"session_id: {chat_session.id}")
        print(f"tools called: {tools_called or '(none)'}")
        print()
        print(result.output)

    await engine.dispose()


def main() -> None:
    args = sys.argv[1:]
    session_id = None
    if "--session" in args:
        idx = args.index("--session")
        session_id = int(args[idx + 1])
        del args[idx : idx + 2]

    if len(args) < 2:
        print('Usage: uv run python -m app.scripts.chat <student_id> "<question>" [--session <id>]')
        raise SystemExit(1)

    student_id, question = args[0], args[1]
    asyncio.run(run(student_id, question, session_id))


if __name__ == "__main__":
    main()
