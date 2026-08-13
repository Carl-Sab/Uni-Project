"""The PydanticAI assistant: deps, tools, and the system prompt assembled
from assistant_config at request time.

CRITICAL security model: AgentDeps.student_id is the only source of "which
student" anywhere below. It is set once, by the caller, from the JWT (via
get_current_student) - never from anything the model outputs. Every tool
signature below takes no student_id parameter; there is nothing for the
model to name, so there is no way for it to ask for - or be tricked into
using - another student's id. This is the same rule the /api/me/* routes
already follow (see app/auth.py).
"""

from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal

from pydantic_ai import Agent, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import get_model
from app.models import AssistantConfig, Student
from app.services.academic import (
    check_course_eligibility as _check_course_eligibility,
    compute_category_progress,
    compute_gpa,
    compute_total_credits_earned,
    get_best_attempts,
    get_courses_by_term,
    get_schedule_items,
)
from app.services.appointments import create_appointment_proposal
from app.services.retrieval import hybrid_search


@dataclass
class AgentDeps:
    student_id: str
    session: AsyncSession
    config: AssistantConfig


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, time)):
        return value.isoformat()
    return value


def _row_dict(obj) -> dict:
    return {k: _jsonable(v) for k, v in vars(obj).items()}


agent = Agent(deps_type=AgentDeps)


@agent.tool
async def search_documents(ctx: RunContext[AgentDeps], query: str) -> list[dict]:
    """Search the Handbook and Course Catalogue for policy, deadlines,
    fees, grading rules, course descriptions, or anything else that lives
    in a document rather than the student's own record. Always cite the
    filename and page/section from the results you use.
    """
    results = await hybrid_search(ctx.deps.session, query)
    return [
        {
            "content": r.content,
            "filename": r.filename,
            "page": r.page,
            "section_number": r.section_number,
            "section_title": r.section_title,
        }
        for r in results
    ]


@agent.tool
async def get_my_schedule(ctx: RunContext[AgentDeps]) -> list[dict]:
    """The current term's class schedule for the logged-in student: course,
    days, times, room, instructor. Only Fall 2026 schedule data exists in
    this system.
    """
    items = await get_schedule_items(ctx.deps.session, ctx.deps.student_id)
    return [_row_dict(item) for item in items]


@agent.tool
async def get_my_courses(ctx: RunContext[AgentDeps]) -> dict:
    """The logged-in student's full academic history, grouped by term:
    every course taken or in progress, with grades and a per-term GPA, plus
    the authoritative cumulative GPA and total credits earned. Use the
    cumulative_gpa field directly for "what's my GPA" - it is already
    correctly computed (deduplicated repeats, W/P excluded); do not
    estimate or average the per-term GPAs yourself.
    """
    terms = await get_courses_by_term(ctx.deps.session, ctx.deps.student_id)
    best_attempts = await get_best_attempts(ctx.deps.session, ctx.deps.student_id)
    return {
        "cumulative_gpa": _jsonable(compute_gpa(best_attempts)),
        "total_credits_earned": compute_total_credits_earned(best_attempts),
        "terms": [
            {
                "term_code": t.term_code,
                "term_name": t.term_name,
                "term_gpa": _jsonable(t.term_gpa),
                "courses": [_row_dict(c) for c in t.courses],
            }
            for t in terms
        ],
    }


@agent.tool
async def get_my_degree_progress(ctx: RunContext[AgentDeps]) -> list[dict]:
    """Degree progress for the logged-in student, per requirement category:
    credits required, earned, in progress, remaining, and which not-yet-
    taken courses in that category the student is currently eligible for.
    """
    student = await ctx.deps.session.get(Student, ctx.deps.student_id)
    categories = await compute_category_progress(ctx.deps.session, student)
    return [
        {
            "category_name": c.category_name,
            "credits_required": c.credits_required,
            "credits_earned": c.credits_earned,
            "credits_in_progress": c.credits_in_progress,
            "credits_remaining": c.credits_remaining,
            "eligible_courses_not_taken": c.eligible_courses_not_taken,
        }
        for c in categories
    ]


