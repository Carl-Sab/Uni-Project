"""initial schema

Revision ID: 15b11f4213a1
Revises:
Create Date: 2026-08-13 20:53:28.634108

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15b11f4213a1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "terms",
        sa.Column("term_code", sa.String(10), primary_key=True),
        sa.Column("term_name", sa.String(50), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, unique=True),
    )

    op.create_table(
        "programs",
        sa.Column("program_code", sa.String(20), primary_key=True),
        sa.Column("program_name", sa.String(100), nullable=False),
        sa.Column("total_credits_required", sa.Integer, nullable=False),
    )

    op.create_table(
        "requirement_categories",
        sa.Column("category_id", sa.String(30), primary_key=True),
        sa.Column(
            "program_code",
            sa.String(20),
            sa.ForeignKey("programs.program_code"),
            nullable=False,
        ),
        sa.Column("category_name", sa.String(100), nullable=False),
        sa.Column("credits_required", sa.Integer, nullable=False),
    )

    op.create_table(
        "courses",
        sa.Column("course_code", sa.String(20), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("credits", sa.Integer, nullable=False),
        sa.Column("description", sa.Text, nullable=False),
    )

    op.create_table(
        "category_courses",
        sa.Column(
            "category_id",
            sa.String(30),
            sa.ForeignKey("requirement_categories.category_id"),
            primary_key=True,
        ),
        sa.Column(
            "course_code",
            sa.String(20),
            sa.ForeignKey("courses.course_code"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_category_courses_category_id", "category_courses", ["category_id"]
    )

    op.create_table(
        "course_prerequisites",
        sa.Column(
            "course_code",
            sa.String(20),
            sa.ForeignKey("courses.course_code"),
            primary_key=True,
        ),
        sa.Column(
            "prerequisite_course_code",
            sa.String(20),
            sa.ForeignKey("courses.course_code"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_course_prerequisites_course_code", "course_prerequisites", ["course_code"]
    )

    op.create_table(
        "grading_scale",
        sa.Column("grade", sa.String(5), primary_key=True),
        sa.Column("grade_points", sa.Numeric(3, 1), nullable=True),
        sa.Column("earns_credit", sa.Boolean, nullable=False),
        sa.Column("included_in_gpa", sa.Boolean, nullable=False),
    )

    op.create_table(
        "students",
        sa.Column("student_id", sa.String(20), primary_key=True),
        sa.Column("first_name", sa.String(50), nullable=False),
        sa.Column("last_name", sa.String(50), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column(
            "program_code",
            sa.String(20),
            sa.ForeignKey("programs.program_code"),
            nullable=False,
        ),
        sa.Column(
            "entry_term", sa.String(10), sa.ForeignKey("terms.term_code"), nullable=False
        ),
        # Not a FK to terms: several students' expected graduation terms
        # (e.g. SP2027, SP2030) fall beyond the terms currently in the
        # dataset.
        sa.Column("expected_graduation_term", sa.String(10), nullable=False),
        sa.Column("academic_status", sa.String(30), nullable=False),
        sa.Column("advisor_name", sa.String(100), nullable=False),
        sa.Column("scenario_note", sa.Text, nullable=True),
    )

    op.create_table(
        "enrollments",
        sa.Column(
            "student_id",
            sa.String(20),
            sa.ForeignKey("students.student_id"),
            primary_key=True,
        ),
        sa.Column(
            "term_code", sa.String(10), sa.ForeignKey("terms.term_code"), primary_key=True
        ),
        sa.Column(
            "course_code",
            sa.String(20),
            sa.ForeignKey("courses.course_code"),
            primary_key=True,
        ),
        sa.Column("credits", sa.Integer, nullable=False),
        sa.Column("grade", sa.String(5), sa.ForeignKey("grading_scale.grade"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index(
        "ix_enrollments_student_id_term_code",
        "enrollments",
        ["student_id", "term_code"],
    )

    op.create_table(
        "class_schedule",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "term_code", sa.String(10), sa.ForeignKey("terms.term_code"), nullable=False
        ),
        sa.Column(
            "course_code",
            sa.String(20),
            sa.ForeignKey("courses.course_code"),
            nullable=False,
        ),
        sa.Column("days", sa.String(30), nullable=False),
        sa.Column("start_time", sa.Time, nullable=False),
        sa.Column("end_time", sa.Time, nullable=False),
        sa.Column("room", sa.String(20), nullable=False),
        sa.Column("instructor", sa.String(100), nullable=False),
        sa.UniqueConstraint(
            "term_code", "course_code", name="uq_class_schedule_term_course"
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("class_schedule")
    op.drop_index("ix_enrollments_student_id_term_code", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_table("students")
    op.drop_table("grading_scale")
    op.drop_index("ix_course_prerequisites_course_code", table_name="course_prerequisites")
    op.drop_table("course_prerequisites")
    op.drop_index("ix_category_courses_category_id", table_name="category_courses")
    op.drop_table("category_courses")
    op.drop_table("courses")
    op.drop_table("requirement_categories")
    op.drop_table("programs")
    op.drop_table("terms")
