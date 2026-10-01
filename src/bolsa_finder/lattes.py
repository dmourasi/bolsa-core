"""Lattes CV intake: parse, staleness check, and merge into a Profile.

Architecture note: this module is a PURE PARSER. It never calls an LLM.
Free-text fields (project descriptions) are returned as-is in
`description_raw` so the Claude Code skill flow can read them and propose
`methods_inferred`/`research_areas` candidates -- those only become part
of a `Profile` after the user confirms them (see `merge_into_profile`).
This keeps the package deterministic and testable without mocking an LLM.

PII handling: CPF, RG/documento de identidade, endereço, telefone and
exact birth date are not "filtered out" -- they have no field anywhere in
LattesExtract, so there is no field to accidentally serialize. The parser
must never read those XML attributes/tags into any model, and must never
log or persist the raw XML content.

KNOWN LIMITATION (see project plan, Fase B): `parse_lattes_xml` below is
implemented against the publicly documented CNPq Lattes XML schema
(ESTRUTURA_CURRICULO) from general knowledge, NOT from inspecting a real
exported file yet. It must be re-validated against a real sample in
`fixtures/private/` before being trusted for an actual Lattes export --
tag names/casing/attributes may differ by Lattes export version.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from lxml import etree
from pydantic import BaseModel, Field

from bolsa_finder.profile import (
    AcademicStage,
    LanguageProficiency,
    NonEmptyStr,
    Profile,
    TargetLevel,
    TimeWindow,
)

Origin = Literal["lattes_xml", "llm_inferred", "user_confirmed"]
SourceFormat = Literal["xml", "pdf"]

STALENESS_THRESHOLD_DAYS = 183  # ~6 months


class Education(BaseModel):
    level: str
    institution: str
    started: date | None = None
    finished: date | None = None


class ProfessionalActivity(BaseModel):
    institution: str
    role: str
    started: date | None = None
    finished: date | None = None  # None = ongoing


class Project(BaseModel):
    title: str
    description_raw: str
    started: date | None = None
    finished: date | None = None


class Publication(BaseModel):
    title: str
    year: int | None = None
    doi: str | None = None
    venue: str | None = None


class LanguageSkill(BaseModel):
    """Self-reported proficiency as the Lattes CV describes it.

    This is NOT the certified ProficiencyLevel that Profile.languages
    requires -- that must always be asked explicitly (see merge_into_profile).
    """

    language: str
    self_reported_proficiency: str


class ProvenancedList(BaseModel):
    values: list[str] = Field(default_factory=list)
    origin: Origin


class LattesExtract(BaseModel):
    full_name: str
    orcid: str | None = None
    last_update: date | None = None
    source_format: SourceFormat
    education: list[Education] = Field(default_factory=list)
    professional_activities: list[ProfessionalActivity] = Field(default_factory=list)
    cnpq_areas: ProvenancedList = Field(default_factory=lambda: ProvenancedList(values=[], origin="lattes_xml"))
    languages: list[LanguageSkill] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    publications: list[Publication] = Field(default_factory=list)
    methods_inferred: ProvenancedList | None = None


def check_staleness(extract: LattesExtract, as_of: date | None = None) -> str | None:
    """Return a warning string if the CV's last update is >6 months old."""
    if extract.last_update is None:
        return "Data de atualização do currículo Lattes não encontrada; não é possível avaliar desatualização."
    today = as_of or date.today()
    age = today - extract.last_update
    if age > timedelta(days=STALENESS_THRESHOLD_DAYS):
        return (
            f"Currículo Lattes atualizado pela última vez em {extract.last_update} "
            f"({age.days} dias atrás) -- considere pedir ao candidato para atualizá-lo antes de usar."
        )
    return None


def _parse_date(value: str | None) -> date | None:
    """Lattes XML encodes dates as separate year (and sometimes month) attributes
    handled by the caller; this only handles whole-date strings like DDMMYYYY."""
    if not value:
        return None
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        day, month, year = int(value[0:2]), int(value[2:4]), int(value[4:8])
        return date(year, month, day)
    if len(value) == 4 and value.isdigit():
        return date(int(value), 1, 1)
    return None


