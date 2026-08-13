"""PDF parsing for the two source documents in data/.

Both documents are dense with borderless, whitespace-aligned tables (grading
scale, academic calendar, fee schedule, the office routing table, programme
requirement breakdowns). pdfplumber's built-in `extract_table()` line/text
strategies either find nothing (no ruling lines to detect) or, with the
"text" strategy run over a whole page, fragment prose paragraphs into
garbage multi-column "tables" and even split individual words into separate
cells (tested directly against this PDF: "Grading scale" came back as two
cells, ["Gradi", "ng scale"]).

So table extraction here works off `page.extract_words()` (still
pdfplumber - just its word-position API rather than its table-grid engine):
words are grouped into lines by y-position, a line is chosen as the header
by row shape (short, multi-column, no trailing period), and every
subsequent word is bucketed into whichever header column's x-range it falls
under. That fixed-column-boundary approach (rather than re-deriving column
gaps per line) is what makes multi-line cells work: a wrapped continuation
line has nothing under the first column, so it is detected as a
continuation of the previous row instead of a new one - the naive
per-line-gap approach spawned a bogus one-cell row for every wrapped line
in the "Handles" column of the office-routing table.

The Handbook (dense prose under numbered headings like "1.1", "2.3") and the
Catalogue (short structured course entries plus two kinds of requirement
tables) are genuinely different shapes, so they get different top-level
parsers below - but both share the line/column extraction primitives and
the same table-vs-prose classifier and row-bucketing routine.
"""

import re
from bisect import bisect_right
from dataclasses import dataclass

import pdfplumber

LINE_Y_TOLERANCE = 3
COLUMN_X_GAP = 15


@dataclass
class Line:
    page: int  # 1-indexed
    top: float
    text: str
    words: list[dict]


@dataclass
class RawUnit:
    """One piece of source content before chunking: either a prose section,
    one packable table row, or one catalogue course entry."""

    kind: str  # "prose" | "table_row" | "course"
    text: str
    page: int
    section_number: str | None
    section_title: str | None


def _cluster_lines(words: list[dict], page_number: int) -> list[Line]:
    words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))
    lines: list[Line] = []
    current: list[dict] = []
    current_top: float | None = None
    for w in words:
        if current_top is None or abs(w["top"] - current_top) > LINE_Y_TOLERANCE:
            if current:
                lines.append(_line_from_words(current, page_number))
            current = [w]
            current_top = w["top"]
        else:
            current.append(w)
    if current:
        lines.append(_line_from_words(current, page_number))
    return lines


def _line_from_words(words: list[dict], page_number: int) -> Line:
    words = sorted(words, key=lambda w: w["x0"])
    text = " ".join(w["text"] for w in words)
    return Line(page=page_number, top=words[0]["top"], text=text, words=words)


def _line_columns(line: Line, x_gap: float = COLUMN_X_GAP) -> list[str]:
    """Split one line's words into columns wherever the horizontal gap
    between consecutive words exceeds x_gap. Never breaks inside a word."""
    return [" ".join(w["text"] for w in group) for group in _line_column_words(line, x_gap)]


def _line_column_words(line: Line, x_gap: float = COLUMN_X_GAP) -> list[list[dict]]:
    words = line.words
    groups: list[list[dict]] = []
    current = [words[0]]
    for prev, cur in zip(words, words[1:]):
        if cur["x0"] - prev["x1"] > x_gap:
            groups.append(current)
            current = [cur]
        else:
            current.append(cur)
    groups.append(current)
    return groups


def _all_lines(pdf: pdfplumber.PDF) -> list[Line]:
    lines: list[Line] = []
    for page in pdf.pages:
        lines.extend(_cluster_lines(page.extract_words(), page.page_number))
    return lines


def _classify_section(lines: list[Line]) -> str:
    """A section is a "table" if most of its lines split into 2+ columns
    under the same x-gap that finds real table columns. Prose sections
    (justified paragraphs) essentially never do this consistently across
    lines; whitespace-aligned tables always do.
    """
    if not lines:
        return "prose"
    multi_col = sum(1 for ln in lines if len(_line_columns(ln)) >= 2)
    return "table" if multi_col / len(lines) >= 0.6 else "prose"


def _looks_like_header(cols: list[str]) -> bool:
    """Header rows here are short label lists ("Item Amount Charged",
    "Office Contact Handles") - multi-column, no column running past a
    handful of words, and not ending in sentence punctuation."""
    if len(cols) < 2:
        return False
    if any(c.strip().endswith((".", ",")) for c in cols):
        return False
    return all(len(c.split()) <= 4 for c in cols)


