from app.services.concatenation_check import (
    check_chunks_for_concatenation,
    find_case_transition_merges,
    find_dictionary_split_merges,
)


def test_case_transition_catches_glued_heading():
    warnings = find_case_transition_merges("the policyStudent Handbook says so")
    assert any(w.token == "policyStudent" for w in warnings)


def test_case_transition_clean_text_has_no_warnings():
    assert find_case_transition_merges("A student may not register for a course.") == []


def test_dictionary_split_catches_known_regression_examples():
    # Only the CLEAN corpus goes into known_words - if the buggy text were
    # included too, "maynot" would trivially become "known" as itself.
    clean_corpus = [
        "A student may not register for a course without approval.",
        "You may accumulate no more than four W notations.",
        "See the schedule for upcoming terms and registration details.",
    ]
    from app.services.concatenation_check import _build_known_words

    known_words = _build_known_words(clean_corpus)

    for bad_text, expected_token in [
        ("A student maynot register for a course", "maynot"),
        ("youmay accumulate no more than four W notations", "youmay"),
        ("schedules for upcoming termsand registration details", "termsand"),
    ]:
        warnings = find_dictionary_split_merges(bad_text, known_words)
        assert any(w.token == expected_token for w in warnings), (bad_text, warnings)


def test_dictionary_split_does_not_flag_words_never_seen_split_elsewhere():
    # "Eurisko" never appears split into two standalone words anywhere in
    # the corpus, so it must not be flagged just for being unfamiliar.
    corpus = ["Eurisko University is a Faculty of Engineering."]
    from app.services.concatenation_check import _build_known_words

    known_words = _build_known_words(corpus)
    warnings = find_dictionary_split_merges("Eurisko", known_words)
    assert warnings == []


def test_check_chunks_runs_both_heuristics_across_corpus():
    chunks = [
        "A student may not register for a course.",
        "You, the student, are responsible for fees and notations.",
        "youmay accumulate no more than four notations",
    ]
    warnings = check_chunks_for_concatenation(chunks)
    assert any(w.token == "youmay" for w in warnings)
