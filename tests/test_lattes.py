from datetime import date
from pathlib import Path

import pymupdf

from bolsa_finder.lattes import (
    LattesExtract,
    ProvenancedList,
    check_staleness,
    merge_into_profile,
    parse_lattes_pdf,
    parse_lattes_xml,
)
from bolsa_finder.profile import AcademicStage, LanguageProficiency, TimeWindow

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "lattes_sample.xml"


def _build_synthetic_lattes_pdf(path: Path, lines: list[str]) -> None:
    """Write a minimal PDF with one line of text per line, for testing
    parse_lattes_pdf's regex/section heuristics without a real Lattes PDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in lines:
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
    pdf_path = tmp_path / "lattes.pdf"
    _build_synthetic_lattes_pdf(
        pdf_path,
        [
            "Fulana de Tal",
            "ORCID: 0000-0000-0000-0001",
            "Ultima atualizacao do curriculo em 15/01/2026",
            "Formacao academica/titulacao",
            "2022 - Atual Doutorado em Estatistica, Universidade Ficticia PDF",
            "Areas de atuacao",
            "Estatistica Aplicada",
            "Bioinformatica",
            "Idiomas",
            "Ingles Compreende Bem, Fala Bem.",
            "Projetos de pesquisa",
            "2023 - Atual Microbioma e estatistica ambiental PDF",
            "Analise de dados de NGS via PDF.",
            "Producao bibliografica",
            "Um estudo de caso em microbioma PDF 2025 10.1234/fake.pdf.doi",
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

    assert set(extract.cnpq_areas.values) == {"Estatistica Aplicada", "Bioinformatica"}

    assert len(extract.languages) == 1
    assert extract.languages[0].language == "Ingles"

    assert len(extract.projects) == 1
    assert "Microbioma" in extract.projects[0].title
    assert "NGS" in extract.projects[0].description_raw

    assert len(extract.publications) == 1
    assert extract.publications[0].doi == "10.1234/fake.pdf.doi"
    assert extract.publications[0].year == 2025


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
