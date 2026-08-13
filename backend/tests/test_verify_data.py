"""Unit tests for the GPA/credit dedup rule (Handbook 1.5).

The live dataset only ever has one *completed* attempt per (student, course)
pair - Rania's repeats are still "In progress" - so the dedup path where two
completed attempts of the same course exist is never exercised against real
data. These tests construct that case synthetically.
"""

from decimal import Decimal

from app.services.academic import compute_gpa, compute_total_credits_earned, dedupe_best_attempts

# Row shape matches the query in get_best_attempts:
# (course_code, credits, grade, grade_points, earns_credit, included_in_gpa)


def test_dedup_keeps_higher_grade_between_two_completed_attempts():
    rows = [
        ("MATH 101", 3, "F", Decimal("0.0"), False, True),   # first attempt: failed
        ("MATH 101", 3, "B", Decimal("3.0"), True, True),    # retake: passed
    ]

    best = dedupe_best_attempts(rows)

    assert len(best) == 1
    assert best[0].grade == "B"
    assert best[0].grade_points == Decimal("3.0")


def test_dedup_is_order_independent():
    rows = [
        ("MATH 101", 3, "B", Decimal("3.0"), True, True),
        ("MATH 101", 3, "F", Decimal("0.0"), False, True),
    ]

    best = dedupe_best_attempts(rows)

    assert len(best) == 1
    assert best[0].grade == "B"


def test_credit_earned_once_despite_two_completed_attempts():
    rows = [
        ("MATH 101", 3, "F", Decimal("0.0"), False, True),
        ("MATH 101", 3, "B", Decimal("3.0"), True, True),
    ]

    best = dedupe_best_attempts(rows)

    assert compute_total_credits_earned(best) == 3  # not 6


def test_gpa_uses_only_the_higher_attempt():
    rows = [
        ("MATH 101", 3, "F", Decimal("0.0"), False, True),
        ("MATH 101", 3, "B", Decimal("3.0"), True, True),
        ("PHYS 101", 3, "A", Decimal("4.0"), True, True),
    ]

    best = dedupe_best_attempts(rows)
    gpa = compute_gpa(best)

    # Only B (3.0) and A (4.0) count, the F attempt is dropped entirely:
    # (3.0*3 + 4.0*3) / (3 + 3) = 3.50
    assert gpa == Decimal("3.50")


def test_w_and_p_excluded_from_gpa_but_p_earns_credit():
    rows = [
        ("HUMN 210", 3, "P", None, True, False),
        ("SOCI 240", 3, "W", None, False, False),
        ("MATH 101", 3, "A", Decimal("4.0"), True, True),
    ]

    best = dedupe_best_attempts(rows)
    gpa = compute_gpa(best)

    assert gpa == Decimal("4.00")  # only MATH 101 counts
    assert compute_total_credits_earned(best) == 6  # HUMN 210 (P) + MATH 101, not SOCI 240 (W)


def test_no_graded_courses_returns_none_not_division_by_zero():
    rows = [("HUMN 210", 3, "P", None, True, False)]

    best = dedupe_best_attempts(rows)

    assert compute_gpa(best) is None
