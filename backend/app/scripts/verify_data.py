"""Verification script: prints total credits earned, cumulative GPA, and
credits per requirement category for every student.

Usage: uv run python -m app.scripts.verify_data

All computation lives in app.services.academic - this script is a thin
console report over that shared module, so it can never drift from what the
API returns.
"""

import asyncio

from sqlalchemy import select

from app.db import async_session, engine
from app.models import Student
from app.services.academic import (
    compute_category_progress,
    compute_gpa,
    compute_total_credits_earned,
    get_best_attempts,
)


async def verify() -> None:
    async with async_session() as session:
        students = (
            await session.execute(select(Student).order_by(Student.student_id))
        ).scalars().all()

        for student in students:
            best_attempts = await get_best_attempts(session, student.student_id)
            gpa = compute_gpa(best_attempts)
            total_credits = compute_total_credits_earned(best_attempts)
            categories = await compute_category_progress(session, student)

            print(f"{student.student_id} - {student.first_name} {student.last_name} ({student.program_code})")
            print(f"  Total credits earned: {total_credits}")
            print(f"  Cumulative GPA: {gpa if gpa is not None else 'N/A (no graded courses)'}")
            print("  Credits per requirement category:")
            for cat in categories:
                print(f"    {cat.category_name}: {cat.credits_earned}/{cat.credits_required}")
            print()

    await engine.dispose()


def main() -> None:
    asyncio.run(verify())


if __name__ == "__main__":
    main()