def _extract_table_units(
    lines: list[Line], caption: str, section_number: str | None, section_title: str | None
) -> tuple[list[RawUnit], list[Line]]:
    """Find the header row within `lines`, then bucket every following word
    into a column by fixed x-position (not per-line gaps), merging wrapped
    continuation lines into the previous row and treating short one-column
    lines with no other content as a running sub-caption (e.g. "Fall 2026"
    / "Spring 2027" inside the academic calendar).

    Returns (table_row units, leading lines that came before the header -
    i.e. a prose preamble the caller should emit separately).
    """
    header_index = None
    for i, ln in enumerate(lines):
        cols = _line_columns(ln)
        if _looks_like_header(cols):
            header_index = i
            break
    if header_index is None:
        return [], lines  # no real table found; caller treats it all as prose

    preamble = lines[:header_index]
    header_line = lines[header_index]
    header_cols = _line_columns(header_line)
    col_starts = sorted(w["x0"] for w in [grp[0] for grp in _line_column_words(header_line)])

    def bucket(line: Line) -> dict[int, list[str]]:
        row: dict[int, list[str]] = {}
        for w in line.words:
            idx = min(max(bisect_right(col_starts, w["x0"] + 1) - 1, 0), len(col_starts) - 1)
            row.setdefault(idx, []).append(w["text"])
        return {k: " ".join(v) for k, v in row.items()}

    units: list[RawUnit] = []
    current_row: dict[int, str] | None = None
    current_row_page: int | None = None
    sub_caption: str | None = None

    def flush():
        nonlocal current_row
        if current_row:
            full_caption = f"{caption}, {sub_caption}" if sub_caption else caption
            pairs = [
                f"{header_cols[idx].strip()}: {text.strip()}"
                for idx, text in sorted(current_row.items())
                if text.strip() and idx < len(header_cols)
            ]
            if pairs:
                units.append(
                    RawUnit(
                        kind="table_row",
                        text=f"{full_caption} — " + ", ".join(pairs),
                        page=current_row_page or header_line.page,
                        section_number=section_number,
                        section_title=section_title,
                    )
                )
        current_row = None

    _DANGLING_WORDS = {"and", "or", "of", "the", "for", "&", "to", "in", "with"}

    def _col0_open_ended(text: str) -> bool:
        """True if a row's accumulated column-0 text reads like it's mid-
        phrase (ends on a conjunction/preposition) - e.g. "Professional
        Practice and", which wraps onto its own line as "Capstone" starting
        back at column 0's x-position. Without this, that continuation
        looks exactly like a new row: it has column-0 content and other
        columns filled on the same line, the same shape genuine rows have.
        """
        words = text.strip().split()
        return bool(words) and words[-1].lower().rstrip(".,;:") in _DANGLING_WORDS

    for ln in lines[header_index + 1 :]:
        row = bucket(ln)
        row_text_joined = " ".join(row.values())
        if row_text_joined.strip() == " ".join(header_cols).strip():
            continue  # repeated header row (table continues after a page break)

        has_col0 = bool(row.get(0, "").strip())

        is_continuation = not has_col0 or (
            current_row is not None and _col0_open_ended(current_row.get(0, ""))
        )

        if is_continuation:
            if current_row is None:
                continue
            # Wrapped continuation of the previous row - append into
            # whichever columns have new text.
            for idx, text in row.items():
                if text.strip():
                    current_row[idx] = (current_row.get(idx, "") + " " + text).strip()
            continue

        # New leftmost content. A short, single-column line is a running
        # sub-caption (e.g. "Spring 2027"), not a data row.
        if len(row) == 1 and len(row[0].split()) <= 4:
            flush()
            sub_caption = row[0].strip()
            continue

        flush()
        current_row = row
        current_row_page = ln.page

    flush()
    return units, preamble


# --- Handbook: numbered sections, some of which are tables ------------------

# Section numbers in this document are always a single leading digit
# (optionally ".digit"), never two digits - the (?!\d) guard is what keeps
# calendar rows like "13 July 2026 Registration opens" from matching as a
# heading "13.".
_SECTION_HEADING = re.compile(r"^([1-9])(\.([1-9]))?(?!\d)\.?\s+([A-Z].*)$")


def _is_heading(text: str) -> re.Match | None:
    return _SECTION_HEADING.match(text.strip())


def _section_number_and_title(match: re.Match) -> tuple[str, str]:
    major, _, minor, title = match.groups()
    number = f"{major}.{minor}" if minor else major
    return number, title.strip()


def parse_handbook(path: str) -> list[RawUnit]:
    with pdfplumber.open(path) as pdf:
        lines = _all_lines(pdf)

    lines = [
        ln
        for ln in lines
        if not ln.text.strip().startswith("Eurisko University")
        and not ln.text.strip().startswith("Faculty of Engineering | Catalogue year")
    ]

    sections: list[tuple[str | None, str | None, list[Line]]] = []
    current_number: str | None = None
    current_title: str | None = None
    current_lines: list[Line] = []

    for line in lines:
        match = _is_heading(line.text.strip())
        if match:
            sections.append((current_number, current_title, current_lines))
            current_number, current_title = _section_number_and_title(match)
            current_lines = []
        else:
            current_lines.append(line)
    sections.append((current_number, current_title, current_lines))

    units: list[RawUnit] = []
    for number, title, sec_lines in sections:
        if not sec_lines:
            continue
        heading = f"{number} {title}" if number else (title or "Front matter")
        kind = _classify_section(sec_lines) if number is not None else "prose"

        if kind == "prose":
            text = " ".join(ln.text.strip() for ln in sec_lines if ln.text.strip())
            if text:
                units.append(
                    RawUnit(
                        kind="prose",
                        text=f"{heading}. {text}",
                        page=sec_lines[0].page,
                        section_number=number,
                        section_title=title,
                    )
                )
            continue

        table_units, preamble = _extract_table_units(sec_lines, heading, number, title)
        preamble_text = " ".join(ln.text.strip() for ln in preamble if ln.text.strip())
        if preamble_text:
            units.append(
                RawUnit(
                    kind="prose",
                    text=f"{heading}. {preamble_text}",
                    page=(preamble[0].page if preamble else sec_lines[0].page),
                    section_number=number,
                    section_title=title,
                )
            )
        units.extend(table_units)
    return units


