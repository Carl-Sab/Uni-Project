from datetime import date, datetime, time
from decimal import Decimal

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

EMBEDDING_DIM = 1536


class Term(Base):
    __tablename__ = "terms"

    term_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    term_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Explicit chronological order (year * 10 + season rank), since term_code
    # sorts wrong as a string: "FA2023" < "SP2024" is false lexicographically.
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)


class Program(Base):
    __tablename__ = "programs"

    program_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    program_name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_credits_required: Mapped[int] = mapped_column(Integer, nullable=False)


class RequirementCategory(Base):
    __tablename__ = "requirement_categories"

    # Programme-scoped: the same course can satisfy a category in one
    # programme and not another, because categories themselves belong to a
    # single programme (category_id values are already programme-prefixed,
    # e.g. BE-CENG-CORE vs BE-MECH-CORE).
    category_id: Mapped[str] = mapped_column(String(30), primary_key=True)
    program_code: Mapped[str] = mapped_column(
        ForeignKey("programs.program_code"), nullable=False
    )
    category_name: Mapped[str] = mapped_column(String(100), nullable=False)
    credits_required: Mapped[int] = mapped_column(Integer, nullable=False)


class Course(Base):
    __tablename__ = "courses"

    course_code: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)


class CategoryCourse(Base):
    """Junction: which courses count toward which programme-scoped category."""

    __tablename__ = "category_courses"

    category_id: Mapped[str] = mapped_column(
        ForeignKey("requirement_categories.category_id"), primary_key=True
    )
    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code"), primary_key=True
    )


class CoursePrerequisite(Base):
    """Junction: one row per required prerequisite.

    Multiple rows for the same course_code are AND'd together (all are
    required) simply by each being its own row — a caller must find every
    row for a course_code satisfied, not just one, so the "all required"
    rule falls out of reading the whole row set rather than needing an
    explicit AND/OR flag.
    """

    __tablename__ = "course_prerequisites"

    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code"), primary_key=True
    )
    prerequisite_course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code"), primary_key=True
    )


class Student(Base):
    __tablename__ = "students"

    student_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    program_code: Mapped[str] = mapped_column(
        ForeignKey("programs.program_code"), nullable=False
    )
    entry_term: Mapped[str] = mapped_column(ForeignKey("terms.term_code"), nullable=False)
    # Not a FK to terms: several students' expected graduation terms (e.g.
    # SP2027, SP2030) fall beyond the terms currently in the dataset.
    expected_graduation_term: Mapped[str] = mapped_column(String(10), nullable=False)
    academic_status: Mapped[str] = mapped_column(String(30), nullable=False)
    advisor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Enrollment(Base):
    __tablename__ = "enrollments"

    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id"), primary_key=True
    )
    term_code: Mapped[str] = mapped_column(ForeignKey("terms.term_code"), primary_key=True)
    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code"), primary_key=True
    )
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str | None] = mapped_column(
        ForeignKey("grading_scale.grade"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)


class GradingScale(Base):
    __tablename__ = "grading_scale"

    grade: Mapped[str] = mapped_column(String(5), primary_key=True)
    grade_points: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    earns_credit: Mapped[bool] = mapped_column(Boolean, nullable=False)
    included_in_gpa: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ClassSchedule(Base):
    __tablename__ = "class_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term_code: Mapped[str] = mapped_column(ForeignKey("terms.term_code"), nullable=False)
    course_code: Mapped[str] = mapped_column(
        ForeignKey("courses.course_code"), nullable=False
    )
    days: Mapped[str] = mapped_column(String(30), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    room: Mapped[str] = mapped_column(String(20), nullable=False)
    instructor: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("term_code", "course_code", name="uq_class_schedule_term_course"),
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # "pending" | "indexing" | "indexed" | "failed" - polled by the admin
    # while ingestion runs as a background task.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class DocChunk(Base):
    __tablename__ = "doc_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    section_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    tsv: Mapped[str] = mapped_column(TSVECTOR, nullable=False)


class AssistantConfig(Base):
    """Single-row table (id is always 1) - an admin edit here is picked up
    by the very next chat message, since the system prompt and model are
    assembled fresh from this row on every request rather than cached at
    startup.
    """

    __tablename__ = "assistant_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    persona: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    # "brief" | "detailed"
    response_length: Mapped[str] = mapped_column(String(20), nullable=False)
    temperature: Mapped[Decimal] = mapped_column(Numeric(2, 1), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_time: Mapped[str] = mapped_column(String(200), nullable=False)
    # "pending" | "approved" | "declined" - the agent only ever creates
    # "pending" rows; POST /api/me/appointments/{id}/approve is the only
    # thing that can move a row to "approved" (human-in-the-loop booking).
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.student_id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    # "user" | "assistant"
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
