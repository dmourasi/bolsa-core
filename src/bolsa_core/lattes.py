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

VALIDATED (2026-10-10) against one real export in `fixtures/private/`
(not committed -- real PII). Three divergences from the publicly
documented CNPq schema this was originally built against were found and
fixed: VINCULOS is a self-closing leaf directly under ATUACAO-PROFISSIONAL
(no nested VINCULO child), PROJETO-DE-PESQUISA nests under
ATIVIDADES-DE-PARTICIPACAO-EM-PROJETO/PARTICIPACAO-EM-PROJETO rather than
a flat top-level wrapper, and ESPECIALIZACAO was missing from the
education tag list entirely -- see the inline NOTE comments at each
fix site. Only validated against one export version/year; a different
Lattes export vintage may still diverge, so unrecognized/missing tags
are still skipped, never guessed.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

import pymupdf
from lxml import etree
from pydantic import BaseModel, Field

from bolsa_core.profile import (
    AcademicStage,
    LanguageProficiency,
    NonEmptyStr,
    Profile,
    TargetLevel,
    TimeWindow,
)

Origin = Literal["lattes_cv", "llm_inferred", "user_confirmed"]
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
    cnpq_areas: ProvenancedList = Field(default_factory=lambda: ProvenancedList(values=[], origin="lattes_cv"))
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

    Validated against a real export (see module docstring). Unrecognized/
    missing tags are skipped, never guessed.
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
        ("ESPECIALIZACAO", "especializacao"),
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

    # NOTE: a real export nests one <VINCULOS .../> leaf per historical
    # stint directly under ATUACAO-PROFISSIONAL (attributes on VINCULOS
    # itself) -- there is no separate <VINCULO> child, unlike what the
    # publicly documented schema implies. Validated against a real
    # export in fixtures/private/ (see lattes.py module docstring).
    professional_activities: list[ProfessionalActivity] = []
    for node in root.findall(".//ATUACOES-PROFISSIONAIS/ATUACAO-PROFISSIONAL/VINCULOS"):
        parent = node.getparent()
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

    # NOTE: a real export nests PROJETO-DE-PESQUISA under
    # ATIVIDADES-DE-PARTICIPACAO-EM-PROJETO/PARTICIPACAO-EM-PROJETO
    # (itself inside the ATUACAO-PROFISSIONAL the project ran under),
    # not under a flat top-level PROJETOS-DE-PESQUISA wrapper. Validated
    # against a real export in fixtures/private/.
    projects: list[Project] = []
    for node in root.findall(".//ATIVIDADES-DE-PARTICIPACAO-EM-PROJETO/PARTICIPACAO-EM-PROJETO/PROJETO-DE-PESQUISA"):
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
        cnpq_areas=ProvenancedList(values=cnpq_area_names, origin="lattes_cv"),
        languages=languages,
        projects=projects,
        publications=publications,
    )


# Headers that bound a section. Includes headers we don't extract from
# (e.g. "Identificação", "Revisor de periódico") purely so their content
# doesn't bleed into the body of a section we DO care about -- this list
# was derived from a real Lattes PDF export (see README.lattes.md, Fase B).
_SECTION_HEADERS = [
    "Identificação",
    "Formação acadêmica/titulação",
    "Formação Complementar",
    "Atuação Profissional",
    "Revisor de periódico",
    "Projetos de pesquisa",
    "Áreas de atuação",
    "Idiomas",
    "Produções",
    "Produção bibliográfica",
    "Citações",
    "Artigos completos publicados em periódicos",
    "Artigos aceitos para publicação",
    "Apresentações de Trabalho",
]

_ORCID_RE = re.compile(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dXx]\b")
_LAST_UPDATE_RE = re.compile(r"ultima atualizacao[^0-9]*(\d{2}/\d{2}/\d{4})")
# A bare "YYYY" or "YYYY - YYYY"/"YYYY - Atual" paragraph, used in the real
# export as a standalone entry-separator before the entry's free text body.
_YEAR_MARKER_RE = re.compile(r"^\s*(\d{4})(?:\s*-\s*(\d{4}|Atual))?\s*$", re.IGNORECASE)
_NUMBERED_ITEM_RE = re.compile(r"^\s*\d+\.\s*$")
_INSTITUTION_RE = re.compile(
    # Deliberately excludes "." from the name portion so the lazy match
    # can't run through a prior sentence-ending period (e.g. a degree
    # description like "Doutorado ... Aplicada.") into the real
    # institution clause that follows it.
    r"([A-ZÀ-Ü][\wÀ-ÿ\s\-]*?,\s*[A-Z0-9][A-Z0-9\.\-\*]{1,20}\s*,\s*[\wÀ-ÿ]+)\."
)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_DOI_RE = re.compile(r"10\.\d{4,9}/\S+")
_EDUCATION_LEVEL_KEYWORDS = [
    ("pos-doutorado", "pos-doutorado"),
    ("doutorado", "doutorado"),
    ("mestrado", "mestrado"),
    ("gradua", "graduacao"),
]


