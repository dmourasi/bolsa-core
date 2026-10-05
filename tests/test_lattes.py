from datetime import date
from pathlib import Path

import pymupdf

from bolsa_core.lattes import (
    LattesExtract,
    ProvenancedList,
    _paragraphs,
    _split_sections,
    check_staleness,
    merge_into_profile,
    parse_lattes_pdf,
    parse_lattes_xml,
)
from bolsa_core.profile import AcademicStage, LanguageProficiency, TimeWindow

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lattes_sample.xml"


def _build_synthetic_lattes_pdf(path: Path, lines: list[str]) -> None:
    """Write a minimal PDF with one line of text per line, for testing
    parse_lattes_pdf's regex/section heuristics without a real Lattes PDF.

    An empty string in `lines` renders as a paragraph break: the real
    Lattes PDF export separates entries within a section with a blank
    line (see README.lattes.md, Fase B), which pymupdf only reconstructs
    as a blank line in extracted text when there is a large enough
    vertical gap between text blocks.
    """
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        if line == "":
            y += 20
            continue
        page.insert_text((72, y), line)
        y += 14
    doc.save(str(path))
    doc.close()


def test_parse_lattes_xml_extracts_structured_fields() -> None:
    extract = parse_lattes_xml(FIXTURE_PATH)

    assert extract.full_name == "Fulana de Tal"
    assert extract.orcid == "0000-0000-0000-0000"
    assert extract.last_update == date(2026, 1, 15)
    assert extract.source_format == "xml"

    assert len(extract.education) == 1
    assert extract.education[0].level == "doutorado"
    assert extract.education[0].institution == "Universidade Ficticia"
    assert extract.education[0].started == date(2022, 1, 1)
    assert extract.education[0].finished is None

    assert set(extract.cnpq_areas.values) == {"Estatistica Aplicada", "Bioinformatica"}
    assert extract.cnpq_areas.origin == "lattes_cv"

    assert len(extract.languages) == 1
    assert extract.languages[0].language == "Ingles"

    assert len(extract.projects) == 1
    assert "Microbioma" in extract.projects[0].title
    assert "modelos mistos" in extract.projects[0].description_raw

    assert len(extract.publications) == 1
    assert extract.publications[0].doi == "10.1234/fake.doi"
    assert extract.publications[0].year == 2025


def test_parse_lattes_xml_never_leaks_pii() -> None:
    extract = parse_lattes_xml(FIXTURE_PATH)
    dumped = extract.model_dump_json()

    # Fake PII present in the source fixture that must never reach the model.
    for leaked in [
        "000.000.000-00",  # CPF
        "0000000",  # RG
        "01011995",  # DATA-NASCIMENTO
        "Rua Ficticia",  # ENDERECO
        "(00) 00000-0000",  # TELEFONE
    ]:
        assert leaked not in dumped, f"PII leaked into LattesExtract: {leaked!r}"


def test_check_staleness_none_when_recently_updated() -> None:
    extract = LattesExtract(
        full_name="X",
        last_update=date(2026, 1, 1),
        source_format="xml",
    )

    assert check_staleness(extract, as_of=date(2026, 2, 1)) is None


def test_check_staleness_warns_when_older_than_six_months() -> None:
    extract = LattesExtract(
        full_name="X",
        last_update=date(2025, 1, 1),
        source_format="xml",
    )

    warning = check_staleness(extract, as_of=date(2026, 1, 1))

    assert warning is not None
    assert "2025-01-01" in warning


def test_check_staleness_warns_when_last_update_missing() -> None:
    extract = LattesExtract(full_name="X", last_update=None, source_format="xml")

    warning = check_staleness(extract, as_of=date(2026, 1, 1))

    assert warning is not None
    assert "não encontrada" in warning


def test_merge_into_profile_uses_explicit_fields_never_inferred_from_lattes() -> None:
    extract = parse_lattes_xml(FIXTURE_PATH)

    profile = merge_into_profile(
        extract,
        research_areas=["applied statistics", "bioinformatics"],
        methods=["mixed models", "NGS data analysis"],
        target_level="sanduiche",
        academic_stage=AcademicStage(program_started=date(2022, 1, 1), expected_defense=date(2027, 1, 1)),
        languages=[LanguageProficiency(language="english", proficiency="avancado")],
        nationality="brazilian",
        funding_required=True,
        time_window=TimeWindow(earliest_start=date(2026, 6, 1)),
    )

    assert profile.nationality == "brazilian"
    assert profile.target_level == "sanduiche"
    assert profile.academic_stage.expected_defense == date(2027, 1, 1)
    assert profile.research_areas == ["applied statistics", "bioinformatics"]
    assert "Universidade Ficticia" in profile.cv_summary


def test_merge_into_profile_custom_cv_summary_overrides_default() -> None:
    extract = parse_lattes_xml(FIXTURE_PATH)

    profile = merge_into_profile(
        extract,
        research_areas=["applied statistics"],
        methods=["mixed models"],
        target_level="posdoc",
        academic_stage=AcademicStage(program_started=date(2022, 1, 1)),
        languages=[LanguageProficiency(language="english", proficiency="avancado")],
        nationality="brazilian",
        funding_required=False,
        time_window=TimeWindow(earliest_start=date(2026, 6, 1)),
        cv_summary="Custom summary text.",
    )

    assert profile.cv_summary == "Custom summary text."


