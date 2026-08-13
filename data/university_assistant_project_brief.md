# University Assistant — Project Brief

**Eurisko AI Academy**

---

## 1. What you are building

A web application for a university, with two surfaces:

- A **student portal**, where a student logs in, sees their own academic record, and talks to an assistant that can answer questions about both university policy and their personal situation.
- An **admin panel**, where a university administrator uploads the documents the assistant answers from, and reviews the data behind it.

The assistant has to do two fundamentally different things and know which one a question needs:

1. Answer from **documents** — policies, deadlines, fees, course descriptions, degree rules. This is retrieval over unstructured text.
2. Answer from **the student's own record** — schedule, grades, courses taken, degree progress. This is a query against structured data, scoped to the logged-in student and nobody else.

Many real questions need both. *"Am I allowed to register for MECH 310?"* requires the prerequisite list from the Course Catalogue, the minimum-grade rule from the Student Handbook, **and** that student's transcript. An assistant that only does one of these will fail visibly.

---

## 2. Why this project

Every team gets **identical data**. Nobody has an advantage from a better dataset, a cleaner corpus, or more records.

What differs is what you build on top of it: how you model and store the data, how you index and retrieve the documents, how you design the agent and its tools, and how fast and how consistently the whole thing answers.

If we ask two teams the same question, we should be able to compare the answers directly — and the difference we see will be architecture, not luck.

---

## 3. The two surfaces

### 3.1 Student portal

A student logs in with their student ID. No password infrastructure is needed — a student ID is enough. What matters is that the logged-in identity is carried through every layer of the system and used to scope every data access.

The portal must show, for the logged-in student only:

- Profile: name, programme, entry term, expected graduation term, academic standing, advisor
- Current term schedule: courses, days, times, rooms, instructors
- Academic history: every course taken, by term, with grades and credits
- Cumulative GPA and total credits earned
- **Degree progress**: for each requirement category, credits earned against credits required, and what remains
- A **chat panel** with the assistant

### 3.2 Admin panel

A separate login. The admin is not a student and does not have a student record.

**Document management (required)**
- Upload a document
- See what is currently indexed, and when
- Remove a document, and have it disappear from the assistant's answers
- Re-run ingestion when a document changes

**Data views (required)**
- Browse students, with their programme and standing
- Browse courses, with credits and prerequisites
- Browse enrollments, filterable by student and by term

**Assistant behaviour configuration (required, keep it small)**

The assistant's behaviour should not be hardcoded. An administrator should be able to change it without touching code. A few settings are enough:

- Tone / persona (e.g. formal vs. friendly)
- Which model the assistant uses — GPT-5, Claude Sonnet 4.5 or Gemini 3 Flash
- Response length (brief vs. detailed)
- Creativity / temperature

Changing any of these should take effect on the next message, without a restart or a redeploy.

---

## 4. The chatbot

The assistant answers through **tools**. It does not get handed the whole database and it does not get handed the whole document set — it decides what to call, and each tool returns only what it should.

Required tools:

| Tool | Returns | Scoped to student? |
|---|---|---|
| `search_documents(query)` | Relevant passages from the indexed documents | No |
| `get_my_schedule()` | Current-term classes with days, times, rooms, instructors | **Yes** |
| `get_my_courses()` | Courses taken and in progress, with grades | **Yes** |
| `get_my_degree_progress()` | Credits earned vs. required, per requirement category | **Yes** |
| `check_course_eligibility(course_code)` | Whether the student may register, and why or why not | **Yes** |
| `request_advisor_appointment(...)` | A **proposed** appointment, pending approval | **Yes** |

`check_course_eligibility` is the interesting one. It has to combine the course's prerequisites, the minimum-grade rule from the Handbook, and the student's transcript. Get this right and the rest of the hybrid questions tend to fall out of it.

`request_advisor_appointment` is the human-in-the-loop case. The agent must **not** book anything on its own. It proposes the action, the user sees what will happen, and it only executes after explicit approval.

---

## 5. Required behaviour

These are not features. They are rules the assistant must follow every time.

1. **Grounded answers only.** Document questions are answered from retrieved content. If the answer is not in the documents, say so and point to the right contact. Never invent a deadline, a fee, or a policy.

2. **Strict data scoping.** A student can only ever see their own record. This must be enforced in the tool and data layer using the authenticated student ID — not by asking the model nicely. If a student asks about another student, the assistant refuses.

3. **Session memory.** Follow-ups resolve from context. *"What about next term?"* should work without repeating the whole question.

4. **Honest uncertainty.** "I don't know" is a correct answer. A confident wrong answer is the worst possible outcome — this is a university, and a fabricated deadline has real consequences.

5. **Cite the source** for document-based answers, so an answer can be checked.

---

## 6. The data we give you

Three files, and nothing else. Everything the assistant knows has to come from them.

### `Eurisko_University_Course_Catalogue_2026-2027.pdf`

5 pages. The degree structure, the five requirement categories and how they interact, both programmes with their credit distributions, and all 33 course descriptions with prerequisites.

This is where a question like *"what are the prerequisites for CENG 320?"* or *"how many credits do I need in General Education?"* is answered.

### `Eurisko_University_Student_Handbook_2026-2027.pdf`

6 pages. Grading and GPA calculation, academic standing and probation, repeating courses, course load limits, prerequisite rules, add/drop/withdrawal, graduation requirements, academic integrity and privacy, the academic calendar, tuition and fees, financial aid, student services, and a routing table naming the office responsible for each kind of enquiry.

