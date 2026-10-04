from datetime import date

import httpx

from bolsa_finder.funding import (
    CAPES_PDSE_URL,
    CAPES_PRINT_URL,
    CNPQ_MODALIDADES_URL,
    DAAD_COFUNDED_GRANT_URL,
    FAPEAM_BOLSAS_EXTERIOR_URL,
    FAPERJ_DOUTORADO_SANDUICHE_URL,
    FAPESB_POSDOUTORADO_URL,
    FAPESPA_BOLSAS_URL,
    FUNDACION_CAROLINA_DOCTORADO_URL,
    MSCA_DOCTORAL_NETWORKS_URL,
    MSCA_POSTDOCTORAL_URL,
    FundingOpportunity,
    fetch_all_automated_opportunities,
    fetch_capes_pdse,
    fetch_capes_print,
    fetch_cnpq_modalities,
    fetch_daad_cofunded_grant,
    fetch_fapeam_modalities,
    fetch_fapesb_posdoutorado,
    fetch_fapespa_pdo,
    fetch_faperj_doutorado_sanduiche,
    fetch_fundacion_carolina_doctorado,
    fetch_msca_doctoral_networks,
    fetch_msca_postdoctoral,
    fetch_page_text,
    opportunities_for_target_level,
)

CAPES_SNIPPET_HTML = """
<html><body><p>{filler}
O candidato deve apresentar Proposta de Pesquisa e atender aos requisitos para
candidatura previstos no edital durante o processo seletivo interno em sua
Instituição. {filler}</p></body></html>
""".format(filler="x" * 100)

DAAD_SNIPPET_HTML = """
<html><body><p>{filler}
Who can apply? Doctoral candidates at universities in Brazil, who have been
awarded a domestic scholarship from CAPES or one of the participating FAPs.
{filler}</p></body></html>
""".format(filler="y" * 100)

CAPES_PRINT_SNIPPET_HTML = """
<html><body><p>{filler}
Promover a mobilidade de docentes e discentes, com ênfase em doutorandos,
pós-doutorandos e docentes para o exterior e do exterior para o Brasil.
{filler}</p></body></html>
""".format(filler="z" * 100)

MSCA_SNIPPET_HTML = """
<html><body><p>{filler}
These fellowships take place in an EU Member State or Horizon Europe
Associated Country. Researchers of any nationality can apply.
{filler}</p></body></html>
""".format(filler="w" * 100)

CNPQ_MODALIDADES_SNIPPET_HTML = """
<html><body><p>{filler}
Doutorado Sanduíche - SWE Apoia aluno formalmente matriculado em curso de
doutorado no Brasil que comprove qualificação inequívoca para usufruir, no
exterior, da oportunidade de aprofundamento teórico.
{filler}</p></body></html>
""".format(filler="v" * 100)

FAPERJ_SNIPPET_HTML = """
<html><body><p>{filler}
Do bolsista Ter nacionalidade brasileira ou visto permanente no Brasil
atualizado, no caso de pesquisador estrangeiro.
{filler}</p></body></html>
""".format(filler="u" * 100)

FAPESB_SNIPPET_HTML = """
<html><body><p>{filler}
PÓS-DOUTORADO 2 – PD2 Destinada a quem alcançou o título de doutor, e tem
vínculo com instituição de enino superior e/ou centro de pesquisa científica
e/ou tecnológica com sede na Bahia, para desenvolver projeto de pesquisa em
instituição de outro estado ou país.
{filler}</p></body></html>
""".format(filler="t" * 100)

FAPEAM_SNIPPET_HTML = """
<html><body><p>{filler}
Doutorado no exterior DEX Cota Individual Formar doutores no exterior em
centros de excelência. ÚNICO Ter sido aceito(a) ou estar regularmente
matriculado(a) em Programa de Doutoramento.
Doutorado Sanduíche no exterior DSEX Cota Individual Apoiar alunos. ÚNICO
Estar regularmente matriculado(a) em Programa de Doutoramento reconhecido
pela CAPES em instituição do Amazonas.
Pós-Doutorado PDEXT Cota Individual Possibilitar a atualização. ÚNICO Ter
vínculo empregatício com IPES do Estado do Amazonas.
{filler}</p></body></html>
""".format(filler="s" * 100)

