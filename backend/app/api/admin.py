"""Admin-only endpoints. Every route here depends on require_admin, never on
get_current_student - see app/auth.py. GET /api/admin/students/{student_id}
is the one legitimate place a student_id appears in a URL path anywhere in
this codebase; it works precisely because it sits behind require_admin, not
because the student-scoped dependency was reused or weakened.
"""

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.db import get_db
from app.models import (
    AssistantConfig,
    CategoryCourse,
    Course,
    CoursePrerequisite,
    Document,
    DocChunk,
    Enrollment,
    Program,
    RequirementCategory,
    Student,
    Term,
)
from app.schemas import (
    AdminCourseResponse,
    AdminDocumentResponse,
    AdminEnrollmentPage,
    AdminEnrollmentResponse,
    AdminStatsResponse,
    AdminStudentDetail,
    AdminStudentSummary,
    AssistantConfigResponse,
    AssistantConfigUpdate,
    CategoryProgressResponse,
    CourseHistoryEntry,
    EligibleCourse,
    ProfileResponse,
    TermHistory,
)
from app.services.academic import (
    compute_gpa,
    compute_total_credits_earned,
    get_best_attempts,
    get_cached_category_progress,
    get_courses_by_term,
)
from app.services.ingestion import (
    UPLOADS_DIR,
    delete_document,
    start_ingestion,
    start_reindex,
    upload_path_for,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_DOC_TYPES = {"handbook", "catalogue"}


# --- Stats -------------------------------------------------------------------


@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    _admin: str = Depends(require_admin), session: AsyncSession = Depends(get_db)
) -> AdminStatsResponse:
    student_count = (await session.execute(select(func.count()).select_from(Student))).scalar_one()
    course_count = (await session.execute(select(func.count()).select_from(Course))).scalar_one()
    enrollment_count = (
        await session.execute(select(func.count()).select_from(Enrollment))
    ).scalar_one()
    indexed_document_count = (
        await session.execute(
            select(func.count()).select_from(Document).where(Document.status == "indexed")
        )
    ).scalar_one()
    total_chunk_count = (await session.execute(select(func.count()).select_from(DocChunk))).scalar_one()
    last_ingested_at = (
        await session.execute(select(func.max(Document.indexed_at)))
    ).scalar_one()

    return AdminStatsResponse(
        student_count=student_count,
        course_count=course_count,
        enrollment_count=enrollment_count,
        indexed_document_count=indexed_document_count,
        total_chunk_count=total_chunk_count,
        last_ingested_at=last_ingested_at,
    )


# --- Documents -----------------------------------------------------------------


@router.get("/documents", response_model=list[AdminDocumentResponse])
async def list_documents(
    _admin: str = Depends(require_admin), session: AsyncSession = Depends(get_db)
) -> list[AdminDocumentResponse]:
    docs = (await session.execute(select(Document).order_by(Document.uploaded_at.desc()))).scalars().all()
    return [
        AdminDocumentResponse(
            id=d.id,
            filename=d.filename,
            doc_type=d.doc_type,
            uploaded_at=d.uploaded_at,
            indexed_at=d.indexed_at,
            status=d.status,
            chunk_count=d.chunk_count,
        )
        for d in docs
    ]


