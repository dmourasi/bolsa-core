from datetime import date

import httpx

from bolsa_finder.funding import (
    CAPES_PDSE_URL,
    DAAD_COFUNDED_GRANT_URL,
    fetch_capes_pdse,
    fetch_daad_cofunded_grant,
    fetch_page_text,
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
