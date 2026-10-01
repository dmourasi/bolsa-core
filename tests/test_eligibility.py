from bolsa_finder.eligibility import (
    assess_capes_pdse,
    assess_capes_print,
    assess_daad_cofunded_grant,
    assess_msca_postdoctoral,
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


def test_assess_capes_print_likely_when_mobility_purpose_text_present() -> None:
    page_text = (
        "Promover a mobilidade de docentes e discentes, com ênfase em doutorandos, "
        "pós-doutorandos e docentes para o exterior."
    )

    level, evidence = assess_capes_print(page_text)

    assert level == "likely"
    assert "doutorandos" in evidence


def test_assess_capes_print_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_capes_print("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_msca_confirmed_when_any_nationality_clause_present() -> None:
    page_text = (
        "These fellowships take place in an EU Member State. "
        "Researchers of any nationality can apply."
    )

    level, evidence = assess_msca_postdoctoral(page_text)

    assert level == "confirmed"
    assert "any nationality" in evidence.lower()


def test_assess_msca_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_msca_postdoctoral("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None
