"""Shared academic computations: GPA, credits, degree progress, eligibility.

This is the single implementation of these rules in the codebase. Both
app/scripts/verify_data.py (offline hand-check) and the /api/me/* routes
import from here — there is no second copy of the GPA or dedup logic.

Handbook: data/Eurisko_University_Student_Handbook_2026-2027.pdf
"""

from datetime import time
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    CategoryCourse,
    ClassSchedule,
    Course,
    CoursePrerequisite,
    Enrollment,
    GradingScale,
    RequirementCategory,
    Student,
    Term,
)


@dataclass(frozen=True)
class Attempt:
    course_code: str
    credits: int
    grade: str | None
    grade_points: Decimal | None
    earns_credit: bool
    included_in_gpa: bool


# --- Pure functions (no I/O) -----------------------------------------------
#
# Kept free of any DB/session dependency so the dedup/GPA/eligibility rules
# can be unit tested directly against synthetic data.


def dedupe_best_attempts(rows: list[tuple]) -> list[Attempt]:
    """One row per course_code: the completed attempt with the higher
    grade_points, per Handbook 1.5 - "Both attempts stay on the transcript,
    but only the higher grade counts toward the GPA. Credit for a course is
    earned once only, however many times it is taken."

    `rows` must already be restricted to status == "Completed": an
    "In progress" enrollment has no grade yet and cannot contribute to GPA,
    credit, or prerequisite satisfaction.

    Row shape: (course_code, credits, grade, grade_points, earns_credit,
    included_in_gpa).
    """
    best: dict[str, Attempt] = {}
    for course_code, credits, grade, grade_points, earns_credit, included_in_gpa in rows:
        # grade_points arrives from a NUMERIC(3,1) column, decoded by the
        # driver as Decimal already; str()-round-tripping here is a safety
        # net so a float can never sneak into the GPA arithmetic even if
        # that decoding behaviour changes.
        gp = Decimal(str(grade_points)) if grade_points is not None else None
        candidate = Attempt(course_code, credits, grade, gp, earns_credit, included_in_gpa)

        current = best.get(course_code)
        # NaN/None grade_points (W, P) sort below any numeric grade.
        if current is None or (
            candidate.grade_points is not None
            and (current.grade_points is None or candidate.grade_points > current.grade_points)
        ):
            best[course_code] = candidate
    return list(best.values())


def row_to_attempt(row: tuple) -> Attempt:
    """Wrap a single (course_code, credits, grade, grade_points, earns_credit,
    included_in_gpa) row as an Attempt with no dedup - for per-term GPA,
    where each term only ever has one attempt of a given course, so there is
    nothing to deduplicate (repeats span different terms).
    """
    course_code, credits, grade, grade_points, earns_credit, included_in_gpa = row
    gp = Decimal(str(grade_points)) if grade_points is not None else None
    return Attempt(course_code, credits, grade, gp, earns_credit, included_in_gpa)


def compute_gpa(attempts: list[Attempt]) -> Decimal | None:
    # Handbook 1.2: GPA = sum(grade_points * credits) / sum(credits attempted
    # in graded courses). Courses carrying W or P are excluded from both the
    # numerator and the denominator. Reported to two decimal places, not
    # rounded upward (i.e. truncated).
    numerator = Decimal("0")
    denominator = Decimal("0")
    for a in attempts:
        if not a.included_in_gpa:
            continue
        numerator += a.grade_points * Decimal(a.credits)
        denominator += Decimal(a.credits)

    if denominator == 0:
        return None  # no graded courses yet - avoid division by zero

    return (numerator / denominator).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def compute_total_credits_earned(attempts: list[Attempt]) -> int:
    # Handbook 1.3 / 1.5: a grade of D or above (or P) earns credit; credit
    # for a course is earned once only, however many times it is taken -
    # already guaranteed by `attempts` being deduplicated per course.
    return sum(a.credits for a in attempts if a.earns_credit)


@dataclass(frozen=True)
class PrereqCheck:
    prerequisite_course_code: str
    satisfied: bool
    grade_earned: str | None


@dataclass(frozen=True)
class EligibilityResult:
    course_code: str
    eligible: bool
    prerequisites: list[PrereqCheck]


