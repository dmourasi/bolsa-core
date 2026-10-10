from datetime import date

import httpx

from bolsa_core.positions import (
    EURAXESS_SEARCH_URL,
    SCIENCECAREERS_SEARCH_URL,
    fetch_euraxess_positions,
    fetch_sciencecareers_positions,
)

# Minimal snippets mirroring the real markup structure (verified against
# live pages on 2026-10-10), not full page dumps.

SCIENCECAREERS_SNIPPET_HTML = """
<html><body>
  <a href="/job/680240/associate-assistant-professor-of-microbiome/">
    Associate/Assistant Professor of Microbiome
  </a>
  <a href="/job/680240/associate-assistant-professor-of-microbiome/">View details</a>
  <a href="/job/679654/open-rank-faculty-positions/">
    Open Rank Faculty Positions in Emerging Pathogen Research
  </a>
  <a href="/analytics/some-tracking-pixel/">not a job link</a>
</body></html>
"""

EURAXESS_SEARCH_SNIPPET_HTML = """
<html><body>
  <select name="job_research_field[]">
    <option value="311">Statistics</option>
    <option value="41">Biology</option>
  </select>
  <a href="/jobs/471908">Postdoc Electron Optics and Instrumentation</a>
  <a href="/jobs/471917">PhD Candidate in Microbiome Research</a>
  <a href="/jobs/471920/apply">not a bare job id -- ignored by the anchored regex</a>
</body></html>
"""

EURAXESS_FACET_RESULTS_HTML = """
<html><body>
  <a href="/jobs/471636">PhD in biostatistics: biodiversity monitoring</a>
</body></html>
"""

EURAXESS_DETAIL_HTML = """
<html><body>
<dl>
  <dt class="ecl-description-list__term">Organisation/Company</dt>
  <dd class="ecl-description-list__definition"><div>Delft University of Technology</div></dd>
  <dt class="ecl-description-list__term">Research Field</dt>
  <dd class="ecl-description-list__definition"><div>Biology - Microbiology</div></dd>
  <dt class="ecl-description-list__term">Researcher Profile</dt>
  <dd class="ecl-description-list__definition"><div>First Stage Researcher (R1)</div></dd>
  <dt class="ecl-description-list__term">Application Deadline</dt>
  <dd class="ecl-description-list__definition"><div>8 Nov 2026 - 22:59 (UTC)</div></dd>
  <dt class="ecl-description-list__term">Country</dt>
  <dd class="ecl-description-list__definition"><div>Netherlands</div></dd>
  <dt class="ecl-description-list__term">Type of Contract</dt>
  <dd class="ecl-description-list__definition"><div>Temporary</div></dd>
</dl>
</body></html>
"""

EURAXESS_DETAIL_HTML_UNRELATED = """
<html><body>
<dl>
  <dt class="ecl-description-list__term">Organisation/Company</dt>
  <dd class="ecl-description-list__definition"><div>Some Institute</div></dd>
  <dt class="ecl-description-list__term">Research Field</dt>
  <dd class="ecl-description-list__definition"><div>Astrophysics</div></dd>
  <dt class="ecl-description-list__term">Country</dt>
  <dd class="ecl-description-list__definition"><div>Germany</div></dd>
</dl>
</body></html>
"""


def test_fetch_sciencecareers_positions_parses_listings(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{SCIENCECAREERS_SEARCH_URL}?keywords=microbiome",
        html=SCIENCECAREERS_SNIPPET_HTML,
    )

    with httpx.Client() as client:
        positions = fetch_sciencecareers_positions(
            client, ["microbiome"], consulted_at=date(2026, 10, 10)
        )

    assert len(positions) == 2
    assert positions[0].title == "Associate/Assistant Professor of Microbiome"
    assert positions[0].source == "sciencecareers"
    assert positions[0].consulted_at == date(2026, 10, 10)
    assert positions[0].matched_terms == ["microbiome"]
    # "View details" duplicate link to the same job must be deduplicated.
    assert len({p.url for p in positions}) == 2


