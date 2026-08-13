"""Advisor appointment proposals.

Human-in-the-loop by construction: creating a row here only ever produces
status="pending". Nothing in this module can move a row to "approved" - that
happens exclusively via POST /api/me/appointments/{id}/approve, a separate
endpoint a human calls after reviewing the proposal. The agent tool that
calls create_appointment_proposal can propose an appointment; it cannot
book one.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment


@dataclass(frozen=True)
class AppointmentProposal:
    id: int
    student_id: str
    reason: str
    preferred_time: str
    status: str


async def create_appointment_proposal(
    session: AsyncSession, student_id: str, reason: str, preferred_time: str
) -> AppointmentProposal:
    now = datetime.now(timezone.utc)
    appointment = Appointment(
        student_id=student_id,
        reason=reason,
        preferred_time=preferred_time,
        status="pending",
        created_at=now,
        updated_at=now,
    )
    session.add(appointment)
    await session.flush()
    return AppointmentProposal(
        id=appointment.id,
        student_id=appointment.student_id,
        reason=appointment.reason,
        preferred_time=appointment.preferred_time,
        status=appointment.status,
    )


async def approve_appointment(
    session: AsyncSession, student_id: str, appointment_id: int
) -> Appointment | None:
    """Scoped to student_id exactly like every other /api/me route - a
    student can only approve their own pending appointment, never another
    student's by guessing an id.
    """
    appointment = (
        await session.execute(
            select(Appointment).where(
                Appointment.id == appointment_id, Appointment.student_id == student_id
            )
        )
    ).scalar_one_or_none()
    if appointment is None:
        return None
    appointment.status = "approved"
    appointment.updated_at = datetime.now(timezone.utc)
    return appointment