This is where *"when is the last day to drop a course?"*, *"what happens if I fail a course?"* and *"how is my GPA calculated?"* are answered.

### `Eurisko_University_Data.xlsx`

The structured data, as nine flat sheets:

| Sheet | Contents |
|---|---|
| `Terms` | Academic terms, oldest first |
| `Program_Requirements` | The two programmes and the five requirement categories of each, with credits required |
| `Courses` | All 33 courses with credits and descriptions |
| `Category_Courses` | Which courses may satisfy which requirement category |
| `Course_Prerequisites` | One row per prerequisite; several rows for one course means all are required |
| `Students` | The five students |
| `Enrollments` | Every course each student has taken or is taking, with grades |
| `Class_Schedule_FA2026` | The courses running this term, with day, time, room and instructor |
| `Grading_Scale` | Grade to grade-point mapping, and which grades earn credit or count toward the GPA |

**The spreadsheet is deliberately flat.** No keys, no types, no indexes, no constraints are declared. Designing all of that is your work, and it is the main thing that distinguishes one team's project from another's.

### The five students

These are your login identities.

| Student ID | Name | Programme |
|---|---|---|
| S2023011 | Maya Haddad | Computer Engineering |
| S2023027 | Jad Mansour | Computer Engineering |
| S2024019 | Karim Nassar | Mechanical Engineering |
| S2025008 | Rania Khoury | Mechanical Engineering |
| S2026042 | Lynn Abou Chakra | Computer Engineering |

They are not five copies of the same situation. One is a term from graduating; one has plenty of credits but has not started the capstone track; one is on probation and repeating failed courses; one has just started and has no completed courses at all. Test against all five, not just the easy one.

---

## 7. What you must figure out

There is no prescribed answer to any of this.

**Data modelling and storage**
- Which database, or databases. One store, or one per job?
- Your schema, from flat sheets to something you can query properly.
- How to model the many-to-many relationship between requirement categories and courses. A course can satisfy a category in one programme and not in another.
- Where the degree-progress calculation lives: in the database, or in application code.
- Indexes. What do you actually query, and what will be slow without one?

**Documents and retrieval**
- How to parse the PDFs. They are not uniform — one is dense prose, the other is short structured entries and tables.
- Chunk size and strategy. A chunk that splits a table row from its header is useless.
- Embedding model, vector store, index type.
- Retrieval strategy: pure vector search, keyword, hybrid, metadata filtering, reranking. Whatever you can justify.
- How ingestion re-runs when an admin uploads or removes a document.

**The agent**
- Tool granularity. Six tools as listed, or fewer and smarter, or more and simpler?
- How the authenticated student ID reaches every tool.
- How conversation state is stored and how much history is passed.
- Prompt design, and how the admin's behaviour config compiles into it.
- How the human-in-the-loop approval gate actually works.

**Performance**
- Caching. What is worth caching, and when does it go stale?
- Keeping retrieval fast as the document set grows.
- Ingestion time — a slow re-index is a real cost to the admin.

---

## 8. Deliverables

- [ ] **Running application**, started with a single `docker compose up`
- [ ] **Backend API** with documented endpoints (Swagger is enough)
- [ ] **Ingestion pipeline** — parse, chunk, embed, index; re-runnable from the admin panel
- [ ] **Agent** with the tools in section 4, every personal-data tool scoped to the logged-in student
- [ ] **Student portal UI** — record views plus the chat panel
- [ ] **Admin panel UI** — document management, data views, behaviour configuration
- [ ] **README** containing:
  - How to run it, from clone to working app
  - An architecture diagram
  - Your database schema
- [ ] **DESIGN.md** — one to two pages answering:
  - Which database(s) you chose and why
  - Your chunking and retrieval strategy and why
  - What you cached and why
  - What you would do differently with another two weeks

---

## 9. Technology

**Fixed** — so the comparison is about your design, not your stack:

| Layer | Tool |
|---|---|
| Backend | FastAPI |
| Agent framework | PydanticAI |
| Frontend | React |
| Containerisation | Docker + Docker Compose |
| Package management | `uv` |
| Version control | Git, with a shared repository per team |

**Your choice:**

- Database(s) — PostgreSQL, MongoDB, Elasticsearch, or a combination. You have seen all three.
- Vector store and embedding model

---

## 10. Suggested build order

You are free to work however you like, but this order front-loads the risk.

1. **Model and load the data.** Get the spreadsheet into your database with a schema you can defend. Verify by hand: compute Maya's GPA and check it against the sheet.
2. **Build the plain queries first** — schedule, courses taken, degree progress — as API endpoints, no agent involved. If these are wrong, nothing downstream can be right.
3. **Ingest the documents.** Parse, chunk, embed, index. Test retrieval directly with a handful of policy questions before any agent touches it.
4. **Wire the agent and its tools.** Start with two tools, get scoping right, then add the rest.
5. **Add eligibility and the human-in-the-loop appointment.** These depend on everything above.
6. **Build the UIs.** Student portal, then admin panel.
7. **Write DESIGN.md.** Do not leave it to the last day.

A tip on step 1: your degree-progress logic should work for both programmes without being written twice. If you find yourself writing `if programme == "BE-CENG"`, your data model is fighting you.