def test_parse_lattes_pdf_best_effort_extraction(tmp_path: Path) -> None:
    # This mirrors the real Lattes PDF export structure found during Fase B
    # (see README.lattes.md): entries are blank-line-separated paragraphs,
    # not single lines -- a bare year/year-range marker, then the entry's
    # free text as the next paragraph(s); numbered items ("1.") similarly
    # sit in their own paragraph before their content.
    pdf_path = tmp_path / "lattes.pdf"
    _build_synthetic_lattes_pdf(
        pdf_path,
        [
            "Fulana de Tal",
            "ORCID: 0000-0000-0000-0001",
            "Ultima atualizacao do curriculo em 15/01/2026",
            "",
            "Formacao academica/titulacao",
            "",
            "2022 - Atual",
            "",
            "Doutorado em Estatistica, Universidade Ficticia PDF",
            "",
            "Areas de atuacao",
            "",
            "1.",
            "",
            "Grande area: Ciencias Exatas / Area: Estatistica Aplicada.",
            "",
            "2.",
            "",
            "Grande area: Ciencias Biologicas / Area: Bioinformatica.",
            "",
            "Idiomas",
            "",
            "Ingles",
            "",
            "Compreende Bem, Fala Bem.",
            "",
            "Projetos de pesquisa",
            "",
            "2023 - Atual",
            "",
            "Microbioma e estatistica ambiental PDF",
            "",
            "Descricao: Analise de dados de NGS via PDF.",
            "",
            "Artigos completos publicados em periodicos",
            "",
            "1.",
            "",
            "Um estudo de caso em microbioma PDF, v. 1, p. 1, 2025. 10.1234/fake.pdf.doi",
        ],
    )

    extract = parse_lattes_pdf(pdf_path)

    assert extract.full_name == "Fulana de Tal"
    assert extract.source_format == "pdf"
    assert extract.orcid == "0000-0000-0000-0001"
    assert extract.last_update == date(2026, 1, 15)

    assert len(extract.education) == 1
    assert extract.education[0].level == "doutorado"
    assert extract.education[0].started == date(2022, 1, 1)
    assert extract.education[0].finished is None

    assert set(extract.cnpq_areas.values) == {
        "Grande area: Ciencias Exatas / Area: Estatistica Aplicada.",
        "Grande area: Ciencias Biologicas / Area: Bioinformatica.",
    }

    assert len(extract.languages) == 1
    assert extract.languages[0].language == "Ingles"
    assert "Compreende Bem" in extract.languages[0].self_reported_proficiency

    assert len(extract.projects) == 1
    assert "Microbioma" in extract.projects[0].title
    assert "NGS" in extract.projects[0].description_raw
    assert extract.projects[0].started == date(2023, 1, 1)
    assert extract.projects[0].finished is None

    assert len(extract.publications) == 1
    assert extract.publications[0].doi == "10.1234/fake.pdf.doi"
    assert extract.publications[0].year == 2025


def test_split_sections_keeps_first_occurrence_when_header_repeats() -> None:
    # Observed in a real Lattes PDF export: a section header can reappear
    # verbatim later in the document for an unrelated, shorter listing.
    # The first (complete) occurrence must win, not the second.
    text = (
        "Projetos de pesquisa\n"
        "first entry content\n"
        "\n"
        "Idiomas\n"
        "Ingles\n"
        "\n"
        "Projetos de pesquisa\n"
        "second unrelated short blurb\n"
    )

    sections = _split_sections(text)

    assert sections["Projetos de pesquisa"].strip() == "first entry content"
    assert sections["Idiomas"].strip() == "Ingles"


def test_paragraphs_splits_marker_merged_onto_start_of_next_paragraph() -> None:
    # "2017 - 2019 Project Title" instead of the marker on its own line
    # (observed at a PDF page break).
    text = "2017 - 2019 Project Title\n\nDescricao: something."

    paragraphs = _paragraphs(text)

    assert paragraphs[0] == "2017 - 2019"
    assert paragraphs[1] == "Project Title"


def test_paragraphs_splits_marker_merged_onto_end_of_previous_paragraph() -> None:
    # "...- Bolsa. 2010 - 2014" instead of the marker on its own line
    # (observed at a PDF page break) -- the full range must be kept
    # together, not split as "...2010 -" + "2014".
    text = "Financiador: Agencia X - Bolsa. 2010 - 2014\n\nNext Title"

    paragraphs = _paragraphs(text)

    assert paragraphs[0] == "Financiador: Agencia X - Bolsa."
    assert paragraphs[1] == "2010 - 2014"


def test_paragraphs_does_not_split_an_inline_year_reference() -> None:
    # "Ano de Obtenção: 2019." has a trailing period right after the year,
    # unlike a genuine merged marker -- must NOT be treated as one.
    text = "Titulo: Something. Ano de Obtencao: 2019.\n\nNext paragraph."

    paragraphs = _paragraphs(text)

    assert paragraphs[0] == "Titulo: Something. Ano de Obtencao: 2019."


def test_parse_lattes_pdf_never_leaks_pii_even_if_present(tmp_path: Path) -> None:
    pdf_path = tmp_path / "lattes.pdf"
    _build_synthetic_lattes_pdf(
        pdf_path,
        [
            "Fulana de Tal",
            "CPF: 000.000.000-00",
            "Endereco: Rua Ficticia, 123",
            "Telefone: (00) 00000-0000",
        ],
    )

    extract = parse_lattes_pdf(pdf_path)
    dumped = extract.model_dump_json()

    for leaked in ["000.000.000-00", "Rua Ficticia", "(00) 00000-0000"]:
        assert leaked not in dumped, f"PII leaked into LattesExtract from PDF: {leaked!r}"


def test_provenanced_list_tracks_origin_for_llm_inferred_fields() -> None:
    inferred = ProvenancedList(values=["microbiome amplicon analysis"], origin="llm_inferred")

    assert inferred.origin == "llm_inferred"
    assert inferred.values == ["microbiome amplicon analysis"]