@router.post("/documents", response_model=AdminDocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AdminDocumentResponse:
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type must be one of {sorted(VALID_DOC_TYPES)}",
        )
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only PDF files are supported")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = upload_path_for(file.filename)
    contents = await file.read()
    dest.write_bytes(contents)

    existing = (
        await session.execute(select(Document).where(Document.filename == file.filename))
    ).scalar_one_or_none()
    if existing is not None:
        existing.doc_type = doc_type
        existing.status = "pending"
        existing.uploaded_at = datetime.now(timezone.utc)
        doc = existing
    else:
        doc = Document(
            filename=file.filename,
            doc_type=doc_type,
            uploaded_at=datetime.now(timezone.utc),
            indexed_at=None,
            status="pending",
            chunk_count=0,
            checksum="",  # computed by the ingestion pipeline itself
        )
        session.add(doc)
    await session.commit()
    await session.refresh(doc)

    start_ingestion(file.filename, str(dest), doc_type)

    return AdminDocumentResponse(
        id=doc.id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        uploaded_at=doc.uploaded_at,
        indexed_at=doc.indexed_at,
        status=doc.status,
        chunk_count=doc.chunk_count,
    )


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_document_route(
    document_id: int,
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    doc.status = "pending"
    await session.commit()
    start_reindex(document_id)
    return {"status": "reindex started"}


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document_route(
    document_id: int,
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> None:
    doc = await session.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    await delete_document(document_id)


# --- Students ------------------------------------------------------------------


@router.get("/students", response_model=list[AdminStudentSummary])
async def list_students(
    _admin: str = Depends(require_admin), session: AsyncSession = Depends(get_db)
) -> list[AdminStudentSummary]:
    rows = (
        await session.execute(
            select(Student, Program.program_name)
            .join(Program, Program.program_code == Student.program_code)
            .order_by(Student.student_id)
        )
    ).all()

    result = []
    for student, program_name in rows:
        best_attempts = await get_best_attempts(session, student.student_id)
        result.append(
            AdminStudentSummary(
                student_id=student.student_id,
                first_name=student.first_name,
                last_name=student.last_name,
                program_code=student.program_code,
                program_name=program_name,
                academic_status=student.academic_status,
                cumulative_gpa=compute_gpa(best_attempts),
                total_credits_earned=compute_total_credits_earned(best_attempts),
            )
        )
    return result


@router.get("/students/{student_id}", response_model=AdminStudentDetail)
async def get_student_detail(
    student_id: str,
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AdminStudentDetail:
    student = await session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    program = await session.get(Program, student.program_code)

    best_attempts = await get_best_attempts(session, student_id)
    gpa = compute_gpa(best_attempts)
    total_credits = compute_total_credits_earned(best_attempts)

    terms = await get_courses_by_term(session, student_id)
    categories = await get_cached_category_progress(session, student)

    return AdminStudentDetail(
        profile=ProfileResponse(
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
        ),
        terms=[
            TermHistory(
                term_code=t.term_code,
                term_name=t.term_name,
                term_gpa=t.term_gpa,
                courses=[CourseHistoryEntry(**vars(c)) for c in t.courses],
            )
            for t in terms
        ],
        degree_progress=[
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
        ],
    )


# --- Courses ---------------------------------------------------------------


@router.get("/courses", response_model=list[AdminCourseResponse])
async def list_courses(
    _admin: str = Depends(require_admin), session: AsyncSession = Depends(get_db)
) -> list[AdminCourseResponse]:
    courses = (await session.execute(select(Course).order_by(Course.course_code))).scalars().all()

    prereq_rows = (
        await session.execute(
            select(CoursePrerequisite.course_code, CoursePrerequisite.prerequisite_course_code)
        )
    ).all()
    prereq_map: dict[str, list[str]] = {}
    for code, prereq in prereq_rows:
        prereq_map.setdefault(code, []).append(prereq)

    category_rows = (
        await session.execute(
            select(CategoryCourse.course_code, RequirementCategory.category_name)
            .join(RequirementCategory, RequirementCategory.category_id == CategoryCourse.category_id)
        )
    ).all()
    # Two different programme-scoped categories (e.g. BE-CENG-CORE and
    # BE-MECH-CORE) can share the same display name "Engineering Core" - a
    # course common to both programmes' core (MATH 101, PHYS 101, ...)
    # would otherwise show that name twice in this cross-programme view.
    # dict.fromkeys preserves first-seen order while deduping.
    category_map: dict[str, list[str]] = {}
    for code, category_name in category_rows:
        names = category_map.setdefault(code, [])
        if category_name not in names:
            names.append(category_name)

    return [
        AdminCourseResponse(
            course_code=c.course_code,
            title=c.title,
            credits=c.credits,
            prerequisites=prereq_map.get(c.course_code, []),
            categories=category_map.get(c.course_code, []),
        )
        for c in courses
    ]


# --- Enrollments -----------------------------------------------------------


@router.get("/enrollments", response_model=AdminEnrollmentPage)
async def list_enrollments(
    student_id: str | None = Query(default=None),
    term_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AdminEnrollmentPage:
    query = (
        select(
            Enrollment.student_id,
            Student.first_name,
            Student.last_name,
            Enrollment.term_code,
            Enrollment.course_code,
            Course.title,
            Enrollment.credits,
            Enrollment.grade,
            Enrollment.status,
        )
        .join(Student, Student.student_id == Enrollment.student_id)
        .join(Course, Course.course_code == Enrollment.course_code)
        .join(Term, Term.term_code == Enrollment.term_code)
    )
    if student_id:
        query = query.where(Enrollment.student_id == student_id)
    if term_code:
        query = query.where(Enrollment.term_code == term_code)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    query = (
        # Term.sort_order, not Enrollment.term_code - term codes sort
        # wrong as strings ("FA2023" < "SP2024" is false lexicographically,
        # the same trap the terms table itself was built to avoid).
        query.order_by(Enrollment.student_id, Term.sort_order, Enrollment.course_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(query)).all()

    items = [
        AdminEnrollmentResponse(
            student_id=r.student_id,
            student_name=f"{r.first_name} {r.last_name}",
            term_code=r.term_code,
            course_code=r.course_code,
            course_title=r.title,
            credits=r.credits,
            grade=r.grade,
            status=r.status,
        )
        for r in rows
    ]
    return AdminEnrollmentPage(items=items, total=total, page=page, page_size=page_size)


# --- Assistant config --------------------------------------------------------


@router.get("/config", response_model=AssistantConfigResponse)
async def get_config(
    _admin: str = Depends(require_admin), session: AsyncSession = Depends(get_db)
) -> AssistantConfigResponse:
    config = await session.get(AssistantConfig, 1)
    return AssistantConfigResponse(
        persona=config.persona,
        model_provider=config.model_provider,
        model_name=config.model_name,
        response_length=config.response_length,
        temperature=config.temperature,
        updated_at=config.updated_at,
    )


@router.put("/config", response_model=AssistantConfigResponse)
async def update_config(
    body: AssistantConfigUpdate,
    _admin: str = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> AssistantConfigResponse:
    config = await session.get(AssistantConfig, 1)
    config.persona = body.persona
    config.model_provider = body.model_provider
    config.model_name = body.model_name
    config.response_length = body.response_length
    config.temperature = body.temperature
    config.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(config)

    return AssistantConfigResponse(
        persona=config.persona,
        model_provider=config.model_provider,
        model_name=config.model_name,
        response_length=config.response_length,
        temperature=config.temperature,
        updated_at=config.updated_at,
    )