def parse_lattes_xml(xml_path: str | Path) -> LattesExtract:
    """Parse a Lattes XML export into a LattesExtract.

    PROVISIONAL (see module docstring): built from the publicly documented
    CNPq schema, pending validation against a real export in
    fixtures/private/. Unrecognized/missing tags are skipped, never guessed.
    """
    tree = etree.parse(str(xml_path))
    root = tree.getroot()

    last_update = _parse_date(root.get("DATA-ATUALIZACAO"))

    dados_gerais = root.find(".//DADOS-GERAIS")
    full_name = (dados_gerais.get("NOME-COMPLETO") if dados_gerais is not None else None) or ""
    orcid = dados_gerais.get("ORCID-ID") if dados_gerais is not None else None

    education: list[Education] = []
    for tag, level in [
        ("GRADUACAO", "graduacao"),
        ("MESTRADO", "mestrado"),
        ("DOUTORADO", "doutorado"),
        ("POS-DOUTORADO", "pos-doutorado"),
    ]:
        for node in root.findall(f".//FORMACAO-ACADEMICA-TITULACAO/{tag}"):
            education.append(
                Education(
                    level=level,
                    institution=node.get("NOME-INSTITUICAO", ""),
                    started=_parse_date(node.get("ANO-DE-INICIO")),
                    finished=_parse_date(node.get("ANO-DE-CONCLUSAO")),
                )
            )

    professional_activities: list[ProfessionalActivity] = []
    for node in root.findall(".//ATUACOES-PROFISSIONAIS/ATUACAO-PROFISSIONAL/VINCULOS/VINCULO"):
        parent = node.getparent().getparent()
        institution = parent.get("NOME-INSTITUICAO", "") if parent is not None else ""
        professional_activities.append(
            ProfessionalActivity(
                institution=institution,
                role=node.get("OUTRO-ENQUADRAMENTO-FUNCIONAL-INFORMADO") or node.get("TIPO-DE-VINCULO", ""),
                started=_parse_date(node.get("ANO-INICIO")),
                finished=_parse_date(node.get("ANO-FIM")),
            )
        )

    cnpq_area_names: list[str] = []
    for node in root.findall(".//AREAS-DE-ATUACAO/AREA-DE-ATUACAO"):
        for key, value in node.attrib.items():
            if key.startswith("NOME-DA-SUB-AREA") or key.startswith("NOME-DA-AREA"):
                if value:
                    cnpq_area_names.append(value)

    languages: list[LanguageSkill] = []
    for node in root.findall(".//IDIOMAS/IDIOMA"):
        languages.append(
            LanguageSkill(
                language=node.get("NOME", ""),
                self_reported_proficiency=node.get("PROFICIENCIA-LEITURA", "") or node.get("PROFICIENCIA-FALA", ""),
            )
        )

    projects: list[Project] = []
    for node in root.findall(".//PROJETOS-DE-PESQUISA/PROJETO-DE-PESQUISA"):
        projects.append(
            Project(
                title=node.get("NOME-DO-PROJETO", ""),
                description_raw=node.get("DESCRICAO-DO-PROJETO", ""),
                started=_parse_date(node.get("ANO-INICIO")),
                finished=_parse_date(node.get("ANO-FIM")),
            )
        )

    publications: list[Publication] = []
    for node in root.findall(".//PRODUCAO-BIBLIOGRAFICA//ARTIGO-PUBLICADO/DADOS-BASICOS-DO-ARTIGO"):
        publications.append(
            Publication(
                title=node.get("TITULO-DO-ARTIGO", ""),
                year=int(node.get("ANO-DO-ARTIGO")) if node.get("ANO-DO-ARTIGO", "").isdigit() else None,
                doi=node.get("DOI"),
                venue=None,
            )
        )

    return LattesExtract(
        full_name=full_name,
        orcid=orcid,
        last_update=last_update,
        source_format="xml",
        education=education,
        professional_activities=professional_activities,
        cnpq_areas=ProvenancedList(values=cnpq_area_names, origin="lattes_xml"),
        languages=languages,
        projects=projects,
        publications=publications,
    )


def merge_into_profile(
    extract: LattesExtract,
    *,
    research_areas: list[str],
    methods: list[str],
    target_level: TargetLevel,
    academic_stage: AcademicStage,
    languages: list[LanguageProficiency],
    nationality: str,
    funding_required: bool,
    time_window: TimeWindow,
    geographic_restrictions: list[NonEmptyStr] | None = None,
    cv_summary: str | None = None,
) -> Profile:
    """Build a Profile from a (user-confirmed) LattesExtract plus the fields
    that must always be asked explicitly and are never inferred from Lattes:
    target_level, academic_stage.expected_defense, certified language
    proficiency, nationality, geographic_restrictions, funding_required,
    and time_window.

    `research_areas`/`methods` must already be the user-confirmed lists
    (e.g. extract.cnpq_areas.values and extract.methods_inferred.values
    after the skill flow had the user approve them) -- this function does
    not read provenance itself, it trusts what it's given.
    """
    return Profile(
        research_areas=research_areas,
        methods=methods,
        cv_summary=cv_summary or _default_cv_summary(extract),
        academic_stage=academic_stage,
        target_level=target_level,
        languages=languages,
        nationality=nationality,
        geographic_restrictions=geographic_restrictions or [],
        funding_required=funding_required,
        time_window=time_window,
    )


def _default_cv_summary(extract: LattesExtract) -> str:
    latest = extract.education[-1] if extract.education else None
    if latest is None:
        return extract.full_name or "Candidate profile derived from Lattes CV."
    return f"{latest.level.capitalize()} at {latest.institution} ({extract.full_name})."
