from bolsa_core.eligibility import (
    assess_capes_pdse,
    assess_capes_print,
    assess_cnpq_no_explicit_criteria,
    assess_cnpq_swe,
    assess_daad_cofunded_grant,
    assess_fapeam_dex,
    assess_fapeam_dsex,
    assess_fapeam_pdext,
    assess_fapesb_posdoutorado,
    assess_fapespa_pdo,
    assess_faperj_doutorado_sanduiche,
    assess_fundacion_carolina_doctorado,
    assess_msca_doctoral_networks,
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


def test_assess_cnpq_swe_likely_when_institutional_enrollment_text_present() -> None:
    page_text = (
        "Apoia aluno formalmente matriculado em curso de doutorado no Brasil "
        "que comprove qualificação inequívoca."
    )

    level, evidence = assess_cnpq_swe(page_text)

    assert level == "likely"
    assert "matriculado em curso de doutorado" in evidence


def test_assess_cnpq_swe_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_cnpq_swe("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_cnpq_no_explicit_criteria_is_always_unknown() -> None:
    # Even text that sounds eligibility-adjacent must not be matched --
    # this assessor is used precisely where the page has no such text.
    level, evidence = assess_cnpq_no_explicit_criteria(
        "Ter nacionalidade brasileira. Requisitos e condições a seguir."
    )

    assert level == "unknown"
    assert evidence is None


def test_assess_faperj_confirmed_when_nationality_clause_present() -> None:
    page_text = (
        "Do bolsista Ter nacionalidade brasileira ou visto permanente no Brasil "
        "atualizado, no caso de pesquisador estrangeiro."
    )

    level, evidence = assess_faperj_doutorado_sanduiche(page_text)

    assert level == "confirmed"
    assert "nacionalidade brasileira" in evidence.lower()


def test_assess_faperj_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_faperj_doutorado_sanduiche("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fapesb_likely_when_institutional_link_text_present() -> None:
    page_text = (
        "Destinada a quem alcançou o título de doutor, e tem vínculo com "
        "instituição de enino superior e/ou centro de pesquisa científica "
        "e/ou tecnológica com sede na Bahia."
    )

    level, evidence = assess_fapesb_posdoutorado(page_text)

    assert level == "likely"
    assert "vínculo com instituição" in evidence.lower()


def test_assess_fapesb_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_fapesb_posdoutorado("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fapeam_dex_likely_when_enrollment_text_present() -> None:
    page_text = "ÚNICO Ter sido aceito(a) ou estar regularmente matriculado(a) em Programa de Doutoramento."

    level, evidence = assess_fapeam_dex(page_text)

    assert level == "likely"
    assert "Programa de Doutoramento" in evidence


def test_assess_fapeam_dex_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_fapeam_dex("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fapeam_dsex_likely_when_amazonas_enrollment_text_present() -> None:
    page_text = (
        "ÚNICO Estar regularmente matriculado(a) em Programa de Doutoramento "
        "reconhecido pela CAPES em instituição do Amazonas no Amazonas."
    )

    level, evidence = assess_fapeam_dsex(page_text)

    assert level == "likely"
    assert "instituição do Amazonas" in evidence


def test_assess_fapeam_dsex_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_fapeam_dsex("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fapeam_pdext_likely_when_employment_link_text_present() -> None:
    page_text = "ÚNICO Ter vínculo empregatício com IPES do Estado do Amazonas."

    level, evidence = assess_fapeam_pdext(page_text)

    assert level == "likely"
    assert "IPES do Estado do Amazonas" in evidence


def test_assess_fapeam_pdext_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_fapeam_pdext("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fapespa_pdo_is_always_unknown() -> None:
    # Even text that sounds eligibility-adjacent must not be matched --
    # the real FAPESPA page only has "Finalidade" (purpose), never criteria.
    page_text = (
        "Pós-Doutorado (PDO) Finalidade: Possibilitar, ao portador do título "
        "de doutor, estágio no país ou no exterior."
    )

    level, evidence = assess_fapespa_pdo(page_text)

    assert level == "unknown"
    assert evidence is None


def test_assess_msca_doctoral_networks_confirmed_when_any_nationality_present() -> None:
    page_text = (
        "Researchers funded by Doctoral Networks must not have a doctoral "
        "degree at the date of their recruitment can be of any nationality "
        "should be enrolled in a doctoral programme."
    )

    level, evidence = assess_msca_doctoral_networks(page_text)

    assert level == "confirmed"
    assert "any nationality" in evidence


def test_assess_msca_doctoral_networks_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_msca_doctoral_networks("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None


def test_assess_fundacion_carolina_confirmed_when_latin_america_clause_present() -> None:
    page_text = (
        "Requisitos. Es necesario cumplir los siguientes requisitos: Tener "
        "ciudadanía de alguno de los países de América Latina integrantes "
        "de la Comunidad Iberoamericana de Naciones."
    )

    level, evidence = assess_fundacion_carolina_doctorado(page_text)

    assert level == "confirmed"
    assert "América Latina" in evidence


def test_assess_fundacion_carolina_unknown_when_text_does_not_match() -> None:
    level, evidence = assess_fundacion_carolina_doctorado("completely unrelated page content")

    assert level == "unknown"
    assert evidence is None
