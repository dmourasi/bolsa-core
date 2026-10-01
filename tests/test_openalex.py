import httpx
import pytest

from bolsa_finder.openalex import OpenAlexClient


@pytest.fixture
def client(httpx_mock) -> OpenAlexClient:
    http_client = httpx.Client(base_url="https://api.openalex.org", timeout=30.0)
    return OpenAlexClient(contact_email="test@example.com", client=http_client)


def test_search_topics_includes_polite_pool_param(httpx_mock, client: OpenAlexClient) -> None:
    httpx_mock.add_response(
        url="https://api.openalex.org/topics?search=microbiome&per_page=10&mailto=test%40example.com",
        json={
            "results": [
                {"id": "https://openalex.org/T10159", "display_name": "Microbiome", "works_count": 1234},
            ]
        },
    )

    topics = client.search_topics("microbiome")

    assert len(topics) == 1
    assert topics[0].id == "https://openalex.org/T10159"
    assert topics[0].display_name == "Microbiome"
    assert topics[0].works_count == 1234


def test_institutions_for_topic_parses_group_by(httpx_mock, client: OpenAlexClient) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.openalex.org/works"
            "?filter=topics.id%3AT10159%2Cpublication_year%3A%3E2021"
            "&group_by=authorships.institutions.id&per_page=25&mailto=test%40example.com"
        ),
        json={
            "group_by": [
                {
                    "key": "https://openalex.org/I123",
                    "key_display_name": "Universidade Federal Rural de Pernambuco",
                    "count": 42,
                },
                # Works without a resolvable institution: must be filtered out.
                {"key": "unknown", "key_display_name": "", "count": 5},
            ]
        },
    )

    institutions = client.institutions_for_topic("T10159", since_year=2022)

    assert len(institutions) == 1
    assert institutions[0].id == "https://openalex.org/I123"
    assert institutions[0].display_name == "Universidade Federal Rural de Pernambuco"
    assert institutions[0].recent_works_count == 42


def test_authors_for_topic_institution_parses_group_by(httpx_mock, client: OpenAlexClient) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.openalex.org/works"
            "?filter=topics.id%3AT10159%2Cauthorships.institutions.id%3AI123%2Cpublication_year%3A%3E2021"
            "&group_by=authorships.author.id&per_page=25&mailto=test%40example.com"
        ),
        json={
            "group_by": [
                {
                    "key": "https://openalex.org/A456",
                    "key_display_name": "Jane Researcher",
                    "count": 7,
                }
            ]
        },
    )

    authors = client.authors_for_topic_institution("T10159", "I123", since_year=2022)

    assert len(authors) == 1
    assert authors[0].id == "https://openalex.org/A456"
    assert authors[0].display_name == "Jane Researcher"
    assert authors[0].recent_works_count == 7


def test_works_for_author_parses_results(httpx_mock, client: OpenAlexClient) -> None:
    httpx_mock.add_response(
        url=(
            "https://api.openalex.org/works"
            "?filter=authorships.author.id%3AA456%2Cpublication_year%3A%3E2021"
            "&sort=publication_year%3Adesc&per_page=25&mailto=test%40example.com"
        ),
        json={
            "results": [
                {
                    "id": "https://openalex.org/W789",
                    "display_name": "Gut microbiome diversity in longitudinal NGS studies",
                    "publication_year": 2024,
                    "doi": "https://doi.org/10.1/abc",
                    "topics": [{"display_name": "Gut microbiota and health"}],
                },
                # Missing display_name must be skipped, not crash or guess a title.
                {"id": "https://openalex.org/W000", "publication_year": 2023, "topics": []},
            ]
        },
    )

    publications = client.works_for_author("A456", since_year=2022)

    assert len(publications) == 1
    assert publications[0].title == "Gut microbiome diversity in longitudinal NGS studies"
    assert publications[0].year == 2024
    assert publications[0].url == "https://doi.org/10.1/abc"
    assert publications[0].topics == ["Gut microbiota and health"]


def test_raises_on_http_error(httpx_mock, client: OpenAlexClient) -> None:
    httpx_mock.add_response(status_code=500)

    with pytest.raises(httpx.HTTPStatusError):
        client.search_topics("microbiome")