MSCA_DN_SNIPPET_HTML = """
<html><body><p>{filler}
Researchers funded by Doctoral Networks must not have a doctoral degree
at the date of their recruitment can be of any nationality should be
enrolled in a doctoral programme during the project.
{filler}</p></body></html>
""".format(filler="q" * 100)

FUNDACION_CAROLINA_SNIPPET_HTML = """
<html><body><p>{filler}
Requisitos Es necesario cumplir los siguientes requisitos: Tener
ciudadanía de alguno de los países de América Latina integrantes de la
Comunidad Iberoamericana de Naciones.
{filler}</p></body></html>
""".format(filler="p" * 100)


def _client(httpx_mock) -> httpx.Client:
    return httpx.Client()


def test_fetch_page_text_returns_none_on_http_error(httpx_mock) -> None:
    httpx_mock.add_response(url="https://example.com/page", status_code=404)

    with httpx.Client() as client:
        result = fetch_page_text(client, "https://example.com/page")

    assert result is None


def test_fetch_page_text_returns_none_when_body_too_short(httpx_mock) -> None:
    httpx_mock.add_response(url="https://example.com/page", html="<html><body>hi</body></html>")

    with httpx.Client() as client:
        result = fetch_page_text(client, "https://example.com/page")

    assert result is None


def test_fetch_page_text_extracts_visible_text(httpx_mock) -> None:
    httpx_mock.add_response(url="https://example.com/page", html=CAPES_SNIPPET_HTML)

    with httpx.Client() as client:
        result = fetch_page_text(client, "https://example.com/page")

    assert result is not None
    assert "processo seletivo interno" in result