def test_fetch_sciencecareers_positions_returns_empty_on_http_error(httpx_mock) -> None:
    httpx_mock.add_response(
        url=f"{SCIENCECAREERS_SEARCH_URL}?keywords=microbiome", status_code=500
    )

    with httpx.Client() as client:
        positions = fetch_sciencecareers_positions(client, ["microbiome"])

    assert positions == []


def test_fetch_euraxess_positions_filters_by_keyword_in_research_field(httpx_mock) -> None:
    # One request to resolve the discipline-name -> id map, one to scan
    # page 0 for the freetext fallback ("microbiology" isn't an exact
    # discipline name, so it takes that path, not the facet one).
    httpx_mock.add_response(url=EURAXESS_SEARCH_URL, html=EURAXESS_SEARCH_SNIPPET_HTML)
    httpx_mock.add_response(url=EURAXESS_SEARCH_URL, html=EURAXESS_SEARCH_SNIPPET_HTML)
    httpx_mock.add_response(
        url="https://euraxess.ec.europa.eu/jobs/471908", html=EURAXESS_DETAIL_HTML_UNRELATED
    )
    httpx_mock.add_response(
        url="https://euraxess.ec.europa.eu/jobs/471917", html=EURAXESS_DETAIL_HTML
    )

    with httpx.Client() as client:
        positions = fetch_euraxess_positions(
            client, ["microbiology"], pages=1, consulted_at=date(2026, 10, 10)
        )

    assert len(positions) == 1
    position = positions[0]
    assert position.title == "PhD Candidate in Microbiome Research"
    assert position.organisation == "Delft University of Technology"
    assert position.country == "Netherlands"
    assert position.deadline == "8 Nov 2026 - 22:59 (UTC)"
    assert position.source == "euraxess"
    assert position.matched_terms == ["microbiology"]
    assert position.eligibility_note is None


def test_fetch_euraxess_positions_skips_detail_fetch_when_disabled(httpx_mock) -> None:
    httpx_mock.add_response(url=EURAXESS_SEARCH_URL, html=EURAXESS_SEARCH_SNIPPET_HTML)
    httpx_mock.add_response(url=EURAXESS_SEARCH_URL, html=EURAXESS_SEARCH_SNIPPET_HTML)

    with httpx.Client() as client:
        positions = fetch_euraxess_positions(
            client, ["microbiome"], pages=1, fetch_details=False
        )

    # Without detail fetches there is no Research Field/Organisation text
    # to match against beyond the title itself.
    assert len(positions) == 1
    assert positions[0].title == "PhD Candidate in Microbiome Research"
    assert positions[0].organisation == "unknown"
    assert positions[0].deadline == "unknown"


def test_fetch_euraxess_positions_uses_research_field_facet_when_keyword_matches() -> None:
    import httpx as httpx_module

    facet_url = httpx_module.URL(
        EURAXESS_SEARCH_URL, params=[("f[0]", "job_research_field:311")]
    )

    def handler(request: httpx_module.Request) -> httpx_module.Response:
        if request.url.path == "/jobs/search" and not request.url.params:
            return httpx_module.Response(200, html=EURAXESS_SEARCH_SNIPPET_HTML)
        if request.url == facet_url:
            return httpx_module.Response(200, html=EURAXESS_FACET_RESULTS_HTML)
        if request.url.path == "/jobs/471636":
            return httpx_module.Response(200, html=EURAXESS_DETAIL_HTML)
        raise AssertionError(f"Unexpected request: {request.url}")

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        positions = fetch_euraxess_positions(
            client, ["Statistics"], pages=1, consulted_at=date(2026, 10, 10)
        )

    assert len(positions) == 1
    assert positions[0].title == "PhD in biostatistics: biodiversity monitoring"
    assert positions[0].matched_terms == ["Statistics"]
    assert positions[0].country == "Netherlands"
