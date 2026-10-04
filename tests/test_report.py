import json
from datetime import date
from pathlib import Path

from bolsa_finder.funding import FundingOpportunity
from bolsa_finder.report import (
    DISCLAIMER,
    build_report,
    load_fit_scores,
    load_funding_opportunities,
    render_markdown,
)
from bolsa_finder.score import FitScore


def _funding(**overrides) -> FundingOpportunity:
    defaults = dict(
        name="Test Grant",
        agency="Test Agency",
        country_or_region="Testland",
        target_levels=["sanduiche"],
        amount="unknown",
        deadline="unknown",
        url="https://example.com/grant",
        consulted_at=date(2026, 1, 1),
        eligibility_brazilian="confirmed",
        eligibility_evidence="Brazilian applicants are eligible.",
    )
    defaults.update(overrides)
    return FundingOpportunity(**defaults)


def _fit(**overrides) -> FitScore:
    defaults = dict(
        researcher_id="A1",
        researcher_name="Dr. Example",
        institution_name="Example University",
        score=1.0,
        evidence=["Topic overlap: profile term 'bioinformatics' matches ..."],
        pending_checks=["Confirm recruiting status directly."],
    )
    defaults.update(overrides)
    return FitScore(**defaults)


def test_build_report_sorts_fit_scores_descending() -> None:
    low = _fit(researcher_id="low", score=0.5)
    high = _fit(researcher_id="high", score=2.0)

    report = build_report([], [low, high], generated_at=date(2026, 1, 1))

    assert [f.researcher_id for f in report.fit_scores] == ["high", "low"]


def test_report_json_round_trips() -> None:
    report = build_report([_funding()], [_fit()], generated_at=date(2026, 1, 1))

    dumped = report.model_dump_json()

    assert "Test Grant" in dumped
    assert "Dr. Example" in dumped


def test_markdown_contains_disclaimer_and_source_attribution() -> None:
    report = build_report([_funding()], [_fit()], generated_at=date(2026, 1, 1))

    markdown = render_markdown(report)

    assert DISCLAIMER in markdown
    assert "https://example.com/grant" in markdown
    assert "2026-01-01" in markdown
    assert "confirmed" in markdown


def test_markdown_handles_empty_results_without_fabricating_data() -> None:
    report = build_report([], [], generated_at=date(2026, 1, 1))

    markdown = render_markdown(report)

    assert "Nenhuma fonte de financiamento verificada" in markdown
    assert "Nenhum pesquisador avaliado" in markdown


def test_load_funding_opportunities_parses_single_object_file(tmp_path: Path) -> None:
    path = tmp_path / "funding_daad.json"
    path.write_text(_funding(name="DAAD Grant").model_dump_json(indent=2), encoding="utf-8")

    opportunities = load_funding_opportunities([path])

    assert len(opportunities) == 1
    assert opportunities[0].name == "DAAD Grant"


def test_load_funding_opportunities_parses_concatenated_objects_file(tmp_path: Path) -> None:
    # Mirrors how `funding cnpq`/`funding fapeam` actually write their output:
    # one JSON object per modality, printed back-to-back, not a JSON array.
    path = tmp_path / "funding_cnpq.json"
    opportunities_in = [_funding(name="GDE"), _funding(name="SWE"), _funding(name="PDE")]
    path.write_text(
        "\n".join(o.model_dump_json(indent=2) for o in opportunities_in), encoding="utf-8"
    )

    opportunities = load_funding_opportunities([path])

    assert [o.name for o in opportunities] == ["GDE", "SWE", "PDE"]


def test_load_funding_opportunities_merges_multiple_files(tmp_path: Path) -> None:
    path_a = tmp_path / "funding_daad.json"
    path_a.write_text(_funding(name="DAAD").model_dump_json(), encoding="utf-8")
    path_b = tmp_path / "funding_capes.json"
    path_b.write_text(_funding(name="CAPES").model_dump_json(), encoding="utf-8")

    opportunities = load_funding_opportunities([path_a, path_b])

    assert {o.name for o in opportunities} == {"DAAD", "CAPES"}


def test_load_fit_scores_returns_empty_list_when_no_path_given() -> None:
    assert load_fit_scores(None) == []


def test_load_fit_scores_parses_json_array_file(tmp_path: Path) -> None:
    path = tmp_path / "fit_scores.json"
    path.write_text(json.dumps([_fit().model_dump()], default=str), encoding="utf-8")

    scores = load_fit_scores(path)

    assert len(scores) == 1
    assert scores[0].researcher_id == "A1"
