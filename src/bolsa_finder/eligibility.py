"""Evidence-based eligibility assessment for Brazilian applicants.

The invariant for this whole project: eligibility is never guessed. Each
assessment function here returns a verbatim excerpt from the source page
alongside a confidence level, and the excerpt is what justifies the level
-- not the other way around. If no relevant excerpt can be found, the
result is "unknown", never a default of "likely".
"""

from __future__ import annotations

import re
from typing import Literal

EligibilityLevel = Literal["confirmed", "likely", "unverified", "unknown"]


def find_evidence(text: str, keywords: list[str], context_chars: int = 220) -> str | None:
    """Return the first excerpt of `text` surrounding any of `keywords`.

    Case-insensitive. Used as a building block by source-specific assessors
    below, which know which keywords are meaningful for a given page.
    """
    lowered = text.lower()
    for keyword in keywords:
        idx = lowered.find(keyword.lower())
        if idx == -1:
            continue
        start = max(0, idx - context_chars)
        end = min(len(text), idx + len(keyword) + context_chars)
        excerpt = text[start:end].strip()
        return re.sub(r"\s+", " ", excerpt)
    return None


def assess_capes_pdse(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess PDSE (CAPES sandwich-doctorate) eligibility for Brazilians.

    PDSE does not gate on nationality directly on this overview page: it
    gates on being enrolled in a CAPES-recognized doctoral program at a
    Brazilian institution, with the institution running its own internal
    selection per edital. That is a strong-but-indirect signal, so this
    is marked "likely" rather than "confirmed" -- the specific edital for
    the candidate's institution/year must be checked for the exact rule.
    """
    evidence = find_evidence(
        page_text,
        [
            "requisitos para candidatura previstos no edital",
            "processo seletivo interno em sua Instituição",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "likely", evidence


def assess_daad_cofunded_grant(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess the DAAD co-funded short-term research grant for Brazilian PhDs.

    This DAAD program page explicitly restricts eligibility to doctoral
    candidates at universities in Brazil holding a CAPES/FAP scholarship,
    so an explicit match is treated as "confirmed".
    """
    evidence = find_evidence(
        page_text,
        [
            "doctoral candidates at universities in Brazil",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "confirmed", evidence


def assess_capes_print(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess CAPES PrInt (institutional internationalization) eligibility.

    Like PDSE, PrInt does not gate on nationality directly: mobility slots
    (for doutorandos AND pós-doutorandos, unlike PDSE which is doctorate
    only) are allocated by the participating Brazilian institution to its
    own students/researchers. Marked "likely", not "confirmed" -- the
    specific institution's internal selection rules must be checked.
    """
    evidence = find_evidence(
        page_text,
        [
            "mobilidade de docentes e discentes, com ênfase em doutorandos",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "likely", evidence


def assess_cnpq_swe(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess CNPq SWE (Doutorado Sanduíche no Exterior) eligibility.

    Same indirect pattern as PDSE: gates on being enrolled in a doctoral
    program in Brazil, not on nationality directly, so "likely" not
    "confirmed".
    """
    evidence = find_evidence(
        page_text,
        [
            "aluno formalmente matriculado em curso de doutorado no Brasil",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "likely", evidence


def assess_cnpq_no_explicit_criteria(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """For CNPq modalities (GDE, PDE, MPE) whose entry on the shared
    "Modalidades" page only states purpose/benefits/duration -- no
    nationality or Brazil-institution-link text appears there at all.
    Always "unknown": there is nothing on this specific page to cite, so
    nothing is claimed. A specific edital must be checked for the real rule.
    """
    return "unknown", None


def assess_faperj_doutorado_sanduiche(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess FAPERJ's Doutorado Sanduíche (Estágio de Doutorando no Exterior).

    This program page explicitly states the scholar must hold Brazilian
    nationality (or a permanent visa for foreign researchers), so an
    explicit match is "confirmed". It additionally requires enrollment in
    a doctoral program at a Rio de Janeiro state institution -- a second,
    narrower constraint the report should still surface via the evidence
    excerpt even though it doesn't change the nationality-eligibility level.
    """
    evidence = find_evidence(
        page_text,
        [
            "Ter nacionalidade brasileira ou visto permanente no Brasil",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "confirmed", evidence


def assess_msca_postdoctoral(page_text: str) -> tuple[EligibilityLevel, str | None]:
    """Assess MSCA European Postdoctoral Fellowships eligibility.

    The official page states plainly that researchers of any nationality
    can apply to the European track, so an explicit match is "confirmed".
    This does NOT cover the separate Global Postdoctoral Fellowships track,
    which is restricted to EU/associated-country nationals or long-term
    residents -- that distinction must be kept in the report, not collapsed.
    """
    evidence = find_evidence(
        page_text,
        [
            "Researchers of any nationality can apply",
        ],
    )
    if evidence is None:
        return "unknown", None
    return "confirmed", evidence
