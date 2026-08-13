"""Idempotent loader for data/Eurisko_University_Data.xlsx.

Usage: uv run python -m app.scripts.load_data

Safe to re-run: every table is populated with an upsert keyed on its primary
key, so re-running against the same source file never duplicates rows and
simply refreshes values if the source changes.
"""

import asyncio
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.db import async_session, engine
from app.models import (
    CategoryCourse,
    ClassSchedule,
    Course,
    CoursePrerequisite,
    Enrollment,
    GradingScale,
    Program,
    RequirementCategory,
    Student,
    Term,
)

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "Eurisko_University_Data.xlsx"

_SEASON_RANK = {"SP": 1, "SU": 2, "FA": 3}


def _term_sort_order(term_code: str) -> int:
    """year * 10 + season rank, so chronological order doesn't depend on
    string comparison ("FA2023" < "SP2024" is false as a string)."""
    season, year = term_code[:2], int(term_code[2:])
    return year * 10 + _SEASON_RANK[season]


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")


async def _upsert(session, model, rows: list[dict], pk_cols: list[str]) -> None:
    if not rows:
        return
    stmt = insert(model).values(rows)
    update_cols = {c: getattr(stmt.excluded, c) for c in rows[0] if c not in pk_cols}
    if update_cols:
        stmt = stmt.on_conflict_do_update(index_elements=pk_cols, set_=update_cols)
    else:
        # Pure junction row (only PK columns) - nothing to refresh on conflict.
        stmt = stmt.on_conflict_do_nothing(index_elements=pk_cols)
    await session.execute(stmt)


async def load() -> None:
    xl = pd.ExcelFile(DATA_PATH)

    terms_df = xl.parse("Terms")
    terms_df["sort_order"] = terms_df["term_code"].map(_term_sort_order)
    terms_df["start_date"] = pd.to_datetime(terms_df["start_date"]).dt.date
    terms_df["end_date"] = pd.to_datetime(terms_df["end_date"]).dt.date

    programs_df = xl.parse("Program_Requirements")[
        ["program_code", "program_name", "total_credits_required"]
    ].drop_duplicates(subset="program_code")

    categories_df = xl.parse("Program_Requirements")[
        ["category_id", "program_code", "category_name", "credits_required"]
    ].drop_duplicates(subset="category_id")

    courses_df = xl.parse("Courses")
    category_courses_df = xl.parse("Category_Courses")
    prereqs_df = xl.parse("Course_Prerequisites")

    grading_df = xl.parse("Grading_Scale")
    for col in ("earns_credit", "included_in_gpa"):
        grading_df[col] = grading_df[col] == "Yes"

    students_df = xl.parse("Students")
    enrollments_df = xl.parse("Enrollments")
    schedule_df = xl.parse("Class_Schedule_FA2026")[
        ["course_code", "days", "start_time", "end_time", "room", "instructor"]
    ].copy()
    schedule_df["term_code"] = "FA2026"
    schedule_df["start_time"] = pd.to_datetime(schedule_df["start_time"], format="%H:%M").dt.time
    schedule_df["end_time"] = pd.to_datetime(schedule_df["end_time"], format="%H:%M").dt.time

    async with async_session() as session:
        async with session.begin():
            await _upsert(session, Term, _records(terms_df), ["term_code"])
            await _upsert(session, Program, _records(programs_df), ["program_code"])
            await _upsert(
                session, RequirementCategory, _records(categories_df), ["category_id"]
            )
            await _upsert(session, Course, _records(courses_df), ["course_code"])
            await _upsert(session, GradingScale, _records(grading_df), ["grade"])
            await _upsert(session, Student, _records(students_df), ["student_id"])

            await _upsert(
                session,
                CategoryCourse,
                _records(category_courses_df),
                ["category_id", "course_code"],
            )
            await _upsert(
                session,
                CoursePrerequisite,
                _records(prereqs_df),
                ["course_code", "prerequisite_course_code"],
            )
            await _upsert(
                session,
                Enrollment,
                _records(enrollments_df),
                ["student_id", "term_code", "course_code"],
            )

            # class_schedule has a surrogate PK; upsert on the real natural
            # key (term_code, course_code) instead.
            await _upsert(
                session,
                ClassSchedule,
                _records(schedule_df),
                ["term_code", "course_code"],
            )

    await engine.dispose()
    print("Load complete.")


def main() -> None:
    asyncio.run(load())


if __name__ == "__main__":
    main()
