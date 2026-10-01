from datetime import date

from bolsa_finder.openalex import Publication
from bolsa_finder.profile import Profile
from bolsa_finder.score import Researcher, score_researcher_fit


def _publication(**overrides) -> Publication:
    defaults = dict(
        id="https://openalex.org/W1",
        title="A study of soil microbiome dynamics",
        year=2025,
        url="https://doi.org/10.1/x",
        topics=["Microbiome and host interactions"],
    )
    defaults.update(overrides)
    return Publication(**defaults)


def test_topic_overlap_scores_higher_than_no_match(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)

    matching_researcher = Researcher(
        id="A1",
        display_name="Dr. Match",
        institution_name="Some University",
        confidence="high",
        publications=[_publication(topics=["bioinformatics"])],
    )
    non_matching_researcher = Researcher(
        id="A2",
        display_name="Dr. NoMatch",
        institution_name="Some University",
        confidence="high",
        publications=[_publication(title="unrelated particle physics paper", topics=["Particle physics"])],
    )

    matching_fit = score_researcher_fit(profile, matching_researcher, as_of=date(2026, 1, 1))
    non_matching_fit = score_researcher_fit(profile, non_matching_researcher, as_of=date(2026, 1, 1))

    assert matching_fit.score > non_matching_fit.score
    assert non_matching_fit.score == 0.0
    assert any("bioinformatics" in e for e in matching_fit.evidence)


def test_title_match_scores_lower_than_topic_match(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)

    topic_match = Researcher(
        id="A1",
        display_name="Dr. Topic",
        institution_name="U",
        confidence="high",
        publications=[_publication(title="neutral title", topics=["bioinformatics"])],
    )
    title_match = Researcher(
        id="A2",
        display_name="Dr. Title",
        institution_name="U",
        confidence="high",
        publications=[_publication(title="A paper mentioning bioinformatics in passing", topics=["Unrelated"])],
    )

    topic_fit = score_researcher_fit(profile, topic_match, as_of=date(2026, 1, 1))
    title_fit = score_researcher_fit(profile, title_match, as_of=date(2026, 1, 1))

    assert topic_fit.score > title_fit.score
    assert title_fit.score > 0.0


def test_recent_publication_scores_higher_than_old_one(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)

    recent = Researcher(
        id="A1",
        display_name="Dr. Recent",
        institution_name="U",
        confidence="high",
        publications=[_publication(year=2026, topics=["bioinformatics"])],
    )
    old = Researcher(
        id="A2",
        display_name="Dr. Old",
        institution_name="U",
        confidence="high",
        publications=[_publication(year=2015, topics=["bioinformatics"])],
    )

    recent_fit = score_researcher_fit(profile, recent, as_of=date(2026, 1, 1))
    old_fit = score_researcher_fit(profile, old, as_of=date(2026, 1, 1))

    assert recent_fit.score > old_fit.score


def test_word_overlap_catches_differently_phrased_topic(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)
    researcher = Researcher(
        id="A1",
        display_name="Dr. Word",
        institution_name="U",
        confidence="high",
        publications=[
            _publication(
                title="Neutral title",
                topics=["Microbiome-adjacent community dynamics"],
            )
        ],
    )

    fit = score_researcher_fit(profile, researcher, as_of=date(2026, 1, 1))

    assert fit.score > 0.0
    assert any("word overlap" in e.lower() for e in fit.evidence)


def test_generic_short_words_are_not_used_for_matching(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)
    researcher = Researcher(
        id="A1",
        display_name="Dr. Generic",
        institution_name="U",
        confidence="high",
        publications=[
            _publication(title="Some unrelated data analysis paper", topics=["General applied research"])
        ],
    )

    fit = score_researcher_fit(profile, researcher, as_of=date(2026, 1, 1))

    assert fit.score == 0.0


def test_low_confidence_adds_disambiguation_pending_check(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)
    researcher = Researcher(
        id="A1",
        display_name="Dr. Common Name",
        institution_name="U",
        confidence="low",
        publications=[],
    )

    fit = score_researcher_fit(profile, researcher, as_of=date(2026, 1, 1))

    assert any("disambiguation" in check.lower() for check in fit.pending_checks)


def test_pending_checks_always_flag_grants_and_recruiting_as_unverifiable(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)
    researcher = Researcher(
        id="A1", display_name="Dr. X", institution_name="U", confidence="high", publications=[]
    )

    fit = score_researcher_fit(profile, researcher, as_of=date(2026, 1, 1))

    joined = " ".join(fit.pending_checks).lower()
    assert "grant" in joined
    assert "recruiting" in joined
