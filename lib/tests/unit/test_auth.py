"""Tests for the auth token file shared by the server and CLI."""

import os
import stat

from blackfish.server.auth import (
    generate_token,
    read_token_file,
    remove_token_file,
    token_file_path,
    write_token_file,
)


class TestGenerateToken:
    def test_tokens_are_distinct(self):
        assert generate_token() != generate_token()

    def test_token_is_url_safe(self):
        """The token goes into a `?token=` link, so it must not need escaping."""
        token = generate_token()
        assert all(c.isalnum() or c in "-_" for c in token)


class TestTokenFile:
    def test_round_trip(self, tmp_path):
        write_token_file(tmp_path, "sealsaretasty")
        assert read_token_file(tmp_path) == "sealsaretasty"

    def test_file_is_private(self, tmp_path):
        """A world-readable token on a shared cluster is the bug we're fixing."""
        write_token_file(tmp_path, "sealsaretasty")
        mode = stat.S_IMODE(os.stat(token_file_path(tmp_path)).st_mode)
        assert mode == 0o600

    def test_overwrites_existing(self, tmp_path):
        write_token_file(tmp_path, "old")
        write_token_file(tmp_path, "new")
        assert read_token_file(tmp_path) == "new"

    def test_leaves_no_temp_file(self, tmp_path):
        write_token_file(tmp_path, "sealsaretasty")
        assert list(tmp_path.iterdir()) == [token_file_path(tmp_path)]


class TestReadTokenFileNeverRaises:
    """`read_token_file` sits on the path of every CLI command."""

    def test_missing_file(self, tmp_path):
        assert read_token_file(tmp_path) is None

    def test_missing_home_dir(self, tmp_path):
        assert read_token_file(tmp_path / "nope") is None

    def test_empty_file(self, tmp_path):
        token_file_path(tmp_path).write_text("")
        assert read_token_file(tmp_path) is None

    def test_whitespace_only_file(self, tmp_path):
        token_file_path(tmp_path).write_text("\n\n")
        assert read_token_file(tmp_path) is None

    def test_directory_in_place_of_file(self, tmp_path):
        token_file_path(tmp_path).mkdir()
        assert read_token_file(tmp_path) is None

    def test_trailing_newline_is_stripped(self, tmp_path):
        token_file_path(tmp_path).write_text("sealsaretasty\n")
        assert read_token_file(tmp_path) == "sealsaretasty"


class TestRemoveTokenFile:
    def test_removes(self, tmp_path):
        write_token_file(tmp_path, "sealsaretasty")
        remove_token_file(tmp_path)
        assert not token_file_path(tmp_path).exists()

    def test_idempotent(self, tmp_path):
        remove_token_file(tmp_path)
        remove_token_file(tmp_path)
