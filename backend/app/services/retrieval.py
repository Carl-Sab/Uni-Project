"""Hybrid retrieval: pgvector cosine search + Postgres full-text search,
merged by reciprocal rank fusion.

Why hybrid and not just one of the two:

- Pure vector search fails on exact tokens like "CENG 320" or "USD 385".
  text-embedding-3-small embeds *meaning*; a course code or a dollar amount
  carries almost no distributed semantic content for the model to place
  precisely - "CENG 320" and "CENG 310" land close together in embedding
  space (both "a computer engineering course code"), so vector search alone
  can easily surface the wrong course or the wrong fee row when the query is
  really just asking to match a literal token.

- Pure keyword (full-text) search fails on "what happens if I fail a
  course" because the Handbook never uses that phrasing - the relevant text
  says "a grade of F" and "must be repeated," not "fail." `tsquery` matches
  lexemes, not meaning, so a query with none of the source document's exact
  words returns nothing useful even though the passage is exactly the
  answer.

Running both and fusing with RRF gets exact-token precision from FTS and
paraphrase/semantic recall from vector search, without having to guess in
advance which kind of query is coming in.
"""

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embeddings import embed_text

VECTOR_TOP_K = 20
FTS_TOP_K = 20
RRF_K = 60
FINAL_TOP_K = 5


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: int
    content: str
    filename: str
    page: int
    section_number: str | None
    section_title: str | None
    doc_type: str
    score: float


_VECTOR_SQL = text(
    """
    SELECT id, embedding <=> (:qvec)::vector AS distance
    FROM doc_chunks
    ORDER BY embedding <=> (:qvec)::vector
    LIMIT :limit
    """
)

_FTS_SQL = text(
    """
    SELECT id, ts_rank(tsv, plainto_tsquery('english', :query)) AS rank
    FROM doc_chunks
    WHERE tsv @@ plainto_tsquery('english', :query)
    ORDER BY rank DESC
    LIMIT :limit
    """
)

_CHUNK_LOOKUP_SQL = text(
    """
    SELECT c.id, c.content, c.page, c.section_number, c.section_title, c.doc_type, d.filename
    FROM doc_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE c.id = ANY(:ids)
    """
)


def _vector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(repr(x) for x in embedding) + "]"


async def hybrid_search(session: AsyncSession, query: str, top_k: int = FINAL_TOP_K) -> list[RetrievalResult]:
    query_embedding = await embed_text(query)

    vector_rows = (
        await session.execute(
            _VECTOR_SQL, {"qvec": _vector_literal(query_embedding), "limit": VECTOR_TOP_K}
        )
    ).all()
    fts_rows = (await session.execute(_FTS_SQL, {"query": query, "limit": FTS_TOP_K})).all()

    # Reciprocal rank fusion: rank (not raw score) from each list, k=60 -
    # this is what makes cosine distance and ts_rank comparable at all,
    # since they live on completely different, non-comparable scales.
    rrf_scores: dict[int, float] = {}
    for rank, row in enumerate(vector_rows, start=1):
        rrf_scores[row.id] = rrf_scores.get(row.id, 0.0) + 1.0 / (RRF_K + rank)
    for rank, row in enumerate(fts_rows, start=1):
        rrf_scores[row.id] = rrf_scores.get(row.id, 0.0) + 1.0 / (RRF_K + rank)

    if not rrf_scores:
        return []

    ranked_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

    chunk_rows = (await session.execute(_CHUNK_LOOKUP_SQL, {"ids": ranked_ids})).all()
    by_id = {row.id: row for row in chunk_rows}

    return [
        RetrievalResult(
            chunk_id=cid,
            content=by_id[cid].content,
            filename=by_id[cid].filename,
            page=by_id[cid].page,
            section_number=by_id[cid].section_number,
            section_title=by_id[cid].section_title,
            doc_type=by_id[cid].doc_type,
            score=rrf_scores[cid],
        )
        for cid in ranked_ids
        if cid in by_id
    ]
