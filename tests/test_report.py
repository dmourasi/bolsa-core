from datetime import date

from bolsa_finder.funding import FundingOpportunity
from bolsa_finder.report import DISCLAIMER, build_report, render_markdown
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
