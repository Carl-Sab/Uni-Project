# Design notes

Honest engineering notes on the decisions that shaped this system, what they cost, and what I'd
do differently with more time. Not a feature list — see README.md for that.

## Database: one Postgres (with pgvector), not a separate vector store

Everything lives in one Postgres 16 instance with the pgvector extension: structured data
(students, enrollments, courses, ...) and the RAG index (`documents` / `doc_chunks`, with a
`vector(1536)` column and a `tsvector` column on the same table) side by side.

The alternative was a dedicated vector store (Pinecone/Weaviate/Qdrant) or Elasticsearch for
full-text, with Postgres kept for structured data only. I didn't do that, for three reasons:

- **Scale doesn't demand it.** Two source PDFs produce a few hundred chunks. pgvector's exact or
  IVFFlat search is fine at this size; the operational case for a purpose-built vector store shows
  up in the tens-of-millions-of-vectors range, not here.
- **Hybrid retrieval wants both signals in the same query planner.** RRF (below) merges a
  vector-similarity ranking with a full-text ranking. Doing that across two different systems
  means running two round trips, in two different score spaces, and manually correlating IDs
  in application code — versus two `SELECT`s against the same table here, or in principle one
  query. Keeping both in Postgres made the merge code (`app/services/retrieval.py`) trivial.
  Same reasoning against Elasticsearch: it's a fine full-text engine, but it doesn't do vector
  similarity in a way that composes cleanly with a `tsvector` rank from a different system.
  Add either as a separate service and I'd still be fusing scores across a network hop.
- **One fewer moving part.** No second database means no second connection pool, no second
  backup/restore story, no second thing that can be down while the other is up, no
  cross-database transactional inconsistency between "chunk indexed" and "document status
  updated."

**What this gives up:** pgvector's ANN indexing (IVFFlat/HNSW) is genuinely weaker at very large
scale and very high recall requirements than a system built for nothing else. If the corpus grew
from two PDFs to the entire university's document set (thousands of documents, tens of thousands
of chunks), I'd expect to hit the point where a dedicated vector store's indexing and filtering
story pays for the operational overhead of running it. That point is nowhere near where this
system is now, but it's a real limit, not a hypothetical one.

## Chunking: section-aware, not fixed-size — and course entries are atomic

Handbook prose (and table rows) are packed to a 300–600 token target, respecting section
boundaries — a chunk never straddles two sections, and a table row is never split from the header
context it needs to be read standalone (see `app/services/chunking.py`). Catalogue course entries
are the deliberate exception: **one course = one chunk, always**, even when that chunk is
~40 tokens, well under the 300 floor, and skips the undersized-chunk merge pass entirely.

That exception exists because of a bug the first version of chunking actually had: packing
catalogue entries into the same 300–600 token buckets as prose put up to **15 course entries in a
single chunk**. Two things broke:

1. **RRF discrimination went flat.** Every catalogue-flavored query (course descriptions,
   prerequisites, credit counts) tended to retrieve the *same* giant chunk, because that chunk's
   embedding and full-text content matched a broad swath of catalogue vocabulary. Reciprocal rank
   fusion has nothing to discriminate on when the same chunk id keeps winning regardless of which
   specific course was actually asked about.
2. **Prerequisite mis-attribution risk.** A chunk holding 15 courses' worth of "Prerequisite: ..."
   lines is a chunk where an agent (or a human skimming it) can visually associate the wrong
   prerequisite line with the wrong course code — they're stacked right next to each other with no
   structural separation stronger than a newline.

Making each course entry its own chunk fixes both: retrieval can score one course's relevance
distinctly from its neighbours, and there is nothing else in the chunk to misattribute a
prerequisite to. The cost is a lot of very small chunks (well under the "normal" 300-token floor)
in the doc_chunks table for the Catalogue — accepted deliberately, with a comment at the top of
`chunking.py` explaining why the floor doesn't apply there.

## Retrieval: hybrid vector + full-text, merged by RRF at k=60

`hybrid_search` (`app/services/retrieval.py`) runs a pgvector cosine-distance query and a Postgres
full-text (`tsvector`/`plainto_tsquery`) query in parallel against `doc_chunks`, then merges them
by reciprocal rank fusion (`1/(k+rank)` per list, `k=60`, standard RRF) rather than trying to
combine raw scores — cosine distance and `ts_rank` live on completely different, non-comparable
scales, so rank-based fusion is what makes them combinable at all.

Why not just one of the two:

- **Pure vector search fails on exact tokens.** A course code like "CENG 320" or a dollar figure
  like "USD 385" carries almost no distributed semantic content for an embedding model to place
  precisely — "CENG 320" and "CENG 310" land close together in embedding space (both read as "a
  computer engineering course code"), so vector search alone can easily surface the wrong course
  or the wrong fee row when the query is really just asking to match a literal token.
- **Pure full-text search fails on paraphrase.** "What happens if I fail a course and have to
  repeat it?" shares almost no vocabulary with the Handbook's actual phrasing ("a grade of F,"
  "must be repeated"). `tsquery` matches lexemes, not meaning, so a query using none of the source
  document's exact words returns nothing, even though the relevant passage answers it directly.

Running both and fusing gets exact-token precision from full-text and paraphrase/semantic recall
from vector search, without having to classify the query type in advance.

## No reranker — deliberately, for now

There's no cross-encoder reranking pass after RRF. That's a corpus-size call, not a belief that
reranking doesn't help: with a few hundred chunks total, RRF over `VECTOR_TOP_K=20` and
`FTS_TOP_K=20` candidates already produces a clean top-5, and a reranker's main value — cleaning
up noisy candidate sets pulled from a much larger corpus — doesn't have much to bite on here. It
also adds a model call (latency and cost) to every retrieval.

