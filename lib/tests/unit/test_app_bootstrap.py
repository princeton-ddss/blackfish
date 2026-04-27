"""Tests for the application-directory bootstrap module."""

import configparser
import sqlite3

import pytest

from blackfish.server.bootstrap import (
    CURRENT_VERSION,
    VERSION_FILE,
    ensure_app_dir,
    ensure_db,
    normalize_profiles_cfg,
    read_app_version,
    bootstrap,
    write_app_version,
)


def test_ensure_app_dir_creates_subdirs(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    assert (p / "models").is_dir()
    assert (p / "images").is_dir()


def test_ensure_app_dir_idempotent(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    sentinel = p / "models" / "keep.txt"
    sentinel.write_text("keep me")

    ensure_app_dir(p)

    assert sentinel.read_text() == "keep me"


def test_ensure_app_dir_missing_parent(tmp_path):
    with pytest.raises(FileNotFoundError):
        ensure_app_dir(tmp_path / "missing" / ".blackfish")


def test_ensure_app_dir_path_is_file(tmp_path):
    p = tmp_path / "not-a-dir"
    p.write_text("oops")
    with pytest.raises(NotADirectoryError):
        ensure_app_dir(p)


def test_write_and_read_app_version(tmp_path):
    write_app_version(tmp_path, "9.9.9")
    assert read_app_version(tmp_path) == "9.9.9"
    assert (tmp_path / VERSION_FILE).read_text() == "9.9.9\n"


def test_read_app_version_missing(tmp_path):
    assert read_app_version(tmp_path) is None


def test_normalize_profiles_cfg_rewrites_legacy_type(tmp_path):
    cfg = tmp_path / "profiles.cfg"
    cfg.write_text(
        "[default]\ntype = slurm\nhost = della.princeton.edu\nuser = alice\n"
    )

    normalize_profiles_cfg(tmp_path)

    parser = configparser.ConfigParser()
    parser.read(cfg)
    assert parser["default"]["schema"] == "slurm"
    assert "type" not in parser["default"]


def test_normalize_profiles_cfg_no_op_preserves_mtime(tmp_path):
    cfg = tmp_path / "profiles.cfg"
    cfg.write_text("[default]\nschema = local\nhome_dir = /tmp\n")
    mtime_before = cfg.stat().st_mtime_ns

    normalize_profiles_cfg(tmp_path)

    assert cfg.stat().st_mtime_ns == mtime_before


def test_normalize_profiles_cfg_missing_file(tmp_path):
    normalize_profiles_cfg(tmp_path)


def test_normalize_profiles_cfg_keeps_schema_when_both_present(tmp_path):
    cfg = tmp_path / "profiles.cfg"
    cfg.write_text("[default]\nschema = local\ntype = slurm\n")

    normalize_profiles_cfg(tmp_path)

    parser = configparser.ConfigParser()
    parser.read(cfg)
    assert parser["default"]["schema"] == "local"
    assert parser["default"]["type"] == "slurm"


def test_ensure_db_creates_sqlite(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    ensure_db(p)

    db_path = p / "app.sqlite"
    assert db_path.is_file()

    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "ddl_version" in tables


def test_ensure_db_idempotent(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    ensure_db(p)
    ensure_db(p)


def test_ensure_db_preserves_existing_data(tmp_path):
    p = tmp_path / ".blackfish"
    ensure_app_dir(p)
    ensure_db(p)

    db_path = p / "app.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE _smoke (id INTEGER PRIMARY KEY, payload TEXT)")
        conn.execute("INSERT INTO _smoke (id, payload) VALUES (1, 'keep me')")
        conn.commit()

    ensure_db(p)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT payload FROM _smoke WHERE id = 1").fetchone()
    assert row == ("keep me",)


def test_bootstrap_empty_dir(tmp_path):
    p = tmp_path / ".blackfish"
    bootstrap(p)

    assert (p / "models").is_dir()
    assert (p / "images").is_dir()
    assert (p / "app.sqlite").is_file()
    assert read_app_version(p) == CURRENT_VERSION


def test_bootstrap_idempotent(tmp_path):
    p = tmp_path / ".blackfish"
    bootstrap(p)
    bootstrap(p)
    assert read_app_version(p) == CURRENT_VERSION
    assert (p / "app.sqlite").is_file()


def test_bootstrap_normalizes_legacy_profiles(tmp_path):
    p = tmp_path / ".blackfish"
    p.mkdir()
    (p / "profiles.cfg").write_text(
        "[default]\ntype = local\nhome_dir = /tmp\ncache_dir = /tmp\n"
    )

    bootstrap(p)

    parser = configparser.ConfigParser()
    parser.read(p / "profiles.cfg")
    assert parser["default"]["schema"] == "local"
    assert "type" not in parser["default"]