# --- Catalogue: course entries + two shapes of requirement table -----------

_COURSE_HEADING = re.compile(r"^([A-Z]{2,4} \d{3}) (.+?) \((\d+) credits?\)$")
_SUBJECT_HEADER = re.compile(r"^[A-Za-z ]+\([A-Z]{2,4}\)$")
_PROGRAMME_NAME = re.compile(r"^(Computer Engineering \(BE-CENG\)|Mechanical Engineering \(BE-MECH\))$")


def _is_subject_header(text: str) -> bool:
    return bool(_SUBJECT_HEADER.match(text.strip()))


def parse_catalogue(path: str) -> list[RawUnit]:
    with pdfplumber.open(path) as pdf:
        lines = _all_lines(pdf)

    lines = [
        ln
        for ln in lines
        if not ln.text.strip().startswith("Eurisko University")
        and not ln.text.strip().startswith("Faculty of Engineering | Catalogue year")
    ]

    units: list[RawUnit] = []
    i = 0
    prose_buffer: list[Line] = []
    current_programme = "Degree requirement overview"

    def flush_prose():
        nonlocal prose_buffer
        text = " ".join(ln.text.strip() for ln in prose_buffer if ln.text.strip())
        if text:
            units.append(
                RawUnit(
                    kind="prose",
                    text=text,
                    page=prose_buffer[0].page,
                    section_number=None,
                    section_title="Overview",
                )
            )
        prose_buffer = []

    while i < len(lines):
        stripped = lines[i].text.strip()
        course_match = _COURSE_HEADING.match(stripped)
        looks_like_req_table_header = (
            _looks_like_header(_line_columns(lines[i])) and stripped.startswith("Category")
        )
        programme_match = _PROGRAMME_NAME.match(stripped)

        if programme_match:
            current_programme = programme_match.group(1)
            prose_buffer.append(lines[i])
            i += 1
            continue

        if looks_like_req_table_header:
            flush_prose()
            block_end = i + 1
            while block_end < len(lines):
                nxt = lines[block_end]
                nxt_stripped = nxt.text.strip()
                if _COURSE_HEADING.match(nxt_stripped) or _PROGRAMME_NAME.match(nxt_stripped):
                    break
                if _looks_like_header(_line_columns(nxt)) and nxt_stripped.startswith("Category"):
                    break
                # A full prose sentence marks the table's end - e.g. "Each
                # course lists its prerequisites. Where more than one is
                # listed ..." runs right after the last real row with no
                # heading in between, and wraps mid-sentence so it doesn't
                # necessarily end in a period on this particular line. The
                # threshold is deliberately generous (>10 words) because
                # legitimate wrapped table cells in these two tables top
                # out around 8 words ("PHYS 101, PHYS 102, CHEM 101, CMPS
                # 101") - narrower than that and it starts cutting off real
                # continuation lines instead of the trailing prose.
                cols = _line_columns(nxt)
                if len(cols) <= 1 and len(nxt_stripped.split()) > 10:
                    break
                block_end += 1
            caption = f"Programme requirement categories, {current_programme}"
            table_units, _ = _extract_table_units(lines[i:block_end], caption, None, caption)
            units.extend(table_units)
            i = block_end
            continue

        if course_match:
            flush_prose()
            code, title, _credits = course_match.groups()
            body_lines = [stripped]
            page = lines[i].page
            i += 1
            # A course entry runs until the next course heading (or a new
            # subject section) - description + Prerequisite(s) line always
            # travel together in one unit, so they can never be split
            # across chunks.
            while i < len(lines):
                nxt = lines[i].text.strip()
                if _COURSE_HEADING.match(nxt) or _is_subject_header(nxt):
                    break
                body_lines.append(nxt)
                i += 1
            units.append(
                RawUnit(
                    kind="course",
                    text=" ".join(body_lines),
                    page=page,
                    section_number=code,
                    section_title=f"{code} {title}",
                )
            )
            continue

        if not _is_subject_header(stripped):
            # A bare subject header ("Physics (PHYS)") carries no retrieval
            # value beyond what every course code under it already states,
            # and emitting it as its own tiny chunk was cascading into a
            # runaway merge of unrelated subjects (see chunking.py).
            prose_buffer.append(lines[i])
        i += 1

    flush_prose()
    return units
