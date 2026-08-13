"""Integration tests against the real loaded dataset (all five students).

Requires postgres to be up and loaded:
    docker compose up -d postgres redis
    uv run python -m app.scripts.load_data

Expected GPA/credit figures were hand-checked against the raw spreadsheet
in the same session that built app/services/academic.py (see conversation
history / README) - these tests pin those figures so a regression in the
shared service module is caught immediately.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db import async_session
from app.models import Student
from app.services.academic import (
    check_course_eligibility,
    compute_category_progress,
    compute_gpa,
    compute_total_credits_earned,
    get_best_attempts,
)

EXPECTED = {
    "S2023011": {"credits": 66, "gpa": Decimal("3.61")},  # Maya
    "S2023027": {"credits": 55, "gpa": Decimal("2.78")},  # Jad
    "S2024019": {"credits": 49, "gpa": Decimal("2.95")},  # Karim
    "S2025008": {"credits": 19, "gpa": Decimal("1.65")},  # Rania
    "S2026042": {"credits": 0, "gpa": None},  # Lynn
}


@pytest.fixture
async def session():
    async with async_session() as s:
        yield s


@pytest.mark.parametrize("student_id", list(EXPECTED.keys()))
async def test_gpa_and_credits_match_hand_check(session, student_id):
    attempts = await get_best_attempts(session, student_id)
    gpa = compute_gpa(attempts)
    credits = compute_total_credits_earned(attempts)

    assert credits == EXPECTED[student_id]["credits"]
    assert gpa == EXPECTED[student_id]["gpa"]


async def test_lynn_has_no_completed_courses_and_does_not_divide_by_zero(session):
    student = await session.get(Student, "S2026042")
    attempts = await get_best_attempts(session, "S2026042")

    assert attempts == []
    assert compute_gpa(attempts) is None
    assert compute_total_credits_earned(attempts) == 0

    categories = await compute_category_progress(session, student)
    assert len(categories) == 5
    for cat in categories:
        assert cat.credits_earned == 0
        assert cat.credits_remaining == cat.credits_required


async def test_lynn_degree_progress_all_categories_present(session):
    student = await session.get(Student, "S2026042")
    categories = await compute_category_progress(session, student)
    names = {c.category_name for c in categories}
    assert names == {
        "Engineering Core",
        "General Education",
        "Computer Engineering Major Core",
        "Professional Practice and Capstone",
        "Technical Electives",
    }


# --- Rania: failed PHYS 101 and MATH 102, currently retaking both (in
# progress). Handbook 2.2: prerequisites require C- or above; an in-progress
# retake has no grade yet and cannot satisfy anything.


async def test_rania_not_eligible_for_course_requiring_failed_phys101(session):
    # PHYS 102 requires PHYS 101
    result = await check_course_eligibility(session, "S2025008", "PHYS 102")
    assert result.eligible is False
    failing = [p for p in result.prerequisites if not p.satisfied]
    assert any(p.prerequisite_course_code == "PHYS 101" for p in failing)
    phys101_check = next(p for p in result.prerequisites if p.prerequisite_course_code == "PHYS 101")
    assert phys101_check.grade_earned == "F"


@pytest.mark.parametrize("course_code", ["MATH 202", "MATH 301"])
async def test_rania_not_eligible_for_courses_requiring_failed_math102(session, course_code):
    result = await check_course_eligibility(session, "S2025008", course_code)
    assert result.eligible is False
    math102_check = next(p for p in result.prerequisites if p.prerequisite_course_code == "MATH 102")
    assert math102_check.satisfied is False
    assert math102_check.grade_earned == "F"


@pytest.mark.parametrize("course_code", ["MECH 200", "MECH 210"])
async def test_rania_not_eligible_for_courses_requiring_failed_phys101_mech(session, course_code):
    result = await check_course_eligibility(session, "S2025008", course_code)
    assert result.eligible is False
    phys_check = next(p for p in result.prerequisites if p.prerequisite_course_code == "PHYS 101")
    assert phys_check.satisfied is False


async def test_rania_in_progress_retake_does_not_satisfy_prerequisite(session):
    # She is currently "In progress" on both MATH 102 and PHYS 101 - even
    # though there's a row on the transcript for this term, it must not
    # count as satisfying anything (no grade yet).
    attempts = await get_best_attempts(session, "S2025008")
    course_codes = {a.course_code for a in attempts}
    # Only the completed (failed) attempts show up in best_attempts, not
    # a phantom "in progress" entry.
    assert "MATH 102" in course_codes
    assert "PHYS 101" in course_codes
    math102 = next(a for a in attempts if a.course_code == "MATH 102")
    phys101 = next(a for a in attempts if a.course_code == "PHYS 101")
    assert math102.grade == "F"
    assert phys101.grade == "F"


# --- Sanity check: a course with all prerequisites satisfied is eligible.


async def test_maya_eligible_for_capstone_course_with_satisfied_prereqs(session):
    # Maya is a term from graduating and has completed her major core.
    result = await check_course_eligibility(session, "S2023011", "CENG 320")
    assert result.eligible is True
    assert all(p.satisfied for p in result.prerequisites)


# --- Maya has in-progress (not yet completed) enrollments this term in
# ENGR 490 (Professional Practice and Capstone) and ENGR 452 (Technical
# Electives). "eligible_courses_not_taken" must not offer courses she is
# already enrolled in, regardless of status - and credits_in_progress
# should reflect them.


async def test_maya_capstone_category_does_not_offer_engr490_shes_already_taking(session):
    student = await session.get(Student, "S2023011")
    categories = await compute_category_progress(session, student)
    capstone = next(c for c in categories if c.category_name == "Professional Practice and Capstone")

    offered_codes = {c["course_code"] for c in capstone.eligible_courses_not_taken}
    assert "ENGR 490" not in offered_codes
    assert capstone.credits_in_progress == 3


async def test_maya_electives_category_does_not_offer_engr452_shes_already_taking(session):
    student = await session.get(Student, "S2023011")
    categories = await compute_category_progress(session, student)
    electives = next(c for c in categories if c.category_name == "Technical Electives")

    offered_codes = {c["course_code"] for c in electives.eligible_courses_not_taken}
    assert "ENGR 452" not in offered_codes
    assert electives.credits_in_progress == 3


async def test_all_five_students_exist_and_have_a_program(session):
    students = (await session.execute(select(Student))).scalars().all()
    ids = {s.student_id for s in students}
    assert ids == set(EXPECTED.keys())
    for s in students:
        assert s.program_code in {"BE-CENG", "BE-MECH"}
