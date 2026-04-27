import logging

from blackfish.cli.__main__ import _warn_if_no_profiles


def test_warn_if_no_profiles_emits_when_cfg_missing(tmp_path, caplog):
    with caplog.at_level(logging.WARNING, logger="blackfish"):
        _warn_if_no_profiles(str(tmp_path))

    assert any("No profiles configured" in r.message for r in caplog.records)


def test_warn_if_no_profiles_emits_when_cfg_empty(tmp_path, caplog):
    (tmp_path / "profiles.cfg").write_text("")

    with caplog.at_level(logging.WARNING, logger="blackfish"):
        _warn_if_no_profiles(str(tmp_path))

    assert any("No profiles configured" in r.message for r in caplog.records)


def test_warn_if_no_profiles_silent_when_profile_exists(tmp_path, caplog):
    (tmp_path / "profiles.cfg").write_text(
        "[default]\nschema = local\nhome_dir = /tmp\ncache_dir = /tmp\n"
    )

    with caplog.at_level(logging.WARNING, logger="blackfish"):
        _warn_if_no_profiles(str(tmp_path))

    assert not any("No profiles configured" in r.message for r in caplog.records)