def _strip_accents(text: str) -> str:
    """Normalize accented Portuguese text for comparison/regex matching.

    Used only to decide WHERE a header/keyword/date is, never to alter
    the actual content stored in the returned model (titles/descriptions
    keep their original accents).
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _split_sections(text: str) -> dict[str, str]:
    """Split Lattes PDF extract text into named sections by known headers.

    Best-effort: Lattes PDF exports are free-flowing prose, not tagged
    data, so this relies on the section headers appearing verbatim as
    their own line -- which is the common Lattes export layout, but not
    guaranteed across every export version. Header matching is
    accent/case-insensitive since PDF text extraction sometimes loses or
    mangles diacritics.
    """
    normalized_headers = {_strip_accents(h).lower(): h for h in _SECTION_HEADERS}
    lines = text.splitlines()
    sections: dict[str, list[str]] = {}
    seen: set[str] = set()
    current: str | None = None
    for line in lines:
        stripped_normalized = _strip_accents(line.strip()).lower()
        matched_header = normalized_headers.get(stripped_normalized)
        if matched_header:
            if matched_header in seen:
                # A real Lattes export can repeat a section's header
                # verbatim for an unrelated secondary listing further down
                # the document (observed: "Projetos de pesquisa" reused for
                # a short, distinct block near the end). Rather than guess
                # which occurrence is "the real one", keep the first and
                # drop everything until the next genuinely new header.
                current = None
                continue
            seen.add(matched_header)
            current = matched_header
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(body) for name, body in sections.items()}


def _parse_br_date(value: str) -> date | None:
    """DD/MM/YYYY, as used in the Lattes PDF's 'last updated' footer line."""
    try:
        day, month, year = (int(part) for part in value.split("/"))
        return date(year, month, day)
    except (ValueError, AttributeError):
        return None


def _education_level_from_text(text: str) -> str:
    normalized = _strip_accents(text).lower()
    for keyword, level in _EDUCATION_LEVEL_KEYWORDS:
        if keyword in normalized:
            return level
    return "unknown"


_LEADING_MARKER_SPLIT_RE = re.compile(r"^(\d{4}(?:\s*-\s*(?:\d{4}|Atual))?)\s+(\S.*)$", re.IGNORECASE)
# Tried in order: a full "YYYY - YYYY/Atual" range must win over treating
# just the trailing "YYYY" as the marker (greedy backtracking on a single
# combined pattern would otherwise prefer the shorter, wrong match -- e.g.
# splitting "...Bolsa. 2010 - 2014" as "...Bolsa. 2010 -" + "2014").
_TRAILING_MARKER_SPLIT_RES = [
    re.compile(r"^(.*\S)\s+(\d{4}\s*-\s*(?:\d{4}|Atual))$", re.IGNORECASE),
    re.compile(r"^(.*\S)\s+(\d{4})$"),
]


def _normalize_year_markers(paragraphs: list[str]) -> list[str]:
    """Peel a year/year-range marker into its own paragraph when a page
    break merged it onto the preceding or following paragraph.

    Normally the real export puts the marker alone on its own paragraph
    (see `_paragraphs`), but observed real exports sometimes fuse it onto
    the entry title ("2017 - 2019 Soil nematodes...") or onto the end of
    the PREVIOUS entry's trailing text ("...- Bolsa. 2010 - 2014") right
    at a page boundary. A trailing marker is only peeled when it sits at
    the very end of the paragraph with nothing after it (e.g. this avoids
    misreading "Ano de Obtenção: 2019." as a marker, since that has a
    period after the year rather than being the end of the paragraph).
    """
    normalized: list[str] = []
    for paragraph in paragraphs:
        if _YEAR_MARKER_RE.match(paragraph):
            normalized.append(paragraph)
            continue
        leading = _LEADING_MARKER_SPLIT_RE.match(paragraph)
        if leading:
            normalized.append(leading.group(1))
            normalized.append(leading.group(2))
            continue
        trailing = next(
            (m for pattern in _TRAILING_MARKER_SPLIT_RES if (m := pattern.match(paragraph))), None
        )
        if trailing:
            normalized.append(trailing.group(1))
            normalized.append(trailing.group(2))
            continue
        normalized.append(paragraph)
    return normalized


