"""Shared fixtures.

The reference candidate used across tests and the end-to-end check: a Brazilian
PhD candidate in applied statistics/bioinformatics seeking a sandwich or
postdoc position in microbiome/NGS and environmental statistics.
"""

import pytest


@pytest.fixture
def valid_profile_dict() -> dict:
    return {
        "research_areas": ["applied statistics", "bioinformatics", "environmental statistics"],
        "methods": ["mixed models", "NGS data analysis", "microbiome amplicon analysis"],
        "cv_summary": (
            "PhD candidate in Statistics at UFRPE, working on applied statistical "
            "methods for microbiome and environmental data."
        ),
        "academic_stage": {
            "program_started": "2022-03-01",
            "expected_defense": "2027-02-28",
        },
        "target_level": "sanduiche",
        "languages": [
            {"language": "portuguese", "proficiency": "nativo"},
            {"language": "english", "proficiency": "avancado"},
        ],
        "nationality": "brazilian",
        "geographic_restrictions": [],
        "funding_required": True,
        "time_window": {
            "earliest_start": "2026-06-01",
            "latest_start": "2027-01-01",
        },
    }
