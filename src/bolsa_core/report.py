"""Final report generation: ranked Markdown + a validated JSON payload.

Every funding line in the Markdown output carries its source URL and the
date it was checked (see FundingOpportunity), and the report always ends
with a reminder to reconfirm against the official edital before acting --
this file does not add any new claims about deadlines/values/eligibility
itself, it only renders what funding.py/score.py already produced.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel

from bolsa_core.funding import FundingOpportunity
from bolsa_core.score import FitScore

DISCLAIMER = (
    "Todas as informações de prazo, valor e elegibilidade devem ser "
    "reconfirmadas no edital oficial antes de qualquer decisão ou candidatura. "
    "Este relatório é um ponto de partida para a investigação, não uma fonte final."
)


class Report(BaseModel):
    generated_at: date
    funding_opportunities: list[FundingOpportunity]
    fit_scores: list[FitScore]
    disclaimer: str = DISCLAIMER


def _parse_concatenated_json_objects(text: str) -> list[dict]:
    """Parse a file containing one or more JSON objects back-to-back, or
    a single JSON array of objects.

    `bolsa-finder funding cnpq`/`fapeam` print one JSON object per
    modality, not a JSON array, so a redirected output file (e.g.
    `funding_cnpq.json`) is several concatenated objects -- a plain
    `json.loads` would fail on anything but a single-opportunity file.
    Manually-assembled sources (see `references/fontes-*.md`) are
    sometimes written as a single JSON array instead -- each top-level
    array found is flattened into its individual objects too, so both
    conventions load the same way.
    """
    decoder = json.JSONDecoder()
    objects: list[dict] = []
    pos = 0
    length = len(text)
    while pos < length:
        while pos < length and text[pos].isspace():
            pos += 1
        if pos >= length:
            break
        obj, pos = decoder.raw_decode(text, pos)
        if isinstance(obj, list):
            objects.extend(obj)
        else:
            objects.append(obj)
    return objects


def load_funding_opportunities(paths: list[Path]) -> list[FundingOpportunity]:
    """Load FundingOpportunity records from one or more `funding_*.json`
    files, each possibly holding several concatenated JSON objects."""
    opportunities: list[FundingOpportunity] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for obj in _parse_concatenated_json_objects(text):
            opportunities.append(FundingOpportunity.model_validate(obj))
    return opportunities


def load_fit_scores(path: Path | None) -> list[FitScore]:
    """Load FitScore records from a JSON array file, or [] if no path given."""
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [FitScore.model_validate(item) for item in data]


def build_report(
    funding_opportunities: list[FundingOpportunity],
    fit_scores: list[FitScore],
    generated_at: date | None = None,
) -> Report:
    ranked = sorted(fit_scores, key=lambda fit: fit.score, reverse=True)
    return Report(
        generated_at=generated_at or date.today(),
        funding_opportunities=funding_opportunities,
        fit_scores=ranked,
        disclaimer=DISCLAIMER,
    )


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"# Relatório de bolsas e pesquisadores — gerado em {report.generated_at}")
    lines.append("")
    lines.append(f"> {report.disclaimer}")
    lines.append("")

    lines.append("## Bolsas e fontes de financiamento")
    lines.append("")
    if not report.funding_opportunities:
        lines.append("Nenhuma fonte de financiamento verificada nesta execução.")
    for funding in report.funding_opportunities:
        lines.append(f"### {funding.name} ({funding.agency})")
        lines.append(f"- Região/país: {funding.country_or_region}")
        lines.append(f"- Nível(is): {', '.join(funding.target_levels)}")
        lines.append(f"- Valor: {funding.amount}")
        lines.append(f"- Prazo: {funding.deadline}")
        lines.append(f"- Elegibilidade para brasileiros: **{funding.eligibility_brazilian}**")
        if funding.eligibility_evidence:
            lines.append(f"  - Trecho do edital/fonte: \"{funding.eligibility_evidence}\"")
        if funding.research_areas != "any":
            areas = (
                ", ".join(funding.research_areas)
                if isinstance(funding.research_areas, list)
                else funding.research_areas
            )
            lines.append(f"- Área(s) de pesquisa: {areas}")
        if funding.application_notes:
            lines.append(f"- Observações da candidatura: {funding.application_notes}")
        lines.append(f"- Fonte: {funding.url} (consultado em {funding.consulted_at})")
        lines.append("")

    lines.append("## Pesquisadores ranqueados por fit")
    lines.append("")
    if not report.fit_scores:
        lines.append("Nenhum pesquisador avaliado nesta execução.")
    for rank, fit in enumerate(report.fit_scores, start=1):
        lines.append(f"### {rank}. {fit.researcher_name} — {fit.institution_name} (score: {fit.score})")
        if fit.evidence:
            lines.append("- Evidência de fit:")
            for item in fit.evidence:
                lines.append(f"  - {item}")
        else:
            lines.append("- Nenhuma evidência de overlap encontrada nas publicações analisadas.")
        lines.append("- Pendências a verificar:")
        for pending in fit.pending_checks:
            lines.append(f"  - {pending}")
        lines.append("")

    return "\n".join(lines)
