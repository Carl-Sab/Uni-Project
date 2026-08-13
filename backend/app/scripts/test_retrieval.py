"""Inspect hybrid retrieval quality directly, before any agent touches it.

Usage: uv run python -m app.scripts.test_retrieval "query text"
"""

import asyncio
import sys

from app.db import async_session, engine
from app.services.retrieval import hybrid_search


async def run(query: str) -> None:
    async with async_session() as session:
        results = await hybrid_search(session, query)

    print(f'\nQuery: "{query}"')
    print("=" * 100)
    if not results:
        print("  (no results)")
    for rank, r in enumerate(results, start=1):
        location = f"{r.filename} p.{r.page}"
        if r.section_number:
            location += f" §{r.section_number}"
        if r.section_title:
            location += f" ({r.section_title})"
        print(f"\n[{rank}] score={r.score:.5f}  {location}")
        for line in r.content.split("\n"):
            print(f"    {line}")
    print()

    await engine.dispose()


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: uv run python -m app.scripts.test_retrieval "query"')
        raise SystemExit(1)
    query = " ".join(sys.argv[1:])
    asyncio.run(run(query))


if __name__ == "__main__":
    main()
