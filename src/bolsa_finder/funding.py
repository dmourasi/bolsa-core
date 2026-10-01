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
from datetime import date
from typing import Literal

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser

from bolsa_finder.eligibility import (
    EligibilityLevel,
    assess_capes_pdse,
    assess_daad_cofunded_grant,
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


def fetch_capes_pdse(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """CAPES PDSE: institutional sandwich-doctorate program abroad (Brazil track)."""
    text = fetch_page_text(client, CAPES_PDSE_URL)
    if text is None:
        return FundingOpportunity(
            name="Programa de Doutorado-Sanduíche no Exterior (PDSE)",
            agency="CAPES",
            country_or_region="Brasil (bolsa para período no exterior)",
            target_levels=["sanduiche"],
            amount="unknown",
            deadline="unknown",
            url=CAPES_PDSE_URL,
            consulted_at=consulted_at or date.today(),
            eligibility_brazilian="unverified",
            eligibility_evidence=None,
        )

    level, evidence = assess_capes_pdse(text)
    return FundingOpportunity(
        name="Programa de Doutorado-Sanduíche no Exterior (PDSE)",
        agency="CAPES",
        country_or_region="Brasil (bolsa para período no exterior)",
        target_levels=["sanduiche"],
        # Amount/deadline vary per edital and per institution's annual quota;
        # the overview page does not state a single fixed value for either.
        amount="unknown",
        deadline="unknown",
        url=CAPES_PDSE_URL,
        consulted_at=consulted_at or date.today(),
        eligibility_brazilian=level,
        eligibility_evidence=evidence,
    )


def fetch_daad_cofunded_grant(client: httpx.Client, consulted_at: date | None = None) -> FundingOpportunity:
    """DAAD co-funded short-term research grant for Brazilian doctoral candidates."""
    text = fetch_page_text(client, DAAD_COFUNDED_GRANT_URL)
    if text is None:
        return FundingOpportunity(
            name="Co-funded Research Grants (short-term research stay in Germany)",
            agency="DAAD",
            country_or_region="Germany (for Brazilian doctoral candidates)",
            target_levels=["sanduiche"],
            amount="unknown",
            deadline="unknown",
            url=DAAD_COFUNDED_GRANT_URL,
            consulted_at=consulted_at or date.today(),
            eligibility_brazilian="unverified",
            eligibility_evidence=None,
        )

    level, evidence = assess_daad_cofunded_grant(text)
    return FundingOpportunity(
        name="Co-funded Research Grants (short-term research stay in Germany)",
        agency="DAAD",
        country_or_region="Germany (for Brazilian doctoral candidates)",
        target_levels=["sanduiche"],
        amount="unknown",
        deadline="unknown",
        url=DAAD_COFUNDED_GRANT_URL,
        consulted_at=consulted_at or date.today(),
        eligibility_brazilian=level,
        eligibility_evidence=evidence,
    )