def check_eligibility(
    course_code: str,
    prereq_map: dict[str, list[str]],
    best_attempts: dict[str, Attempt],
    c_minus_points: Decimal,
) -> EligibilityResult:
    """Handbook 2.2: "A student may not register for a course without having
    completed every prerequisite listed for it ... at a grade of C- or
    above. Where more than one prerequisite is listed, all are required."

    Handbook 1.3: "A grade of C- (1.7) or above is required in any course
    used as a prerequisite for another ... A student earning below C- in
    such a course keeps the credit but must repeat the course" - so a D
    (which earns credit, Handbook 1.3) does NOT satisfy a prerequisite.

    In-progress enrollments never appear in `best_attempts` (it is built
    from dedupe_best_attempts, which only considers completed rows), so an
    in-progress retake cannot satisfy a prerequisite either.
    """
    checks = []
    eligible = True
    for prereq_code in prereq_map.get(course_code, []):
        attempt = best_attempts.get(prereq_code)
        grade_earned = attempt.grade if attempt else None
        satisfied = (
            attempt is not None
            and attempt.grade_points is not None
            and attempt.grade_points >= c_minus_points
        )
        if not satisfied:
            eligible = False
        checks.append(PrereqCheck(prereq_code, satisfied, grade_earned))
    return EligibilityResult(course_code, eligible, checks)


@dataclass(frozen=True)
class CategoryProgress:
    category_id: str
    category_name: str
    credits_required: int
    credits_earned: int
    credits_in_progress: int
    credits_remaining: int
    eligible_courses_not_taken: list[dict]


# --- I/O-touching helpers ---------------------------------------------------


async def get_c_minus_points(session: AsyncSession) -> Decimal:
    grade_points = (
        await session.execute(
            select(GradingScale.grade_points).where(GradingScale.grade == "C-")
        )
    ).scalar_one()
    return Decimal(str(grade_points))


async def get_best_attempts(session: AsyncSession, student_id: str) -> list[Attempt]:
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


async def get_prereq_map(session: AsyncSession) -> dict[str, list[str]]:
    rows = (
        await session.execute(
            select(CoursePrerequisite.course_code, CoursePrerequisite.prerequisite_course_code)
        )
    ).all()
    prereq_map: dict[str, list[str]] = {}
    for course_code, prereq_code in rows:
        prereq_map.setdefault(course_code, []).append(prereq_code)
    return prereq_map


async def get_current_term_code(session: AsyncSession) -> str:
    return (
        await session.execute(select(Term.term_code).order_by(Term.sort_order.desc()).limit(1))
    ).scalar_one()


async def get_enrolled_course_codes(session: AsyncSession, student_id: str) -> set[str]:
    """Every course_code the student has an enrollment row for, in ANY
    status - completed or in-progress. Used to keep "courses that could fill
    this gap" meaning courses never enrolled in, not just courses not yet
    earning credit (an in-progress enrollment earns no credit yet either,
    but registering for it again would be nonsense).
    """
    rows = (
        await session.execute(
            select(Enrollment.course_code).where(Enrollment.student_id == student_id).distinct()
        )
    ).scalars().all()
    return set(rows)


async def get_in_progress_credits(session: AsyncSession, student_id: str) -> dict[str, int]:
    """course_code -> credits for the student's currently in-progress enrollments."""
    rows = (
        await session.execute(
            select(Enrollment.course_code, Enrollment.credits).where(
                Enrollment.student_id == student_id,
                Enrollment.status == "In progress",
            )
        )
    ).all()
    return {course_code: credits for course_code, credits in rows}


async def compute_category_progress(
    session: AsyncSession, student: Student
) -> list[CategoryProgress]:
    """Driven entirely by requirement_categories/category_courses for the
    student's programme - no branching on program_code anywhere here.
    """
    best_attempts = await get_best_attempts(session, student.student_id)
    best_by_course = {a.course_code: a for a in best_attempts}
    earned_courses = {a.course_code for a in best_attempts if a.earns_credit}

    enrolled_courses = await get_enrolled_course_codes(session, student.student_id)
    in_progress_credits = await get_in_progress_credits(session, student.student_id)

    prereq_map = await get_prereq_map(session)
    c_minus = await get_c_minus_points(session)

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
                select(Course.course_code, Course.title, Course.credits)
                .join(CategoryCourse, CategoryCourse.course_code == Course.course_code)
                .where(CategoryCourse.category_id == cat.category_id)
            )
        ).all()

        earned_in_category = sum(
            best_by_course[code].credits
            for code, _title, _credits in cat_courses
            if code in earned_courses
        )
        in_progress_in_category = sum(
            in_progress_credits[code] for code, _title, _credits in cat_courses if code in in_progress_credits
        )

        eligible_not_taken = []
        for code, title, credits in cat_courses:
            # "Not taken" means never enrolled at all, in any status - a
            # course already in progress this term can't fill a gap it's
            # already filling.
            if code in enrolled_courses:
                continue
            elig = check_eligibility(code, prereq_map, best_by_course, c_minus)
            if elig.eligible:
                eligible_not_taken.append({"course_code": code, "title": title, "credits": credits})

        result.append(
            CategoryProgress(
                category_id=cat.category_id,
                category_name=cat.category_name,
                credits_required=cat.credits_required,
                credits_earned=earned_in_category,
                credits_in_progress=in_progress_in_category,
                credits_remaining=max(cat.credits_required - earned_in_category, 0),
                eligible_courses_not_taken=eligible_not_taken,
            )
        )
    return result


