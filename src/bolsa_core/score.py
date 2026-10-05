"""Deterministic, evidence-based fit scoring.

Per the project's inviolable rule, a researcher's fit is never inferred
from reputation proxies like h-index: it is computed purely from overlap
between the candidate's declared research areas/methods and the
researcher's actual recent publication topics/titles, weighted by
recency. Every point added to the score is traceable to one specific
(profile term, publication) pair, which `evidence` lists verbatim.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

from pydantic import BaseModel

from bolsa_core.openalex import Publication
from bolsa_core.profile import Profile

ConfidenceLevel = Literal["high", "medium", "low"]

# Recency weighting: a topic overlap in a 2026 paper says more about current
# fit than the same overlap in a 2018 paper. Buckets are coarse on purpose --
# this is a deterministic heuristic, not a statistical model.
_RECENT_YEARS = 2
_MID_YEARS = 5
_TOPIC_MATCH_WEIGHT = 1.0
_TITLE_MATCH_WEIGHT = 0.5
# Full-phrase matching ("microbiome amplicon analysis") misses real overlap
# whenever OpenAlex's topic vocabulary phrases the same idea differently
# (e.g. "Microbial Community Ecology"). A weaker word-level signal catches
# that without losing determinism: it still points at the exact shared word.
_WORD_MATCH_WEIGHT = 0.3
_MIN_WORD_LENGTH = 6
_GENERIC_WORDS = {
    "analysis", "analyses", "methods", "studies", "research",
    "science", "sciences", "applied", "environmental", "general",
}


def _significant_words(term: str) -> set[str]:
    words = re.findall(r"[a-z]+", term.lower())
    return {w for w in words if len(w) >= _MIN_WORD_LENGTH and w not in _GENERIC_WORDS}


class Researcher(BaseModel):
    id: str
    display_name: str
    institution_name: str
    confidence: ConfidenceLevel
    publications: list[Publication]


class FitScore(BaseModel):
    researcher_id: str
    researcher_name: str
    institution_name: str
    score: float
    evidence: list[str]
    pending_checks: list[str]


def _recency_weight(publication_year: int, as_of_year: int) -> float:
    age = as_of_year - publication_year
    if age <= _RECENT_YEARS:
        return 1.0
    if age <= _MID_YEARS:
        return 0.6
    return 0.3


def _profile_terms(profile: Profile) -> list[str]:
    return [term.lower() for term in (*profile.research_areas, *profile.methods)]


def score_researcher_fit(
    profile: Profile, researcher: Researcher, as_of: date | None = None
) -> FitScore:
    as_of_year = (as_of or date.today()).year
    terms = _profile_terms(profile)

    total = 0.0
    evidence: list[str] = []

    for publication in researcher.publications:
        weight = _recency_weight(publication.year, as_of_year)
        topics_lower = [t.lower() for t in publication.topics]
        title_lower = publication.title.lower()

        matched_as_topic: set[str] = set()
        for term in terms:
            if any(term in topic or topic in term for topic in topics_lower):
                matched_as_topic.add(term)
                total += _TOPIC_MATCH_WEIGHT * weight
                evidence.append(
                    f"Topic overlap: profile term '{term}' matches a topic of "
                    f'"{publication.title}" ({publication.year}) -- {publication.url}'
                )

        for term in terms:
            if term in matched_as_topic:
                continue
            if term in title_lower:
                matched_as_topic.add(term)
                total += _TITLE_MATCH_WEIGHT * weight
                evidence.append(
                    f"Title match: profile term '{term}' appears in "
                    f'"{publication.title}" ({publication.year}) -- {publication.url}'
                )

        combined_haystack = " ".join([title_lower, *topics_lower])
        for term in terms:
            if term in matched_as_topic:
                continue
            words = _significant_words(term)
            hit_word = next((w for w in words if w in combined_haystack), None)
            if hit_word is None:
                continue
            total += _WORD_MATCH_WEIGHT * weight
            evidence.append(
                f"Word overlap: '{hit_word}' (from profile term '{term}') found in "
                f'"{publication.title}" ({publication.year}) -- {publication.url}'
            )

    pending_checks = [
        "Active grants and lab funding status are not available via OpenAlex; "
        "confirm directly with the researcher or lab page.",
        "Current recruiting status (open PhD/postdoc slots) is not available via "
        "OpenAlex; confirm directly with the researcher.",
    ]
    if researcher.confidence != "high":
        pending_checks.insert(
            0,
            f"Author identity disambiguation confidence is '{researcher.confidence}' "
            "(OpenAlex author matching is fragile for common names/old affiliations); "
            "confirm this is the same person via the institutional page before contacting them.",
        )

    return FitScore(
        researcher_id=researcher.id,
        researcher_name=researcher.display_name,
        institution_name=researcher.institution_name,
        score=round(total, 2),
        evidence=evidence,
        pending_checks=pending_checks,
    )
