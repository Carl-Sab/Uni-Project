from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_student
from app.db import get_db
from app.models import Course
from app.schemas import CatalogueCourse
from app.services.academic import get_prereq_map

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=list[CatalogueCourse])
async def list_courses(
    _student_id: str = Depends(get_current_student), session: AsyncSession = Depends(get_db)
) -> list[CatalogueCourse]:
    """Not student-specific - just needs a valid token, same as every other
    /api route. Course data itself isn't scoped to anyone.
    """
    courses = (await session.execute(select(Course).order_by(Course.course_code))).scalars().all()
    prereq_map = await get_prereq_map(session)

    return [
        CatalogueCourse(
            course_code=c.course_code,
            title=c.title,
            credits=c.credits,
            description=c.description,
            prerequisites=prereq_map.get(c.course_code, []),
        )
        for c in courses
    ]
