from bolsa_finder.eligibility import (
    assess_capes_pdse,
    assess_daad_cofunded_grant,
    find_evidence,
)


def test_find_evidence_returns_excerpt_around_keyword() -> None:
    text = "A" * 300 + " the keyword phrase here " + "B" * 300

    evidence = find_evidence(text, ["keyword phrase"], context_chars=10)

    assert "keyword phrase" in evidence
    assert len(evidence) < len(text)


def test_find_evidence_returns_none_when_no_keyword_matches() -> None:
    assert find_evidence("nothing relevant here", ["unrelated keyword"]) is None


def test_assess_capes_pdse_likely_when_institutional_selection_text_present() -> None:
    page_text = (
        "O candidato deve atender aos requisitos para candidatura previstos no edital "
        "durante o processo seletivo interno em sua Instituição."
    )

    level, evidence = assess_capes_pdse(page_text)

    assert level == "likely"
    assert "processo seletivo interno" in evidence


def test_assess_capes_pdse_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_capes_pdse("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_daad_confirmed_when_explicit_brazil_clause_present() -> None:
    page_text = (
        "Who can apply? Doctoral candidates at universities in Brazil, who have "
        "been awarded a domestic scholarship from CAPES."
    )

    level, evidence = assess_daad_cofunded_grant(page_text)

    assert level == "confirmed"
    assert "doctoral candidates at universities in Brazil".lower() in evidence.lower()


def test_assess_daad_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_daad_cofunded_grant("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None
