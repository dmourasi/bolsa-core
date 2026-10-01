# Schemas (pydantic contract)

Source of truth is the code; this is a map so you don't have to open
every file. All models validate strictly (`pydantic` v2) and raise on
unexpected/missing fields -- that is intentional, not a bug to work
around.

## `bolsa_finder.profile.Profile`

| field | type | notes |
|---|---|---|
| `research_areas` | `list[str]`, min 1 | free text, used as OpenAlex topic search queries and as fit-score terms |
| `methods` | `list[str]`, min 1 | free text, same dual use as above |
| `cv_summary` | `str` | short text, not a full CV |
| `academic_stage` | `AcademicStage` | `program_started: date`, `expected_defense: date \| None` (must be >= program_started) |
| `target_level` | `"doutorado" \| "sanduiche" \| "posdoc"` | |
| `languages` | `list[LanguageProficiency]`, min 1 | `{language, proficiency}`, proficiency one of `basico\|intermediario\|avancado\|fluente\|nativo` |
| `nationality` | `str` | |
| `geographic_restrictions` | `list[str]`, default `[]` | free text, e.g. countries to avoid |
| `funding_required` | `bool` | |
| `time_window` | `TimeWindow` | `earliest_start: date`, `latest_start: date \| None` (must be >= earliest_start) |

Load with `bolsa_finder.profile.load_profile(path)` -- raises
`ProfileLoadError` with an explicit message on missing file, invalid
YAML, or failed validation. Never catch and silently default.

## `bolsa_finder.funding.FundingOpportunity`

| field | type | notes |
|---|---|---|
| `name`, `agency`, `country_or_region` | `str` | |
| `target_levels` | `list[str]` | free text, agency's own wording |
| `amount` | `str \| "unknown"` | literal string `"unknown"` when not stated by the source |
| `deadline` | `str \| "unknown"` | same; many editais have per-institution deadlines, so this is often legitimately `"unknown"` at the program level |
| `url` | `str` | the exact page/document consulted |
| `consulted_at` | `date` | when the page was fetched -- always set, never backdated |
| `eligibility_brazilian` | `"confirmed" \| "likely" \| "unverified" \| "unknown"` | see `references/elegibilidade.md` for how to assign this |
| `eligibility_evidence` | `str \| None` | verbatim excerpt that justifies the level above; `None` only when level is `"unverified"`/`"unknown"` |

## `bolsa_finder.lattes`

- `LattesExtract`: `full_name, orcid: str | None, last_update: date | None, source_format: "xml"|"pdf", education: list[Education], professional_activities: list[ProfessionalActivity], cnpq_areas: ProvenancedList, languages: list[LanguageSkill], projects: list[Project], publications: list[Publication], methods_inferred: ProvenancedList | None`.
  No field for CPF/RG/endereço/telefone/data de nascimento exists -- not filtered, structurally absent.
- `ProvenancedList`: `values: list[str], origin: "lattes_cv"|"llm_inferred"|"user_confirmed"`. `methods_inferred`/`research_areas` candidates proposed by reading `projects[].description_raw` are `"llm_inferred"` and must be confirmed by the user before use.
- `parse_lattes_xml(path) -> LattesExtract` -- PROVISIONAL, built from the publicly documented CNPq schema, not yet validated against a real export (see `README.lattes.md`).
- `parse_lattes_pdf(path) -> LattesExtract` -- best-effort regex/section-heuristic fallback, lower reliability than XML; always has `source_format="pdf"`.
- `check_staleness(extract, as_of=None) -> str | None` -- warns if `last_update` is >~6 months old, or missing.
- `merge_into_profile(extract, *, research_areas, methods, target_level, academic_stage, languages, nationality, funding_required, time_window, geographic_restrictions=None, cv_summary=None) -> Profile` -- the only path from a Lattes extract to a usable `Profile`; everything not derivable from Lattes is a required explicit argument.

## `bolsa_finder.openalex` hit types

- `Topic`: `id, display_name, works_count`
- `InstitutionHit`: `id, display_name, recent_works_count` (recent = since the `since_year` passed to the query)
- `AuthorHit`: `id, display_name, recent_works_count`
- `Publication`: `id, title, year, url, topics: list[str]` -- used as fit evidence, never scored by venue/journal prestige
- `OpenAlexClient.find_author_by_orcid(orcid) -> AuthorHit | None` -- direct, treat as high-confidence identity match
- `OpenAlexClient.find_author_by_dois(dois) -> tuple[AuthorHit, "medium"|"low"] | None` -- fallback when no ORCID; confidence reflects how much of the given DOI list matched one author, never upgrade it

## `bolsa_finder.score`

- `Researcher`: `id, display_name, institution_name, confidence: "high"|"medium"|"low", publications: list[Publication]`.
  `confidence` reflects how sure you are this OpenAlex author ID is the
  right person (see `references/elegibilidade.md`'s sibling concern:
  author disambiguation, not eligibility, but same "say when unsure" rule).
- `FitScore`: `researcher_id, researcher_name, institution_name, score: float, evidence: list[str], pending_checks: list[str]`.
  `evidence` entries are human-readable and each cites a specific
  publication + URL; `pending_checks` always lists what OpenAlex cannot
  confirm (active grants, recruiting status), plus a disambiguation
  warning when `confidence != "high"`.

## `bolsa_finder.report.Report`

`generated_at: date, funding_opportunities: list[FundingOpportunity], fit_scores: list[FitScore]` (sorted by score descending), `disclaimer: str` (fixed text reminding to reconfirm against the official edital).