**What I'd do differently:** if the corpus grew substantially (more documents, more chunk
diversity, queries pulling in more marginal candidates), a reranking pass over the RRF-merged
top-K would be the next retrieval-quality lever, ahead of anything more elaborate — cheap to add
on top of the existing pipeline since it slots in right before `FINAL_TOP_K` truncation.

## Caching: two things, cached-aside in Redis

Two — and only two — things are cached, both cache-aside with an explicit TTL and an explicit
invalidation path:

| What | Key | TTL | Invalidated on |
|---|---|---|---|
| Degree progress | `progress:{student_id}` | 1h | Any write to that student's enrollments |
| Retrieval results | `retr:{sha256(lower(query))}` | 24h | Any document upload, re-index, or delete |

`compute_category_progress` runs several joins per requirement category (courses, prerequisites,
best-attempt dedup) and is read on every profile/degree-progress view; caching it per student
knocks the common-path read down from a real query to a Redis GET. `hybrid_search` pays for an
embedding API call on every miss — by far the largest cost in the whole request — so caching the
merged result under a normalized-query hash turns a repeated question into a cache hit instead of
a second embedding call.

**Explicitly not cached: LLM responses.** This was a hard line, not an oversight. The assistant's
persona, model, and temperature are admin-configurable at `/api/admin/config` and are read fresh
on every chat request specifically so an admin's change takes effect on the very next message. If
LLM responses were cached by question text, a student could receive a stale answer generated under
the *previous* persona/model/config — the assistant would silently be lying about which version of
itself is currently talking, with no way for the student to know. The two things that are cached
have no such coupling: degree progress reflects the database exactly as of the last write, and
retrieval results reflect the indexed documents exactly as of the last ingest — neither depends on
"which persona is active right now."

**Invalidation caveat, stated plainly:** there is currently no API endpoint anywhere in this
codebase that writes to `enrollments` — enrollment data is seed-only, loaded once at boot by
`load_data.py`. `invalidate_progress_cache(student_id)` exists in `app/services/academic.py` and
is ready to be called from wherever a future enrollment-writing endpoint lands, but as of now it
has no caller. That's a real gap between the letter of "invalidated on any write" and what the
system currently does, worth being honest about rather than papering over with a caller that
doesn't actually enroll anyone.

### Measured latency (real numbers, this stack, this machine)

**Document question** ("What happens if I fail a course and have to repeat it?" — via
`hybrid_search`, isolated from LLM generation time):

- Cold (cache miss, includes the embedding API call): **~2800 ms**
- Warm (cache hit): **~0.8 ms**

**Record question** (`GET /api/me/degree-progress` for S2023011, full HTTP round trip):

- Cold (cache miss): **~101 ms**
- Warm (cache hit): **~16–37 ms**

The retrieval cache's win is almost entirely about avoiding the embedding API round trip — that's
where nearly all 2.8s of the cold path goes. The degree-progress cache's win is smaller in
absolute terms (it was never slow) but still a real ~3–6x cut in the fast path's cost, and it's
the endpoint hit most repeatedly by a student re-checking their progress in one session.

## Scoping model: `student_id` never leaves the JWT

Every student-scoped route depends on `get_current_student`, which decodes the JWT and returns the
`student_id` it names — nothing else. No route under `/api/me/*` or `/api/chat`, and no agent
tool, accepts a `student_id` as a query parameter, path parameter, or request body field. The
service-layer functions in `app/services/academic.py` all take `student_id` as an explicit
argument, but callers only ever pass in the value that came out of `get_current_student` — there's
no code path where a client-supplied ID reaches those functions instead.

The one deliberate exception is `GET /api/admin/students/{student_id}`, which *does* take a
`student_id` from the URL path — but it sits behind `require_admin`, a completely separate
dependency from `get_current_student`, and is the only route in the codebase where that pattern is
allowed. It's audited by being exactly one route, clearly commented as the exception in
`app/api/admin.py`, rather than a pattern that's easy to accidentally reuse elsewhere.

This is the property that makes "cache keyed by `student_id`" safe in the first place: since the
key can only ever be the token holder's own ID (or, for the admin route, is never cached at all),
there's no way for the progress cache to leak one student's data to another via a manipulated
parameter.

## What I'd do differently with two more weeks

- **Wire up an actual enrollment-write endpoint** (grade posting, add/drop) and hang
  `invalidate_progress_cache` off it for real, instead of it being a currently-uncalled hook.
- **Add a reranking pass** once there's a reason to — either a larger corpus or evidence (from
  real usage, not synthetic tests) that RRF's top-5 is missing good candidates.
- **Cache warming for retrieval:** the 24h TTL plus full-namespace flush on any document change
  means the first query after any admin edit pays full embedding-call cost again, for every
  distinct question, until each is asked once. A background job that re-warms a fixed set of
  common questions after a flush would smooth that out.
- **Structured eval for retrieval quality**, not just the manual/ad hoc query checks
  (`app/scripts/test_retrieval.py`) that exist today — a small labeled query/expected-chunk set
  that could catch a regression like the 15-courses-in-one-chunk bug automatically instead of by
  noticing the symptom in a live answer.
- **Redis as a hard dependency, currently.** If Redis is down, both cache-aside paths currently
  have no fallback wrapped around the `redis.get`/`redis.set` calls — a Redis outage would 500
  requests that would otherwise succeed against Postgres alone. Worth wrapping in a try/except
  that degrades to "just hit the database" rather than failing the request.
