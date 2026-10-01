"""Funding opportunity schema and source-specific fetchers.

Each fetcher retrieves ONE real, named source end-to-end: HTTP GET -> text
extraction -> eligibility assessment (see eligibility.py) -> a validated
FundingOpportunity with url + consulted_at so the report can always point
back to where a claim came from.

If the page cannot be parsed into usable text (e.g. it turns out to be
JS-rendered and httpx+selectolax see only an empty shell), the fetcher
still returns a FundingOpportunity, but with eligibility_brazilian set to
"unverified" and amount/deadline set to "unknown" rather than failing
silently or guessing.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from typing import Literal

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from bolsa_finder.eligibility import (
    EligibilityLevel,
    assess_capes_pdse,
    assess_capes_print,
    assess_daad_cofunded_grant,
    assess_msca_postdoctoral,
)

Unknown = Literal["unknown"]


class FundingOpportunity(BaseModel):
    name: str
    agency: str
    country_or_region: str
    target_levels: list[str]
    amount: str | Unknown
    deadline: str | Unknown
    url: str
    consulted_at: date
    eligibility_brazilian: EligibilityLevel
    eligibility_evidence: str | None = None


def fetch_page_text(client: httpx.Client, url: str) -> str | None:
    """GET a URL and return its visible text, or None if that fails.

    None covers both network/HTTP failures and pages that render to
    essentially empty text (a signal of client-side/JS rendering), so
    callers can fall back to "unverified" instead of guessing.
    """
    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    tree = HTMLParser(response.text)
    body = tree.body
    if body is None:
        return None
    text = body.text(separator=" ", strip=True)
    # Collapse arbitrary internal whitespace/newlines so later substring
    # matching against known phrases (see eligibility.py) is robust to how
    # a page happens to wrap its text in the source HTML.
    text = re.sub(r"\s+", " ", text)
    if len(text) < 200:
        return None
    return text


CAPES_PDSE_URL = (
    "https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/bolsas/"
    "bolsas-e-auxilios-internacionais/encontre-aqui/paises/multinacional/"
    "programa-de-doutorado-sanduiche-no-exterior-pdse"
)

DAAD_COFUNDED_GRANT_URL = (
    "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"
    "?detail=57378178"
)

CAPES_PRINT_URL = (
    "https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/bolsas/"
    "bolsas-e-auxilios-internacionais/informacoes-internacionais/"
    "programa-institucional-de-internacionalizacao-capes-print"
)

MSCA_POSTDOCTORAL_URL = "https://marie-sklodowska-curie-actions.ec.europa.eu/actions/postdoctoral-fellowships"


def _fetch_opportunity(
    client: httpx.Client,
    url: str,
    assess: Callable[[str], tuple[EligibilityLevel, str | None]],
    *,
    name: str,
    agency: str,
    country_or_region: str,
    target_levels: list[str],
    consulted_at: date | None,
) -> FundingOpportunity:
    """Shared fetch -> assess -> FundingOpportunity flow used by every source.

    Amount/deadline are always "unknown" here: none of the automated sources
    state a single fixed value at the program-overview level (they vary per
    edital/call), so this is never guessed from unrelated page text.
    """
    text = fetch_page_text(client, url)
    level, evidence = assess(text) if text is not None else ("unverified", None)
    return FundingOpportunity(
        name=name,
        agency=agency,
        country_or_region=country_or_region,
        target_levels=target_levels,
        amount="unknown",
        deadline="unknown",
        url=url,
        consulted_at=consulted_at or date.today(),
        eligibility_brazilian=level,
        eligibility_evidence=evidence,
    )


def fetch_capes_pdse(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """CAPES PDSE: institutional sandwich-doctorate program abroad (Brazil track)."""
    return _fetch_opportunity(
        client,
        CAPES_PDSE_URL,
        assess_capes_pdse,
        name="Programa de Doutorado-Sanduíche no Exterior (PDSE)",
        agency="CAPES",
        country_or_region="Brasil (bolsa para período no exterior)",
        target_levels=["sanduiche"],
        consulted_at=consulted_at,
    )


def fetch_daad_cofunded_grant(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """DAAD co-funded short-term research grant for Brazilian doctoral candidates."""
    return _fetch_opportunity(
        client,
        DAAD_COFUNDED_GRANT_URL,
        assess_daad_cofunded_grant,
        name="Co-funded Research Grants (short-term research stay in Germany)",
        agency="DAAD",
        country_or_region="Germany (for Brazilian doctoral candidates)",
        target_levels=["sanduiche"],
        consulted_at=consulted_at,
    )


def fetch_capes_print(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """CAPES PrInt: institutional internationalization mobility (doctorate + postdoc)."""
    return _fetch_opportunity(
        client,
        CAPES_PRINT_URL,
        assess_capes_print,
        name="Programa Institucional de Internacionalização (CAPES PrInt)",
        agency="CAPES",
        country_or_region="Brasil (mobilidade para o exterior e do exterior para o Brasil)",
        target_levels=["sanduiche", "posdoc"],
        consulted_at=consulted_at,
    )


def fetch_msca_postdoctoral(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """MSCA European Postdoctoral Fellowships (Horizon Europe, EU)."""
    return _fetch_opportunity(
        client,
        MSCA_POSTDOCTORAL_URL,
        assess_msca_postdoctoral,
        name="MSCA Postdoctoral Fellowships (European track)",
        agency="European Commission / Horizon Europe (MSCA)",
        country_or_region="European Union / Horizon Europe Associated Countries",
        target_levels=["posdoc"],
        consulted_at=consulted_at,
    )
