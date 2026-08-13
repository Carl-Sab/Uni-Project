"""Verification script: prints total credits earned, cumulative GPA, and
credits per requirement category for every student.

Usage: uv run python -m app.scripts.verify_data

Handbook: data/Eurisko_University_Student_Handbook_2026-2027.pdf
"""

import asyncio
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select

from app.db import async_session, engine
from app.models import (
    CategoryCourse,
    Enrollment,
    GradingScale,
    RequirementCategory,
    Student,
)


def dedupe_best_attempts(rows: list[tuple]) -> list[dict]:
    """One row per course_code: the completed attempt with the higher
    grade_points, per Handbook 1.5 - "Both attempts stay on the transcript,
    but only the higher grade counts toward the GPA. Credit for a course is
    earned once only, however many times it is taken."

    `rows` must already be restricted to status == "Completed": an
    "In progress" enrollment has no grade yet and cannot contribute to GPA
    or credit.

    Pure function (no I/O) so the dedup rule can be unit tested directly
    against a synthetic pair of attempts, independent of what the current
    dataset happens to contain.
    """
    best: dict[str, dict] = {}
    for course_code, credits, grade, grade_points, earns_credit, included_in_gpa in rows:
        # grade_points arrives from a NUMERIC(3,1) column, decoded by the
        # driver as Decimal already; str()-round-tripping here is a safety
        # net so a float can never sneak into the GPA arithmetic even if
        # that decoding behaviour changes.
        candidate = {
            "credits": credits,
            "grade": grade,
            "grade_points": Decimal(str(grade_points)) if grade_points is not None else None,
            "earns_credit": earns_credit,
            "included_in_gpa": included_in_gpa,
        }
        current = best.get(course_code)
        # NaN/None grade_points (W, P) sort below any numeric grade.
        if current is None or (
            candidate["grade_points"] is not None
            and (
                current["grade_points"] is None
                or candidate["grade_points"] > current["grade_points"]
            )
        ):
            best[course_code] = candidate
    return [{"course_code": cc, **v} for cc, v in best.items()]


async def _best_attempt_per_course(session, student_id: str) -> list[dict]:
    rows = (
        await session.execute(
            select(
                Enrollment.course_code,
                Enrollment.credits,
                Enrollment.grade,
                GradingScale.grade_points,
                GradingScale.earns_credit,
                GradingScale.included_in_gpa,
            )
            .join(GradingScale, GradingScale.grade == Enrollment.grade, isouter=True)
            .where(
                Enrollment.student_id == student_id,
                Enrollment.status == "Completed",
            )
        )
    ).all()
    return dedupe_best_attempts(rows)


def _gpa(best_attempts: list[dict]) -> Decimal | None:
    # Handbook 1.2: GPA = sum(grade_points * credits) / sum(credits attempted
    # in graded courses). Courses carrying W or P are excluded from both the
    # numerator and the denominator. Reported to two decimal places, not
    # rounded upward (i.e. truncated).
    numerator = Decimal("0")
    denominator = Decimal("0")
    for a in best_attempts:
        if not a["included_in_gpa"]:
            continue
        numerator += a["grade_points"] * Decimal(a["credits"])
        denominator += Decimal(a["credits"])

    if denominator == 0:
        return None  # no graded courses yet - avoid division by zero

    gpa = numerator / denominator
    return gpa.quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def _total_credits_earned(best_attempts: list[dict]) -> int:
    # Handbook 1.3 / 1.5: a grade of D or above (or P) earns credit; credit
    # for a course is earned once only, however many times it is taken -
    # already guaranteed by best_attempts being deduplicated per course.
    return sum(a["credits"] for a in best_attempts if a["earns_credit"])


async def _credits_per_category(session, student: Student, best_attempts: list[dict]) -> list[tuple[str, int, int]]:
    earned_courses = {a["course_code"] for a in best_attempts if a["earns_credit"]}

    categories = (
        await session.execute(
            select(RequirementCategory)
            .where(RequirementCategory.program_code == student.program_code)
            .order_by(RequirementCategory.category_id)
        )
    ).scalars().all()

    result = []
    for cat in categories:
        cat_courses = (
            await session.execute(
                select(CategoryCourse.course_code).where(
                    CategoryCourse.category_id == cat.category_id
                )
            )
        ).scalars().all()
        earned_in_category = sum(
            a["credits"]
            for a in best_attempts
            if a["course_code"] in earned_courses and a["course_code"] in cat_courses
        )
        result.append((cat.category_name, earned_in_category, cat.credits_required))
    return result


async def verify() -> None:
    async with async_session() as session:
        students = (
            await session.execute(select(Student).order_by(Student.student_id))
        ).scalars().all()

        for student in students:
            best_attempts = await _best_attempt_per_course(session, student.student_id)
            gpa = _gpa(best_attempts)
            total_credits = _total_credits_earned(best_attempts)
            categories = await _credits_per_category(session, student, best_attempts)

            print(f"{student.student_id} - {student.first_name} {student.last_name} ({student.program_code})")
            print(f"  Total credits earned: {total_credits}")
            print(f"  Cumulative GPA: {gpa if gpa is not None else 'N/A (no graded courses)'}")
            print("  Credits per requirement category:")
            for name, earned, required in categories:
                print(f"    {name}: {earned}/{required}")
            print()

    await engine.dispose()


def main() -> None:
    asyncio.run(verify())


if __name__ == "__main__":
    main()
