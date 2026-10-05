"""Minimal REST client for the OpenAlex API.

Implements the topics -> institutions -> authors discovery chain using
plain httpx calls (no pyalex) so pagination, the polite pool contact
param, and response shape are all explicit and easy to mock in tests.

API docs: https://docs.openalex.org/
"""

from __future__ import annotations

from collections import Counter
from typing import Literal

import httpx
from pydantic import BaseModel

BASE_URL = "https://api.openalex.org"

# Mirrors score.ConfidenceLevel; duplicated as a plain Literal (not imported)
# to avoid a circular import, since score.py imports from this module.
AuthorMatchConfidence = Literal["high", "medium", "low"]


class Topic(BaseModel):
    id: str
    display_name: str
    works_count: int


class InstitutionHit(BaseModel):
    """An institution with recent production in a given topic."""

    id: str
    display_name: str
    recent_works_count: int


class AuthorHit(BaseModel):
    """An author with recent production in a given topic at a given institution."""

    id: str
    display_name: str
    recent_works_count: int


class Publication(BaseModel):
    """A single work, used as fit evidence -- never scored by venue prestige."""

    id: str
    title: str
    year: int
    url: str
    topics: list[str]


class OpenAlexClient:
    """Thin wrapper around httpx for the OpenAlex REST API.

    `contact_email` is sent as the `mailto` query param to use OpenAlex's
    polite pool (faster, more reliable rate limits) as recommended by the
    API docs.
    """

    def __init__(self, contact_email: str, client: httpx.Client | None = None) -> None:
        self._contact_email = contact_email
        self._client = client or httpx.Client(base_url=BASE_URL, timeout=30.0)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "OpenAlexClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, str]) -> dict:
        params = {**params, "mailto": self._contact_email}
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def search_topics(self, query: str, limit: int = 10) -> list[Topic]:
        """Find OpenAlex topic IDs matching a free-text research area."""
        data = self._get(
            "/topics",
            {"search": query, "per_page": str(limit)},
        )
        return [
            Topic(
                id=item["id"],
                display_name=item["display_name"],
                works_count=item.get("works_count", 0),
            )
            for item in data.get("results", [])
        ]

    def institutions_for_topic(
        self, topic_id: str, since_year: int, limit: int = 25
    ) -> list[InstitutionHit]:
        """Institutions with recent (since_year onward) production in a topic.

        Uses OpenAlex's group_by to aggregate works by institution without
        having to page through individual works.
        """
        data = self._get(
            "/works",
            {
                "filter": f"topics.id:{topic_id},publication_year:>{since_year - 1}",
                "group_by": "authorships.institutions.id",
                "per_page": str(limit),
            },
        )
        hits: list[InstitutionHit] = []
        for group in data.get("group_by", []):
            # OpenAlex group_by keys are institution IDs; an empty key means
            # "works without an institution" and is not a usable result.
            if not group.get("key") or not group.get("key_display_name"):
                continue
            hits.append(
                InstitutionHit(
                    id=group["key"],
                    display_name=group["key_display_name"],
                    recent_works_count=group.get("count", 0),
                )
            )
        return hits[:limit]

    def authors_for_topic_institution(
        self, topic_id: str, institution_id: str, since_year: int, limit: int = 25
    ) -> list[AuthorHit]:
        """Authors with recent production in a topic at a given institution."""
        data = self._get(
            "/works",
            {
                "filter": (
                    f"topics.id:{topic_id},"
                    f"authorships.institutions.id:{institution_id},"
                    f"publication_year:>{since_year - 1}"
                ),
                "group_by": "authorships.author.id",
                "per_page": str(limit),
            },
        )
        hits: list[AuthorHit] = []
        for group in data.get("group_by", []):
            if not group.get("key") or not group.get("key_display_name"):
                continue
            hits.append(
                AuthorHit(
                    id=group["key"],
                    display_name=group["key_display_name"],
                    recent_works_count=group.get("count", 0),
                )
            )
        return hits[:limit]

    def works_for_author(
        self, author_id: str, since_year: int, limit: int = 25
    ) -> list[Publication]:
        """Recent publications for a specific author, used as fit evidence.

        Titles and topic names are returned as-is from OpenAlex so score.py
        can match them against the candidate's profile; this method does
        not interpret or rank them.
        """
        data = self._get(
            "/works",
            {
                "filter": f"authorships.author.id:{author_id},publication_year:>{since_year - 1}",
                "sort": "publication_year:desc",
                "per_page": str(limit),
            },
        )
        publications: list[Publication] = []
        for item in data.get("results", []):
            if not item.get("id") or not item.get("display_name"):
                continue
            topics = [
                topic["display_name"]
                for topic in item.get("topics", [])
                if topic.get("display_name")
            ]
            publications.append(
                Publication(
                    id=item["id"],
                    title=item["display_name"],
                    year=item.get("publication_year", since_year),
                    url=item.get("doi") or item["id"],
                    topics=topics,
                )
            )
        return publications

    def find_author_by_orcid(self, orcid: str) -> AuthorHit | None:
        """Resolve an OpenAlex author directly by ORCID.

        An ORCID match is as close to a verified identity as OpenAlex
        offers, so this is the preferred resolution path for Lattes-derived
        candidates (see lattes.py) -- callers should treat this as "high"
        confidence. Accepts either a bare ORCID ("0000-0002-1298-3089") or
        a full URL; OpenAlex's filter requires the full URL form.
        """
        orcid_url = orcid if orcid.startswith("http") else f"https://orcid.org/{orcid}"
        data = self._get("/authors", {"filter": f"orcid:{orcid_url}"})
        results = data.get("results", [])
        if not results:
            return None
        item = results[0]
        return AuthorHit(
            id=item["id"],
            display_name=item.get("display_name", ""),
            recent_works_count=item.get("works_count", 0),
        )

    def find_author_by_dois(self, dois: list[str]) -> tuple[AuthorHit, AuthorMatchConfidence] | None:
        """Resolve an OpenAlex author by overlap with a list of known DOIs.

        Fallback for when no ORCID is available (e.g. an older Lattes CV).
        Tallies authorship across the works matching any of `dois` and
        returns the most frequent author -- but this can never be as sure
        as an ORCID match (a co-author could tally just as high), so the
        confidence returned is "medium" when the match covers most of the
        given DOIs, else "low". Returns None if no DOI resolves at all.
        """
        clean_dois = [d for d in dois if d]
        if not clean_dois:
            return None

        filter_value = "|".join(clean_dois)
        data = self._get("/works", {"filter": f"doi:{filter_value}", "per_page": "100"})
        results = data.get("results", [])
        if not results:
            return None

        author_counts: Counter[tuple[str, str]] = Counter()
        for work in results:
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                author_id = author.get("id")
                if author_id:
                    author_counts[(author_id, author.get("display_name", ""))] += 1

        if not author_counts:
            return None

        (author_id, display_name), match_count = author_counts.most_common(1)[0]
        confidence: AuthorMatchConfidence = "medium" if match_count >= len(clean_dois) / 2 else "low"
        return (
            AuthorHit(id=author_id, display_name=display_name, recent_works_count=match_count),
            confidence,
        )