@agent.tool
async def check_course_eligibility(ctx: RunContext[AgentDeps], course_code: str) -> dict:
    """Whether the logged-in student may register for a course, and why or
    why not. Combines three things: the course's prerequisites, the
    minimum grade required for a prerequisite to count (retrieved from the
    Handbook, not assumed), and the student's own transcript.

    Report the specific failing prerequisite and the grade actually earned
    when eligibility fails - "not eligible" alone is not a useful answer.
    """
    # The eligibility computation itself (app.services.academic) already
    # pulls its minimum-grade threshold from the grading_scale table rather
    # than a hardcoded "C-" value - see get_c_minus_points. What's added
    # here is the citable source for THAT rule: the Handbook passage that
    # actually states it, retrieved live rather than assumed, so the
    # agent can quote where the rule comes from instead of asserting it.
    result = await _check_course_eligibility(ctx.deps.session, ctx.deps.student_id, course_code)
    rule_passages = await hybrid_search(
        ctx.deps.session, "minimum grade required for a prerequisite course"
    )

    return {
        "course_code": result.course_code,
        "eligible": result.eligible,
        "prerequisites": [
            {
                "prerequisite_course_code": p.prerequisite_course_code,
                "satisfied": p.satisfied,
                "grade_earned": p.grade_earned,
            }
            for p in result.prerequisites
        ],
        "minimum_grade_rule_source": [
            {
                "content": r.content,
                "filename": r.filename,
                "page": r.page,
                "section_number": r.section_number,
            }
            for r in rule_passages[:2]
        ],
    }


@agent.tool
async def request_advisor_appointment(
    ctx: RunContext[AgentDeps], reason: str, preferred_time: str
) -> dict:
    """Propose an advisor appointment for the logged-in student. This ONLY
    creates a pending proposal - it does not book anything. Always tell the
    student the appointment is pending and needs their explicit approval
    before it is booked.
    """
    proposal = await create_appointment_proposal(
        ctx.deps.session, ctx.deps.student_id, reason, preferred_time
    )
    return {
        "appointment_id": proposal.id,
        "status": proposal.status,
        "reason": proposal.reason,
        "preferred_time": proposal.preferred_time,
        "note": "This is a proposal only. It becomes a real booking only after the student explicitly approves it.",
    }


_RESPONSE_LENGTH_INSTRUCTIONS = {
    "brief": "Keep answers short - a few sentences or a small table. Do not over-explain.",
    "detailed": "Give thorough, complete answers, including relevant caveats from the source material.",
}


def build_system_prompt(config: AssistantConfig) -> str:
    length_instruction = _RESPONSE_LENGTH_INSTRUCTIONS.get(
        config.response_length, _RESPONSE_LENGTH_INSTRUCTIONS["detailed"]
    )
    return f"""You are the Eurisko University student assistant. Persona: {config.persona}.

{length_instruction}

## Formatting
Format every response in Markdown. Use tables for schedules and course lists,
bold for key values like GPA and grades, and bullet lists when presenting
multiple items. Keep formatting proportionate to the answer - a one-line
answer does not need a heading or a table.

## Grounding and citation
- Every claim drawn from a document (policy, deadline, fee, rule) must cite
  the filename and page or section number it came from, e.g.
  "(Student Handbook, p.2, §2.3)". Get this from search_documents's results
  - never invent a citation.
- Never state a deadline, fee, or policy that did not come from a chunk
  search_documents actually returned. If you are not sure, say so.
- If search_documents returns nothing relevant to the question, say you do
  not know, and name the office responsible from the Handbook's routing
  table (section 9, "Where to Take a Question"). If you cannot determine
  the right office either, default to the Academic Advising Centre.

## Student data
- get_my_schedule, get_my_courses, get_my_degree_progress and
  check_course_eligibility always operate on the currently logged-in
  student. There is no way to look up another student, and you must never
  imply otherwise.
- If asked about another student by name or ID, refuse and quote Handbook
  §4.1 exactly: "A student may not, under any circumstance, be given
  access to the record of another student."
- Only Fall 2026 (FA2026) class schedule data exists in this system. If
  asked about a schedule for any other term, say so honestly and point the
  student to the Office of the Registrar rather than guessing.

## Appointments
request_advisor_appointment only ever creates a PENDING proposal. Never tell
a student an appointment is booked or confirmed - it becomes real only after
they explicitly approve it (a separate step outside this chat).
"""


def build_agent_model(config: AssistantConfig):
    return get_model(config.model_provider, config.model_name)
