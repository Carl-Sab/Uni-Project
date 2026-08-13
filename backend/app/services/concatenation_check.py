"""Flags likely missing-space concatenations in chunk text before/at
ingestion, so a word-joining regression in pdf_parsing.py surfaces as a
loud warning at ingest time instead of silently reaching a chat answer and
its citations.

Two independent heuristics, since they catch different failure shapes:

1. Case-transition merges: a lowercase letter directly followed by an
   uppercase one ("wordWord") - typically a heading, acronym, or new
   sentence glued onto the previous token.

2. Corpus self-consistency merges: a token that isn't found as a standalone
   word anywhere in this document's own text, but splits into two
   substrings that ARE both standalone words elsewhere in the document
   ("maynot" -> "may" + "not", when "may" and "not" both appear elsewhere
   as their own tokens). This needs no external dictionary - the document
   is its own reference corpus - but it necessarily flags some genuine
   compound words too ("without" -> "with"+"out", "outstanding" ->
   "out"+"standing"). That's an acceptable false-positive rate for a
   warning that a human skims at ingestion time, not a hard gate that
   blocks it.
"""

import re
from dataclasses import dataclass

_CASE_TRANSITION = re.compile(r"[a-z][A-Z]")
_WORD = re.compile(r"[a-zA-Z]+")

MIN_SPLIT_TOKEN_LEN = 6
MIN_PART_LEN = 2


@dataclass(frozen=True)
class ConcatenationWarning:
    token: str
    kind: str  # "case_transition" | "dictionary_split"
    context: str
    split: tuple[str, str] | None = None


def _build_known_words(texts: list[str]) -> set[str]:
    known: set[str] = set()
    for text in texts:
        known.update(t.lower() for t in _WORD.findall(text) if len(t) >= MIN_PART_LEN)
    return known


def find_case_transition_merges(text: str) -> list[ConcatenationWarning]:
    warnings = []
    for token in _WORD.findall(text):
        if _CASE_TRANSITION.search(token):
            idx = text.find(token)
            context = text[max(0, idx - 20) : idx + len(token) + 20]
            warnings.append(ConcatenationWarning(token=token, kind="case_transition", context=context))
    return warnings


def find_dictionary_split_merges(text: str, known_words: set[str]) -> list[ConcatenationWarning]:
    # Deliberately does NOT skip tokens already present in known_words.
    # known_words is built from the same corpus being checked (see
    # check_chunks_for_concatenation), so a merge artifact that appears
    # even once would register itself as "known" and evade detection
    # against its own occurrence - the exact case this function exists to
    # catch. The tradeoff is that a genuine repeated word which also
    # happens to split into two other known words ("outstanding") gets
    # flagged too; acceptable for an advisory, human-reviewed warning.
    warnings = []
    for token in set(_WORD.findall(text)):
        low = token.lower()
        if len(low) < MIN_SPLIT_TOKEN_LEN:
            continue
        for i in range(MIN_PART_LEN, len(low) - MIN_PART_LEN + 1):
            a, b = low[:i], low[i:]
            if a in known_words and b in known_words:
                idx = text.find(token)
                context = text[max(0, idx - 20) : idx + len(token) + 20]
                warnings.append(
                    ConcatenationWarning(
                        token=token, kind="dictionary_split", context=context, split=(a, b)
                    )
                )
                break
    return warnings


def check_chunks_for_concatenation(chunk_texts: list[str]) -> list[ConcatenationWarning]:
    """Run both heuristics across a whole document's chunks at once - the
    dictionary-split check needs the full corpus to build its known-word
    set, so it can't run per-chunk in isolation.
    """
    known_words = _build_known_words(chunk_texts)
    warnings: list[ConcatenationWarning] = []
    for text in chunk_texts:
        warnings.extend(find_case_transition_merges(text))
        warnings.extend(find_dictionary_split_merges(text, known_words))
    return warnings