async def check_course_eligibility(
    session: AsyncSession, student_id: str, course_code: str
) -> EligibilityResult:
    best_attempts = await get_best_attempts(session, student_id)
    best_by_course = {a.course_code: a for a in best_attempts}
    prereq_map = await get_prereq_map(session)
    c_minus = await get_c_minus_points(session)
    return check_eligibility(course_code, prereq_map, best_by_course, c_minus)


@dataclass(frozen=True)
class ScheduleItem:
    course_code: str
    title: str
    credits: int
    days: str
    start_time: time
    end_time: time
    room: str
    instructor: str


async def get_schedule_items(session: AsyncSession, student_id: str) -> list[ScheduleItem]:
    """Current-term (max sort_order in terms) classes the student is
    enrolled in, joined against class_schedule for meeting details. The one
    implementation used by both GET /api/me/schedule and the
    get_my_schedule agent tool.
    """
    current_term = await get_current_term_code(session)
    rows = (
        await session.execute(
            select(
                ClassSchedule.course_code,
                Course.title,
                Course.credits,
                ClassSchedule.days,
                ClassSchedule.start_time,
                ClassSchedule.end_time,
                ClassSchedule.room,
                ClassSchedule.instructor,
            )
            .join(Course, Course.course_code == ClassSchedule.course_code)
            .join(
                Enrollment,
                (Enrollment.course_code == ClassSchedule.course_code)
                & (Enrollment.term_code == ClassSchedule.term_code),
            )
            .where(
                Enrollment.student_id == student_id,
                ClassSchedule.term_code == current_term,
            )
            .order_by(ClassSchedule.start_time)
        )
    ).all()
    return [
        ScheduleItem(
            course_code=r.course_code,
            title=r.title,
            credits=r.credits,
            days=r.days,
            start_time=r.start_time,
            end_time=r.end_time,
            room=r.room,
            instructor=r.instructor,
        )
        for r in rows
    ]


@dataclass(frozen=True)
class CourseHistoryEntry:
    course_code: str
    title: str
    credits: int
    grade: str | None
    status: str


@dataclass
class TermCourses:
    term_code: str
    term_name: str
    term_gpa: Decimal | None
    courses: list[CourseHistoryEntry] = field(default_factory=list)


async def get_courses_by_term(session: AsyncSession, student_id: str) -> list[TermCourses]:
    """Every enrollment (completed and in-progress), grouped by term, with a
    per-term GPA. The one implementation used by both GET /api/me/courses
    and the get_my_courses agent tool.
    """
    rows = (
        await session.execute(
            select(
                Enrollment.term_code,
                Term.term_name,
                Term.sort_order,
                Enrollment.course_code,
                Course.title,
                Enrollment.credits,
                Enrollment.grade,
                Enrollment.status,
                GradingScale.grade_points,
                GradingScale.earns_credit,
                GradingScale.included_in_gpa,
            )
            .join(Term, Term.term_code == Enrollment.term_code)
            .join(Course, Course.course_code == Enrollment.course_code)
            .join(GradingScale, GradingScale.grade == Enrollment.grade, isouter=True)
            .where(Enrollment.student_id == student_id)
            .order_by(Term.sort_order, Enrollment.course_code)
        )
    ).all()

    terms: dict[str, TermCourses] = {}
    term_attempt_rows: dict[str, list[tuple]] = {}
    for r in rows:
        if r.term_code not in terms:
            terms[r.term_code] = TermCourses(term_code=r.term_code, term_name=r.term_name, term_gpa=None)
            term_attempt_rows[r.term_code] = []
        terms[r.term_code].courses.append(
            CourseHistoryEntry(
                course_code=r.course_code,
                title=r.title,
                credits=r.credits,
                grade=r.grade,
                status=r.status,
            )
        )
        if r.status == "Completed":
            term_attempt_rows[r.term_code].append(
                (r.course_code, r.credits, r.grade, r.grade_points, r.earns_credit, r.included_in_gpa)
            )

    for term_code, term_courses in terms.items():
        attempts = [row_to_attempt(row) for row in term_attempt_rows[term_code]]
        term_courses.term_gpa = compute_gpa(attempts)

    return list(terms.values())
