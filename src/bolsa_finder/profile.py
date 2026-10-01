"""Candidate profile schema and loader.

The profile is the single source of truth for everything downstream
(funding search, OpenAlex queries, fit scoring) so it is validated
strictly and fails loudly rather than silently defaulting fields.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, Field, StringConstraints, ValidationError

# "pleno" = doutorado pleno no exterior (the whole PhD program abroad),
# distinct from "sanduiche" (a period abroad with the PhD based in Brazil)
# and from "doutorado" (PhD based in Brazil, no funded period abroad).
TargetLevel = Literal["mestrado", "doutorado", "sanduiche", "pleno", "posdoc"]

TARGET_LEVEL_DESCRIPTIONS: dict[TargetLevel, str] = {
    "mestrado": "Mestrado",
    "doutorado": "Doutorado (no Brasil, sem período financiado no exterior)",
    "sanduiche": "Doutorado-sanduíche (período no exterior, doutorado principal no Brasil)",
    "pleno": "Doutorado pleno no exterior (programa inteiro cursado fora do Brasil)",
    "posdoc": "Pós-doutorado",
}

ProficiencyLevel = Literal["basico", "intermediario", "avancado", "fluente", "nativo"]

# A blank/whitespace-only string here would silently match every publication
# in score.py's substring overlap check (an empty string is "in" any text),
# fabricating fit evidence out of nothing -- so these lists require
# non-empty, non-whitespace entries.
NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strip_whitespace=True)]


class LanguageProficiency(BaseModel):
    language: NonEmptyStr
    proficiency: ProficiencyLevel


class AcademicStage(BaseModel):
    """Where the candidate currently stands in their program."""

    program_started: date
    expected_defense: date | None = None

    def model_post_init(self, __context: object) -> None:
        if self.expected_defense is not None and self.expected_defense < self.program_started:
            raise ValueError("expected_defense cannot be before program_started")


class TimeWindow(BaseModel):
    """The period during which the candidate wants to start the target position."""

    earliest_start: date
    latest_start: date | None = None

    def model_post_init(self, __context: object) -> None:
        if self.latest_start is not None and self.latest_start < self.earliest_start:
            raise ValueError("latest_start cannot be before earliest_start")


class Profile(BaseModel):
    research_areas: list[NonEmptyStr] = Field(min_length=1)
    methods: list[NonEmptyStr] = Field(min_length=1)
    cv_summary: NonEmptyStr
    academic_stage: AcademicStage
    target_level: TargetLevel
    languages: list[LanguageProficiency] = Field(min_length=1)
    nationality: NonEmptyStr
    geographic_restrictions: list[NonEmptyStr] = Field(default_factory=list)
    funding_required: bool
    time_window: TimeWindow


class ProfileLoadError(Exception):
    """Raised when profile.yaml is missing, malformed, or fails validation."""


def load_profile(path: str | Path) -> Profile:
    """Load and validate a profile.yaml file, raising ProfileLoadError on any failure."""
    profile_path = Path(path)
    if not profile_path.exists():
        raise ProfileLoadError(f"Profile file not found: {profile_path}")

    try:
        raw = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ProfileLoadError(f"Invalid YAML in {profile_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ProfileLoadError(f"Profile file must contain a mapping at the top level: {profile_path}")

    try:
        return Profile.model_validate(raw)
    except ValidationError as exc:
        raise ProfileLoadError(f"Profile validation failed for {profile_path}:\n{exc}") from exc
