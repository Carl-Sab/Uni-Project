"""Section-aware chunking over the RawUnits produced by pdf_parsing.

The 300-600 token target applies to Handbook PROSE (and table rows, which
get packed the same way). Catalogue course entries are the exception: a
course entry is treated as an ATOMIC unit and gets exactly one chunk each,
even at ~40 tokens - well under the 300 floor - and the under-100-token
merge rule specifically does NOT apply to them. Packing multiple course
entries per chunk was tried first and rejected: retrieving "prerequisites
for CENG 320" returned one chunk holding all 15 ENGR/MATH/PHYS courses, each
with its own prerequisite line, which is a mis-attribution risk (an agent
skimming that chunk could read a neighbouring course's prerequisite and
apply it to the one actually asked about) and it also flattened RRF
discrimination - every catalogue query scored near-identically because the
same giant chunk satisfied all of them. One course per chunk fixes both:
retrieval can score a single course's relevance distinctly, and there is
nothing else in the chunk an agent could misattribute a prerequisite to.

Table rows and course entries are never split internally by this module -
pdf_parsing already emits them as whole, indivisible RawUnits (one row, one
course entry), so packing can only ever combine whole units, never cut one
in half. That is what "never split a course entry from its prerequisite
line, and never split a table row from its header" reduces to here: the
header is already inlined into every row's text (see pdf_parsing's
"header: value" serialisation), and a course entry is one RawUnit end to
end.
"""

import re
from dataclasses import dataclass

import tiktoken

from app.services.pdf_parsing import RawUnit

TARGET_MIN_TOKENS = 300
TARGET_MAX_TOKENS = 600
MIN_FLOOR_TOKENS = 100

_encoding = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


@dataclass
class Chunk:
    content: str
    page: int
    section_number: str | None
    section_title: str | None
    doc_type: str


def _split_oversized_prose(unit: RawUnit) -> list[RawUnit]:
    """A prose unit over TARGET_MAX_TOKENS is split on sentence boundaries,
    greedily packed back up toward the target, so no single chunk blows past
    it just because its source section happened to be long.
    """
    if count_tokens(unit.text) <= TARGET_MAX_TOKENS:
        return [unit]

    sentences = re.split(r"(?<=[.!?])\s+", unit.text)
    pieces: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sentence in sentences:
        t = count_tokens(sentence)
        if current and current_tokens + t > TARGET_MAX_TOKENS:
            pieces.append(" ".join(current))
            current, current_tokens = [], 0
        current.append(sentence)
        current_tokens += t
    if current:
        pieces.append(" ".join(current))

    return [
        RawUnit(
            kind=unit.kind,
            text=piece,
            page=unit.page,
            section_number=unit.section_number,
            section_title=unit.section_title,
        )
        for piece in pieces
    ]


CATALOGUE_CONTEXT = "Eurisko University Undergraduate Course Catalogue — Course Descriptions"


def _course_chunk(unit: RawUnit, doc_type: str) -> Chunk:
    """One chunk per course entry, full stop - no packing, no under-100
    floor merge. The catalogue section context is prepended so the chunk
    reads standalone (a reader/embedder sees more than a bare "CENG 320
    Computer Architecture ... Prerequisite: CENG 310" fragment).
    """
    return Chunk(
        content=f"{CATALOGUE_CONTEXT}. {unit.text}",
        page=unit.page,
        section_number=unit.section_number,
        section_title=unit.section_title,
        doc_type=doc_type,
    )


def _section_key(unit: RawUnit) -> tuple:
    return (unit.kind, unit.section_number, unit.section_title)


def _pack_section(units: list[RawUnit], doc_type: str) -> list[Chunk]:
    """Greedily accumulate whole units (rows/sentences/course entries) up to
    TARGET_MAX_TOKENS, starting a new chunk once that would be exceeded.
    """
    chunks: list[Chunk] = []
    buffer: list[RawUnit] = []
    buffer_tokens = 0

    def flush():
        nonlocal buffer, buffer_tokens
        if not buffer:
            return
        content = "\n".join(u.text for u in buffer)
        chunks.append(
            Chunk(
                content=content,
                page=buffer[0].page,
                section_number=buffer[0].section_number,
                section_title=buffer[0].section_title,
                doc_type=doc_type,
            )
        )
        buffer, buffer_tokens = [], 0

    for unit in units:
        t = count_tokens(unit.text)
        if buffer and buffer_tokens + t > TARGET_MAX_TOKENS and buffer_tokens >= TARGET_MIN_TOKENS:
            flush()
        buffer.append(unit)
        buffer_tokens += t
        if buffer_tokens >= TARGET_MAX_TOKENS:
            flush()
    flush()
    return chunks


def _merge_undersized_chunks(chunks: list[Chunk]) -> list[Chunk]:
    """Final pass: any chunk under MIN_FLOOR_TOKENS gets absorbed into a
    neighbour (previous if one exists in the result so far, else the next
    chunk produced) rather than left as a fragment too small to carry
    useful context.
    """
    if not chunks:
        return chunks

    merged: list[Chunk] = []
    for chunk in chunks:
        if merged and count_tokens(chunk.content) < MIN_FLOOR_TOKENS:
            prev = merged[-1]
            merged[-1] = Chunk(
                content=prev.content + "\n" + chunk.content,
                page=prev.page,
                section_number=prev.section_number,
                section_title=prev.section_title,
                doc_type=prev.doc_type,
            )
        else:
            merged.append(chunk)

    # A lone first chunk that's still tiny (no predecessor to absorb into)
    # gets folded into whatever follows it instead.
    if len(merged) > 1 and count_tokens(merged[0].content) < MIN_FLOOR_TOKENS:
        first, second = merged[0], merged[1]
        merged[1] = Chunk(
            content=first.content + "\n" + second.content,
            page=first.page,
            section_number=first.section_number,
            section_title=first.section_title,
            doc_type=second.doc_type,
        )
        merged = merged[1:]

    return merged


def chunk_units(units: list[RawUnit], doc_type: str) -> list[Chunk]:
    # Course entries bypass packing and the undersized-chunk merge entirely
    # - see the module docstring for why. Everything else (prose, table
    # rows) goes through the normal 300-600 token packing pipeline.
    course_chunks = [_course_chunk(u, doc_type) for u in units if u.kind == "course"]
    packable_units = [u for u in units if u.kind != "course"]

    expanded: list[RawUnit] = []
    for unit in packable_units:
        expanded.extend(_split_oversized_prose(unit) if unit.kind == "prose" else [unit])

    chunks: list[Chunk] = []
    current_section: list[RawUnit] = []
    current_key = None
    for unit in expanded:
        key = _section_key(unit)
        if current_key is not None and key != current_key:
            chunks.extend(_pack_section(current_section, doc_type))
            current_section = []
        current_key = key
        current_section.append(unit)
    if current_section:
        chunks.extend(_pack_section(current_section, doc_type))

    return course_chunks + _merge_undersized_chunks(chunks)
