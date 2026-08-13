"""Every route in this module is scoped to the token holder via
get_current_student. None of them accept a student_id from the client -
there is no /api/students/{id}/... route anywhere in this codebase.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_student
from app.db import get_db
from app.models import ClassSchedule, Course, Enrollment, GradingScale, Program, Student, Term
from app.schemas import (
    CategoryProgressResponse,
    CourseHistoryEntry,
    EligibilityResponse,
    EligibleCourse,
    PrereqCheckResponse,
    ProfileResponse,
    ScheduleItem,
    TermHistory,
)
from app.services.academic import (
    check_course_eligibility,
    compute_category_progress,
    compute_gpa,
    compute_total_credits_earned,
    get_best_attempts,
    get_current_term_code,
    row_to_attempt,
)

router = APIRouter(prefix="/api/me", tags=["me"])


async def _get_student(session: AsyncSession, student_id: str) -> Student:
    student = await session.get(Student, student_id)
    if student is None:
        # The JWT was valid but the student row it names is gone.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


@router.get("", response_model=ProfileResponse)
async def get_profile(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> ProfileResponse:
    student = await _get_student(session, student_id)
    program = await session.get(Program, student.program_code)

    best_attempts = await get_best_attempts(session, student_id)
    gpa = compute_gpa(best_attempts)
    total_credits = compute_total_credits_earned(best_attempts)

    return ProfileResponse(
        student_id=student.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        email=student.email,
        program_code=student.program_code,
        program_name=program.program_name,
        entry_term=student.entry_term,
        expected_graduation_term=student.expected_graduation_term,
        academic_status=student.academic_status,
        advisor_name=student.advisor_name,
        cumulative_gpa=gpa,
        total_credits_earned=total_credits,
    )


@router.get("/schedule", response_model=list[ScheduleItem])
async def get_schedule(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[ScheduleItem]:
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


@router.get("/courses", response_model=list[TermHistory])
async def get_courses(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[TermHistory]:
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

    terms: dict[str, TermHistory] = {}
    term_attempt_rows: dict[str, list[tuple]] = {}
    for r in rows:
        if r.term_code not in terms:
            terms[r.term_code] = TermHistory(
                term_code=r.term_code, term_name=r.term_name, term_gpa=None, courses=[]
            )
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

    for term_code, term_history in terms.items():
        attempts = [row_to_attempt(row) for row in term_attempt_rows[term_code]]
        term_history.term_gpa = compute_gpa(attempts)

    return list(terms.values())


@router.get("/degree-progress", response_model=list[CategoryProgressResponse])
async def get_degree_progress(
    student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[CategoryProgressResponse]:
    student = await _get_student(session, student_id)
    categories = await compute_category_progress(session, student)

    return [
        CategoryProgressResponse(
            category_id=c.category_id,
            category_name=c.category_name,
            credits_required=c.credits_required,
            credits_earned=c.credits_earned,
            credits_in_progress=c.credits_in_progress,
            credits_remaining=c.credits_remaining,
            eligible_courses_not_taken=[EligibleCourse(**ec) for ec in c.eligible_courses_not_taken],
        )
        for c in categories
    ]


@router.get("/eligibility/{course_code}", response_model=EligibilityResponse)
async def get_eligibility(
    course_code: str,
    student_id: str = Depends(get_current_student),
    session: AsyncSession = Depends(get_db),
) -> EligibilityResponse:
    course = await session.get(Course, course_code)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown course_code")

    result = await check_course_eligibility(session, student_id, course_code)
    return EligibilityResponse(
        course_code=result.course_code,
        eligible=result.eligible,
        prerequisites=[
            PrereqCheckResponse(
                prerequisite_course_code=p.prerequisite_course_code,
                satisfied=p.satisfied,
                grade_earned=p.grade_earned,
            )
            for p in result.prerequisites
        ],
    )