def _paragraphs(section_text: str) -> list[str]:
    """Split a section's body into blank-line-separated paragraphs.

    The real Lattes PDF export (see README.lattes.md, Fase B) uses blank
    lines, not tags, to separate entries within a section -- a year/
    year-range marker alone on its own paragraph, then the entry's free
    text as the next paragraph(s). This is far more robust than matching
    a fixed single-line format, which the real export does not follow.
    """
    normalized_lines = [line if line.strip() else "" for line in section_text.splitlines()]
    raw_paragraphs = re.split(r"\n{2,}", "\n".join(normalized_lines))
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in raw_paragraphs if p.strip()]
    return _normalize_year_markers(paragraphs)


def _year_range(marker: re.Match) -> tuple[date, date | None]:
    start_year, end_token = marker.groups()
    started = date(int(start_year), 1, 1)
    finished = None if not end_token or end_token.lower() == "atual" else date(int(end_token), 1, 1)
    return started, finished


def _extract_institution(body: str) -> str:
    """Best-effort 'Name, ABBREV, Country' extraction from free-text body.

    Falls back to the raw body when the pattern isn't found -- never
    guesses an institution name that isn't literally present in the text.
    """
    match = _INSTITUTION_RE.search(body)
    return match.group(1).strip() if match else body


def _parse_education(section_text: str) -> list[Education]:
    paragraphs = _paragraphs(section_text)
    education: list[Education] = []
    i = 0
    while i < len(paragraphs):
        marker = _YEAR_MARKER_RE.match(paragraphs[i])
        if marker and i + 1 < len(paragraphs):
            started, finished = _year_range(marker)
            body = paragraphs[i + 1]
            education.append(
                Education(
                    level=_education_level_from_text(body),
                    institution=_extract_institution(body),
                    started=started,
                    finished=finished,
                )
            )
            i += 2
        else:
            i += 1
    return education


def _parse_professional_activities(section_text: str) -> list[ProfessionalActivity]:
    paragraphs = _paragraphs(section_text)
    activities: list[ProfessionalActivity] = []
    current_institution: str | None = None
    pending_period: tuple[date, date | None] | None = None

    for paragraph in paragraphs:
        normalized = _strip_accents(paragraph).lower()
        if normalized in {"vinculo institucional", "outras informacoes"}:
            continue
        marker = _YEAR_MARKER_RE.match(paragraph)
        if marker:
            pending_period = _year_range(marker)
            continue
        if normalized.startswith("vinculo:") and current_institution is not None:
            started, finished = pending_period or (date.today(), None)
            role_match = re.search(r"Enquadramento Funcional:\s*([^,]+)", paragraph)
            role = role_match.group(1).strip() if role_match else paragraph
            activities.append(
                ProfessionalActivity(
                    institution=current_institution,
                    role=role,
                    started=started,
                    finished=finished,
                )
            )
            pending_period = None
            continue
        # Anything else that looks like "Name, ABBREV, Country." starts a
        # new institution block; free-text asides (e.g. "Outras informações"
        # body) are otherwise skipped rather than misfiled as a new entry.
        if _INSTITUTION_RE.search(paragraph):
            current_institution = _extract_institution(paragraph)

    return activities


def _parse_cnpq_areas(section_text: str) -> list[str]:
    return [p for p in _paragraphs(section_text) if not _NUMBERED_ITEM_RE.match(p)]


def _parse_languages(section_text: str) -> list[LanguageSkill]:
    paragraphs = _paragraphs(section_text)
    languages: list[LanguageSkill] = []
    i = 0
    while i < len(paragraphs):
        normalized = _strip_accents(paragraphs[i]).lower()
        is_proficiency_line = normalized.startswith("compreende")
        if not is_proficiency_line and i + 1 < len(paragraphs):
            languages.append(
                LanguageSkill(language=paragraphs[i], self_reported_proficiency=paragraphs[i + 1])
            )
            i += 2
        else:
            i += 1
    return languages


