from datetime import time
from decimal import Decimal

from pydantic import BaseModel


class StudentLoginRequest(BaseModel):
    student_id: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileResponse(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    email: str
    program_code: str
    program_name: str
    entry_term: str
    expected_graduation_term: str
    academic_status: str
    advisor_name: str
    cumulative_gpa: Decimal | None
    total_credits_earned: int


class ScheduleItem(BaseModel):
    course_code: str
    title: str
    credits: int
    days: str
    start_time: time
    end_time: time
    room: str
    instructor: str


class CourseHistoryEntry(BaseModel):
    course_code: str
    title: str
    credits: int
    grade: str | None
    status: str


class TermHistory(BaseModel):
    term_code: str
    term_name: str
    term_gpa: Decimal | None
    courses: list[CourseHistoryEntry]


class EligibleCourse(BaseModel):
    course_code: str
    title: str
    credits: int


class CategoryProgressResponse(BaseModel):
    category_id: str
    category_name: str
    credits_required: int
    credits_earned: int
    credits_in_progress: int
    credits_remaining: int
    eligible_courses_not_taken: list[EligibleCourse]


class PrereqCheckResponse(BaseModel):
    prerequisite_course_code: str
    satisfied: bool
    grade_earned: str | None


class EligibilityResponse(BaseModel):
    course_code: str
    eligible: bool
    prerequisites: list[PrereqCheckResponse]


class CatalogueCourse(BaseModel):
    course_code: str
    title: str
    credits: int
    description: str
    prerequisites: list[str]