def test_fetch_capes_pdse_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=CAPES_PDSE_URL, html=CAPES_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_capes_pdse(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "CAPES"
    assert opportunity.url == CAPES_PDSE_URL
    assert opportunity.consulted_at == date(2026, 1, 15)
    assert opportunity.eligibility_brazilian == "likely"
    assert opportunity.eligibility_evidence is not None
    assert opportunity.amount == "unknown"
    assert opportunity.deadline == "unknown"


def test_fetch_capes_pdse_unverified_when_page_unreachable(httpx_mock) -> None:
    httpx_mock.add_response(url=CAPES_PDSE_URL, status_code=500)

    with httpx.Client() as client:
        opportunity = fetch_capes_pdse(client, consulted_at=date(2026, 1, 15))

    assert opportunity.eligibility_brazilian == "unverified"
    assert opportunity.eligibility_evidence is None


def test_fetch_daad_cofunded_grant_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=DAAD_COFUNDED_GRANT_URL, html=DAAD_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_daad_cofunded_grant(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "DAAD"
    assert opportunity.url == DAAD_COFUNDED_GRANT_URL
    assert opportunity.eligibility_brazilian == "confirmed"
    assert "Brazil" in opportunity.eligibility_evidence


def test_fetch_capes_print_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=CAPES_PRINT_URL, html=CAPES_PRINT_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_capes_print(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "CAPES"
    assert opportunity.url == CAPES_PRINT_URL
    assert "posdoc" in opportunity.target_levels
    assert opportunity.eligibility_brazilian == "likely"
    assert "doutorandos" in opportunity.eligibility_evidence


def test_fetch_capes_print_unverified_when_page_unreachable(httpx_mock) -> None:
    httpx_mock.add_response(url=CAPES_PRINT_URL, status_code=500)

    with httpx.Client() as client:
        opportunity = fetch_capes_print(client, consulted_at=date(2026, 1, 15))

    assert opportunity.eligibility_brazilian == "unverified"
    assert opportunity.eligibility_evidence is None


def test_fetch_msca_postdoctoral_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=MSCA_POSTDOCTORAL_URL, html=MSCA_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_msca_postdoctoral(client, consulted_at=date(2026, 1, 15))

    assert "MSCA" in opportunity.agency or "Horizon" in opportunity.agency
    assert opportunity.url == MSCA_POSTDOCTORAL_URL
    assert opportunity.eligibility_brazilian == "confirmed"
    assert "any nationality" in opportunity.eligibility_evidence.lower()


def _opportunity(**overrides) -> FundingOpportunity:
    defaults = dict(
        name="Test Opportunity",
        agency="Test Agency",
        country_or_region="Testland",
        target_levels=["sanduiche"],
        amount="unknown",
        deadline="unknown",
        url="https://example.com",
        consulted_at=date(2026, 1, 1),
        eligibility_brazilian="confirmed",
        eligibility_evidence=None,
    )
    defaults.update(overrides)
    return FundingOpportunity(**defaults)


def test_opportunities_for_target_level_filters_by_membership() -> None:
    sanduiche_only = _opportunity(name="A", target_levels=["sanduiche"])
    posdoc_only = _opportunity(name="B", target_levels=["posdoc"])
    both = _opportunity(name="C", target_levels=["sanduiche", "posdoc"])

    result = opportunities_for_target_level([sanduiche_only, posdoc_only, both], "posdoc")

    assert {o.name for o in result} == {"B", "C"}


def test_opportunities_for_target_level_empty_for_uncovered_level() -> None:
    sanduiche_only = _opportunity(name="A", target_levels=["sanduiche"])

    result = opportunities_for_target_level([sanduiche_only], "mestrado")

    assert result == []


def test_fetch_cnpq_modalities_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=CNPQ_MODALIDADES_URL, html=CNPQ_MODALIDADES_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunities = fetch_cnpq_modalities(client, consulted_at=date(2026, 1, 15))

    assert len(opportunities) == 4
    by_level = {o.target_levels[0]: o for o in opportunities}
    assert by_level["sanduiche"].eligibility_brazilian == "likely"
    assert by_level["sanduiche"].eligibility_evidence is not None
    # GDE/MPE/PDE: this page has no nationality/institution-link text for
    # them, so they must stay honestly "unknown", not inherit SWE's "likely".
    assert by_level["pleno"].eligibility_brazilian == "unknown"
    assert by_level["mestrado"].eligibility_brazilian == "unknown"
    assert by_level["posdoc"].eligibility_brazilian == "unknown"
    assert all(o.agency == "CNPq" for o in opportunities)
    assert all(o.url == CNPQ_MODALIDADES_URL for o in opportunities)


def test_fetch_cnpq_modalities_all_unverified_when_page_unreachable(httpx_mock) -> None:
    httpx_mock.add_response(url=CNPQ_MODALIDADES_URL, status_code=500)

    with httpx.Client() as client:
        opportunities = fetch_cnpq_modalities(client, consulted_at=date(2026, 1, 15))

    assert len(opportunities) == 4
    assert all(o.eligibility_brazilian == "unverified" for o in opportunities)


def test_fetch_faperj_doutorado_sanduiche_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=FAPERJ_DOUTORADO_SANDUICHE_URL, html=FAPERJ_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_faperj_doutorado_sanduiche(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "FAPERJ"
    assert opportunity.eligibility_brazilian == "confirmed"
    assert "nacionalidade brasileira" in opportunity.eligibility_evidence.lower()


def test_fetch_fapesb_posdoutorado_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=FAPESB_POSDOUTORADO_URL, html=FAPESB_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_fapesb_posdoutorado(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "FAPESB"
    assert opportunity.target_levels == ["posdoc"]
    assert opportunity.eligibility_brazilian == "likely"
    assert "vínculo com instituição" in opportunity.eligibility_evidence.lower()


def test_fetch_fapeam_modalities_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=FAPEAM_BOLSAS_EXTERIOR_URL, html=FAPEAM_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunities = fetch_fapeam_modalities(client, consulted_at=date(2026, 1, 15))

    assert len(opportunities) == 3
    by_level = {o.target_levels[0]: o for o in opportunities}
    # Unlike CNPq, all three FAPEAM modalities have real eligibility text.
    assert by_level["pleno"].eligibility_brazilian == "likely"
    assert by_level["sanduiche"].eligibility_brazilian == "likely"
    assert by_level["posdoc"].eligibility_brazilian == "likely"
    assert all(o.agency == "FAPEAM" for o in opportunities)
    assert all(o.url == FAPEAM_BOLSAS_EXTERIOR_URL for o in opportunities)


def test_fetch_fapeam_modalities_all_unverified_when_page_unreachable(httpx_mock) -> None:
    httpx_mock.add_response(url=FAPEAM_BOLSAS_EXTERIOR_URL, status_code=500)

    with httpx.Client() as client:
        opportunities = fetch_fapeam_modalities(client, consulted_at=date(2026, 1, 15))

    assert len(opportunities) == 3
    assert all(o.eligibility_brazilian == "unverified" for o in opportunities)


def test_fetch_fapespa_pdo_always_unknown_even_with_real_page_text(httpx_mock) -> None:
    # The permanent FAPESPA "Bolsas" page states only the program's purpose
    # ("Finalidade"), never nationality/institutional-link criteria -- this
    # must stay "unknown" regardless of what the page says.
    fapespa_html = """
    <html><body><p>{filler}
    Pós-Doutorado (PDO) Finalidade: Possibilitar, ao portador do título de
    doutor, estágio para desenvolvimento de projetos de pesquisa junto a
    grupos e instituições de reconhecida excelência no país ou no exterior.
    {filler}</p></body></html>
    """.format(filler="r" * 100)
    httpx_mock.add_response(url=FAPESPA_BOLSAS_URL, html=fapespa_html)

    with httpx.Client() as client:
        opportunity = fetch_fapespa_pdo(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "FAPESPA"
    assert opportunity.target_levels == ["posdoc"]
    assert opportunity.eligibility_brazilian == "unknown"
    assert opportunity.eligibility_evidence is None


def test_fetch_msca_doctoral_networks_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=MSCA_DOCTORAL_NETWORKS_URL, html=MSCA_DN_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_msca_doctoral_networks(client, consulted_at=date(2026, 1, 15))

    assert opportunity.target_levels == ["pleno"]
    assert opportunity.eligibility_brazilian == "confirmed"
    assert "any nationality" in opportunity.eligibility_evidence


def test_fetch_fundacion_carolina_doctorado_end_to_end_with_mocked_http(httpx_mock) -> None:
    httpx_mock.add_response(url=FUNDACION_CAROLINA_DOCTORADO_URL, html=FUNDACION_CAROLINA_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunity = fetch_fundacion_carolina_doctorado(client, consulted_at=date(2026, 1, 15))

    assert opportunity.agency == "Fundación Carolina"
    assert opportunity.target_levels == ["pleno"]
    assert opportunity.eligibility_brazilian == "confirmed"
    assert "América Latina" in opportunity.eligibility_evidence


def test_fetch_all_automated_opportunities_fetches_every_source(httpx_mock) -> None:
    httpx_mock.add_response(url=CAPES_PDSE_URL, html=CAPES_SNIPPET_HTML)
    httpx_mock.add_response(url=CAPES_PRINT_URL, html=CAPES_PRINT_SNIPPET_HTML)
    httpx_mock.add_response(url=DAAD_COFUNDED_GRANT_URL, html=DAAD_SNIPPET_HTML)
    httpx_mock.add_response(url=MSCA_POSTDOCTORAL_URL, html=MSCA_SNIPPET_HTML)
    httpx_mock.add_response(url=MSCA_DOCTORAL_NETWORKS_URL, html=MSCA_DN_SNIPPET_HTML)
    httpx_mock.add_response(url=FUNDACION_CAROLINA_DOCTORADO_URL, html=FUNDACION_CAROLINA_SNIPPET_HTML)
    httpx_mock.add_response(url=FAPERJ_DOUTORADO_SANDUICHE_URL, html=FAPERJ_SNIPPET_HTML)
    httpx_mock.add_response(url=FAPESB_POSDOUTORADO_URL, html=FAPESB_SNIPPET_HTML)
    httpx_mock.add_response(url=FAPESPA_BOLSAS_URL, html=FAPESB_SNIPPET_HTML)
    httpx_mock.add_response(url=CNPQ_MODALIDADES_URL, html=CNPQ_MODALIDADES_SNIPPET_HTML)
    httpx_mock.add_response(url=FAPEAM_BOLSAS_EXTERIOR_URL, html=FAPEAM_SNIPPET_HTML)

    with httpx.Client() as client:
        opportunities = fetch_all_automated_opportunities(client, consulted_at=date(2026, 1, 15))

    assert len(opportunities) == 16
    assert {o.agency for o in opportunities} == {
        "CAPES",
        "DAAD",
        "European Commission / Horizon Europe (MSCA)",
        "European Research Executive Agency (REA) / Horizon Europe (MSCA)",
        "Fundación Carolina",
        "FAPERJ",
        "FAPESB",
        "FAPESPA",
        "CNPq",
        "FAPEAM",
    }