def _parse_projects(section_text: str) -> list[Project]:
    paragraphs = _paragraphs(section_text)
    projects: list[Project] = []
    i = 0
    while i < len(paragraphs):
        marker = _YEAR_MARKER_RE.match(paragraphs[i])
        if marker and i + 1 < len(paragraphs):
            started, finished = _year_range(marker)
            title = paragraphs[i + 1]
            description_raw = ""
            j = i + 2
            while j < len(paragraphs) and not _YEAR_MARKER_RE.match(paragraphs[j]):
                if _strip_accents(paragraphs[j]).lower().startswith("descricao:"):
                    description_raw = paragraphs[j].split(":", 1)[1].strip()
                j += 1
            projects.append(
                Project(title=title, description_raw=description_raw, started=started, finished=finished)
            )
            i = j
        else:
            i += 1
    return projects


def _parse_publications(section_text: str) -> list[Publication]:
    """Extract publications from 'Artigos completos publicados em periódicos'.

    The real export does NOT print a DOI in this list (unlike the XML,
    which does), so `doi` is always None here -- never guessed. Title is
    kept as the full citation text rather than attempting to split author
    list / title / journal name, which is not reliably separable from
    free-flowing PDF text without risking a wrong split; the full citation
    still works fine as fit-scoring evidence in score.py's text matching.
    """
    paragraphs = _paragraphs(section_text)
    publications: list[Publication] = []
    i = 0
    while i < len(paragraphs):
        # Usually "N." is its own paragraph with the citation as the next
        # one, but sometimes (e.g. right at a page break) they land in the
        # same paragraph as "N. <citation>" -- handle both.
        merged_match = re.match(r"^\d+\.\s+(\S.*)$", paragraphs[i])
        if merged_match:
            citation = merged_match.group(1)
            i += 1
        elif _NUMBERED_ITEM_RE.match(paragraphs[i]) and i + 1 < len(paragraphs):
            citation = paragraphs[i + 1]
            i += 2
        else:
            i += 1
            continue

        # The publication year is conventionally the last year-like
        # number in the citation (volume/page numbers precede it).
        year_candidates = _YEAR_RE.findall(citation)
        year = int(year_candidates[-1]) if year_candidates else None
        doi_match = _DOI_RE.search(citation)
        publications.append(
            Publication(
                title=citation,
                year=year,
                doi=doi_match.group(0).rstrip(".,;") if doi_match else None,
                venue=None,
            )
        )
    return publications


def parse_lattes_pdf(pdf_path: str | Path) -> LattesExtract:
    """Best-effort fallback parser for a Lattes CV exported as PDF.

    LOWER RELIABILITY than parse_lattes_xml: a Lattes PDF is free-flowing
    prose with no tags, so this is paragraph/regex-heuristic-based and can
    miss or misparse entries that don't match the real export layout this
    was calibrated against (see README.lattes.md, Fase B). Callers (the
    SKILL.md flow) must surface source_format="pdf" to the user as a
    reliability caveat, same as any other unverified extraction here.
    """
    doc = pymupdf.open(str(pdf_path))
    # sort=True reconstructs reading order across the export's two-column
    # layout (a narrow identity sidebar beside the main CV body); without
    # it, lines from both columns interleave and every downstream regex
    # breaks.
    # .strip() per page avoids a page boundary accidentally introducing a
    # blank-line gap (our paragraph separator, see _paragraphs) in the
    # middle of an entry that spans two pages.
    text = "\n".join(page.get_text(sort=True).strip() for page in doc)
    doc.close()

    full_name = next((line.strip() for line in text.splitlines() if line.strip()), "")

    orcid_match = _ORCID_RE.search(text)
    orcid = orcid_match.group(0) if orcid_match else None

    last_update_match = _LAST_UPDATE_RE.search(_strip_accents(text).lower())
    last_update = _parse_br_date(last_update_match.group(1)) if last_update_match else None

    sections = _split_sections(text)

    return LattesExtract(
        full_name=full_name,
        orcid=orcid,
        last_update=last_update,
        source_format="pdf",
        education=_parse_education(sections.get("Formação acadêmica/titulação", "")),
        professional_activities=_parse_professional_activities(sections.get("Atuação Profissional", "")),
        cnpq_areas=ProvenancedList(
            values=_parse_cnpq_areas(sections.get("Áreas de atuação", "")), origin="lattes_cv"
        ),
        languages=_parse_languages(sections.get("Idiomas", "")),
        projects=_parse_projects(sections.get("Projetos de pesquisa", "")),
        publications=_parse_publications(sections.get("Artigos completos publicados em periódicos", "")),
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
