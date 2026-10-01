import yaml

from bolsa_finder.profile import Profile, ProfileLoadError, load_profile


def test_valid_profile_dict_parses(valid_profile_dict: dict) -> None:
    profile = Profile.model_validate(valid_profile_dict)
    assert profile.target_level == "sanduiche"
    assert profile.nationality == "brazilian"
    assert len(profile.languages) == 2


def test_load_profile_from_yaml_file(tmp_path, valid_profile_dict: dict) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(valid_profile_dict), encoding="utf-8")

    profile = load_profile(path)

    assert profile.research_areas == valid_profile_dict["research_areas"]


def test_load_profile_missing_file_raises(tmp_path) -> None:
    missing = tmp_path / "does_not_exist.yaml"

    try:
        load_profile(missing)
        assert False, "expected ProfileLoadError"
    except ProfileLoadError as exc:
        assert "not found" in str(exc)


def test_load_profile_invalid_yaml_raises(tmp_path) -> None:
    path = tmp_path / "profile.yaml"
    path.write_text("research_areas: [unterminated", encoding="utf-8")

    try:
        load_profile(path)
        assert False, "expected ProfileLoadError"
    except ProfileLoadError as exc:
        assert "Invalid YAML" in str(exc)


def test_load_profile_missing_required_field_raises(tmp_path, valid_profile_dict: dict) -> None:
    incomplete = dict(valid_profile_dict)
    del incomplete["nationality"]
    path = tmp_path / "profile.yaml"
    path.write_text(yaml.safe_dump(incomplete), encoding="utf-8")

    try:
        load_profile(path)
        assert False, "expected ProfileLoadError"
    except ProfileLoadError as exc:
        assert "nationality" in str(exc)


def test_empty_research_areas_rejected(valid_profile_dict: dict) -> None:
    invalid = dict(valid_profile_dict)
    invalid["research_areas"] = []

    try:
        Profile.model_validate(invalid)
        assert False, "expected validation error"
    except Exception as exc:
        assert "research_areas" in str(exc)


def test_blank_research_area_rejected(valid_profile_dict: dict) -> None:
    # A blank entry would silently match every publication's title/topics
    # as a substring in score.py, fabricating fit evidence out of nothing.
    invalid = dict(valid_profile_dict)
    invalid["research_areas"] = [""]

    try:
        Profile.model_validate(invalid)
        assert False, "expected validation error"
    except Exception as exc:
        assert "research_areas" in str(exc)


def test_whitespace_only_method_rejected(valid_profile_dict: dict) -> None:
    invalid = dict(valid_profile_dict)
    invalid["methods"] = ["   "]

    try:
        Profile.model_validate(invalid)
        assert False, "expected validation error"
    except Exception as exc:
        assert "methods" in str(exc)


def test_expected_defense_before_program_started_rejected(valid_profile_dict: dict) -> None:
    invalid = dict(valid_profile_dict)
    invalid["academic_stage"] = {
        "program_started": "2022-03-01",
        "expected_defense": "2020-01-01",
    }

    try:
        Profile.model_validate(invalid)
        assert False, "expected validation error"
    except Exception as exc:
        assert "expected_defense" in str(exc)


def test_time_window_latest_before_earliest_rejected(valid_profile_dict: dict) -> None:
    invalid = dict(valid_profile_dict)
    invalid["time_window"] = {
        "earliest_start": "2027-01-01",
        "latest_start": "2026-01-01",
    }

    try:
        Profile.model_validate(invalid)
        assert False, "expected validation error"
    except Exception as exc:
        assert "latest_start" in str(exc)
