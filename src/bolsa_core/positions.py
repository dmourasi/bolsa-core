"""Open position listings: job boards and portals, distinct from FundingOpportunity.

A FundingOpportunity (see funding.py) describes a PROGRAM: it recurs
every cycle under roughly the same eligibility criteria (CAPES PDSE,
MSCA, ...). A Position here describes one individual, specific listing
(one lab, one deadline, closes when filled or past deadline) scraped
from a job board/portal -- EURAXESS, Science Careers (AAAS), etc. These
need a different shape: no eligibility_brazilian (job boards rarely
state nationality restrictions explicitly; when they do, it goes in
eligibility_note, never invented otherwise), but they do have the
specific org/lab and a real posted-vs-deadline date.

Same inviolable rule as funding.py: every Position carries url +
consulted_at, and any field the source page doesn't state is None/
"unknown", never guessed or inferred beyond literal substring matching.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Literal

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser

Unknown = Literal["unknown"]


class Position(BaseModel):
    title: str
    organisation: str
    country: str | Unknown
    position_type: str | Unknown  # e.g. "PhD", "Postdoc", "Faculty" -- source's own wording
    url: str
    source: str  # "euraxess" | "sciencecareers"
    consulted_at: date
    deadline: str | Unknown = "unknown"
    matched_terms: list[str] = []
    eligibility_note: str | None = None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _matches_any_term(haystack: str, terms: list[str]) -> list[str]:
    haystack_lower = haystack.lower()
    return [t for t in terms if t.lower() in haystack_lower]


# -- Science Careers (AAAS) --------------------------------------------
# Madgex-platform job board; ?keywords=<q> is a real server-side search
# (verified against https://jobs.sciencecareers.org/jobs/?keywords=microbiome
# on 2026-10-10 -- returns results whose titles/descriptions actually
# contain the keyword, unlike EURAXESS below).

SCIENCECAREERS_SEARCH_URL = "https://jobs.sciencecareers.org/jobs/"


def fetch_sciencecareers_positions(
    client: httpx.Client,
    keywords: list[str],
    *,
    limit: int = 25,
    consulted_at: date | None = None,
) -> list[Position]:
    """Search Science Careers by keyword and return matching listings.

    One request per call (keywords are OR'd into a single query string
    the way the site's own search box does), not one request per
    keyword -- keep this polite.
    """
    consulted = consulted_at or date.today()
    try:
        response = client.get(
            SCIENCECAREERS_SEARCH_URL,
            params={"keywords": " ".join(keywords)},
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    tree = HTMLParser(response.text)
    seen_urls: set[str] = set()
    positions: list[Position] = []
    for anchor in tree.css("a"):
        href = (anchor.attributes.get("href") or "").strip()
        if "/job/" not in href:
            continue
        url = href if href.startswith("http") else f"https://jobs.sciencecareers.org{href}"
        if url in seen_urls:
            continue
        title = _clean_text(anchor.text(strip=True))
        if not title or title.lower() == "view details":
            continue
        seen_urls.add(url)
        matched = _matches_any_term(title, keywords)
        positions.append(
            Position(
                title=title,
                organisation="unknown",
                country="unknown",
                position_type="unknown",
                url=url,
                source="sciencecareers",
                consulted_at=consulted,
                matched_terms=matched,
            )
        )
        if len(positions) >= limit:
            break
    return positions


# -- EURAXESS -------------------------------------------------------------
# Drupal-based portal. Its exposed `keywords`/`search_api_fulltext` query
# params do NOT filter results server-side when fetched with a plain GET
# (verified 2026-10-10: both return the same unfiltered "newest 10"
# regardless of the query), likely because the real filter form requires
# a session-bound form_build_id token. So this fetches the newest N
# listings unfiltered and matches keywords against title + the detail
# page's Research Field/Offer Description text client-side, same as
# score.py's literal term-overlap approach -- never silently assumes the
# EURAXESS "showing results" count reflects the query.
#
# There IS a real server-side filter, though: the `f[0]=job_research_field:
# <id>` facet (verified 2026-10-10 -- filters from 6731 down to 43 for id
# 311 "Statistics", and multiple f[N] params OR together, and `page=N`
# paginates the filtered set correctly). The catch is it's discipline-coded,
# not free text: there is no "Bioinformatics" or "Microbiome" field in its
# ~366-option taxonomy, only broad disciplines like "Statistics"/"Biology"/
# "Ecology"/"Environmental science". So a keyword that happens to equal one
# of those discipline names gets the precise, fully-paginated facet query;
# any keyword that doesn't (most free-text research terms) falls back to
# the unfiltered-scan-and-client-filter approach described above, over
# whatever's left of `pages`.

EURAXESS_SEARCH_URL = "https://euraxess.ec.europa.eu/jobs/search"
EURAXESS_BASE_URL = "https://euraxess.ec.europa.eu"

_JOB_LINK_RE = re.compile(r"^/jobs/\d+$")


def _euraxess_research_field_ids(client: httpx.Client) -> dict[str, str]:
    """Map lowercased EURAXESS research-field names to their facet ids.

    One extra request per call to re-read the search page's own <select>
    (its options could change over time, so this isn't hardcoded).
    Returns {} if the page/select can't be found -- callers then skip
    facet filtering entirely rather than guessing an id.
    """
    try:
        response = client.get(EURAXESS_SEARCH_URL, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return {}
    tree = HTMLParser(response.text)
    select = tree.css_first('select[name="job_research_field[]"]')
    if select is None:
        return {}
    return {
        option.text(strip=True).lower(): option.attributes.get("value", "")
        for option in select.css("option")
        if option.attributes.get("value")
    }


def _list_job_titles_by_research_field(
    client: httpx.Client, field_ids: list[str], pages: int
) -> dict[str, str]:
    """List job hrefs -> titles matching any of the given facet ids, paginated."""
    titles_by_href: dict[str, str] = {}
    params = [("f[%d]" % i, f"job_research_field:{field_id}") for i, field_id in enumerate(field_ids)]
    for page in range(pages):
        page_params = params + ([("page", page)] if page else [])
        try:
            response = client.get(EURAXESS_SEARCH_URL, params=page_params, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            break
        tree = HTMLParser(response.text)
        found_any = False
        for anchor in tree.css("a"):
            href = (anchor.attributes.get("href") or "").strip()
            if _JOB_LINK_RE.match(href):
                found_any = True
                if href not in titles_by_href:
                    title = _clean_text(anchor.text(strip=True))
                    if title:
                        titles_by_href[href] = title
        if not found_any:
            break  # ran past the last page of results
    return titles_by_href


def _euraxess_detail_fields(client: httpx.Client, url: str) -> dict[str, str]:
    """Pull the labelled Job Information fields off a EURAXESS job page.

    Returns {} if the page can't be fetched/parsed -- callers then leave
    the corresponding Position fields as "unknown" rather than guessing.
    """
    try:
        response = client.get(url, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError:
        return {}

    # The "Job Information" panel is a definition list (ECL design
    # system: <dt class="ecl-description-list__term">Label</dt><dd
    # class="ecl-description-list__definition">value</dd>) -- verified
    # against a real listing on 2026-10-10. The page also has a second,
    # unlabelled definition list for "Work Location(s)" further down
    # that repeats some of the same labels (e.g. "Country"), so only the
    # FIRST occurrence of each label (the Job Information one) is kept.
    tree = HTMLParser(response.text)
    terms = tree.css("dt.ecl-description-list__term")
    definitions = tree.css("dd.ecl-description-list__definition")
    fields: dict[str, str] = {}
    for term, definition in zip(terms, definitions):
        label = term.text(strip=True)
        if label and label not in fields:
            fields[label] = definition.text(separator=" ", strip=True)
    return fields


def fetch_euraxess_positions(
    client: httpx.Client,
    keywords: list[str],
    *,
    pages: int = 2,
    fetch_details: bool = True,
    consulted_at: date | None = None,
) -> list[Position]:
    """Fetch EURAXESS listings matching the given keywords.

    Two paths, combined:

    1. Keywords that exactly match one of EURAXESS's own ~366 discipline
       names (case-insensitive -- e.g. "statistics", "biology",
       "ecology") use the real server-side `f[N]=job_research_field:<id>`
       facet filter, fully paginated (`pages` result pages of 10, filtered
       -- a higher `pages` here means more of an ALREADY-FILTERED set).
    2. Keywords that don't match any discipline name (most free-text
       research terms, e.g. "microbiome", "bioinformatics") fall back to
       scanning the newest `pages` pages UNFILTERED and matching
       client-side against title + Research Field + Organisation -- a
       higher `pages` here means more of the newest listings scanned for
       a chance match, not a more targeted query.

    `fetch_details=False` skips the per-listing detail fetch entirely
    (faster, but country/organisation/deadline stay "unknown", and path 2
    degrades to title-only matching).
    """
    consulted = consulted_at or date.today()

    field_name_to_id = _euraxess_research_field_ids(client) if keywords else {}
    facet_keywords = [k for k in keywords if k.lower() in field_name_to_id]
    freetext_keywords = [k for k in keywords if k.lower() not in field_name_to_id]

    titles_by_href: dict[str, str] = {}
    # One facet query per keyword (not one combined OR query) so each
    # resulting href can be attributed back to the specific keyword that
    # matched it, for matched_terms below.
    facet_keywords_by_href: dict[str, list[str]] = {}
    for keyword in facet_keywords:
        field_id = field_name_to_id[keyword.lower()]
        by_facet = _list_job_titles_by_research_field(client, [field_id], pages)
        titles_by_href.update(by_facet)
        for href in by_facet:
            facet_keywords_by_href.setdefault(href, []).append(keyword)

    if freetext_keywords:
        for page in range(pages):
            try:
                response = client.get(
                    EURAXESS_SEARCH_URL,
                    params={"page": page} if page else {},
                    follow_redirects=True,
                )
                response.raise_for_status()
            except httpx.HTTPError:
                break
            tree = HTMLParser(response.text)
            for anchor in tree.css("a"):
                href = (anchor.attributes.get("href") or "").strip()
                if _JOB_LINK_RE.match(href) and href not in titles_by_href:
                    title = _clean_text(anchor.text(strip=True))
                    if title:
                        titles_by_href[href] = title

    positions: list[Position] = []
    for href, title in titles_by_href.items():
        url = f"{EURAXESS_BASE_URL}{href}"
        fields = _euraxess_detail_fields(client, url) if fetch_details else {}
        haystack = " ".join(
            [title, fields.get("Research Field", ""), fields.get("Organisation/Company", "")]
        )
        # A facet hit is already a confirmed match on that discipline even
        # when the (differently-worded) discipline name isn't literally in
        # the title/fields text -- e.g. field "Statistics" matching a
        # listing titled "Multi-source data and non-probability samples".
        matched = facet_keywords_by_href.get(href, []) + _matches_any_term(
            haystack, freetext_keywords
        )
        if not matched:
            continue
        # eligibility_note is always None here: the "Requirements" section
        # (nationality/visa language, when a listing states any) sits in
        # unlabelled free-text further down the page, not in the dt/dd
        # Job Information panel this parses -- extracting it reliably
        # would need more than this fetcher currently does, so it's left
        # unset rather than guessed from a fragile heuristic.
        positions.append(
            Position(
                title=title,
                organisation=fields.get("Organisation/Company", "unknown"),
                country=fields.get("Country", "unknown"),
                position_type=fields.get("Researcher Profile", "unknown"),
                url=url,
                source="euraxess",
                consulted_at=consulted,
                deadline=fields.get("Application Deadline", "unknown"),
                matched_terms=matched,
            )
        )
    return positions
