"""The logger must not break a fresh install.

`logger.py` attaches a `FileHandler` on `$HOME_DIR/logs` at import time, but
only outside debug mode. `bootstrap()` creates that directory and cannot run
first — importing `blackfish` at all pulls in the logger — so with
authentication on by default, an eager handler made every command, `init`
included, fail on a machine that had never run Blackfish.
"""

import os
import subprocess
import sys


def _run(code: str, home_dir, debug: str):
    env = {**os.environ, "BLACKFISH_HOME_DIR": str(home_dir), "BLACKFISH_DEBUG": debug}
    return subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )


class TestFreshInstallImport:
    """Must be subprocesses: the logger is already imported in the test process."""

    def test_import_succeeds_without_home_dir(self, tmp_path):
        res = _run("import blackfish", tmp_path / "nonexistent", "0")

        assert res.returncode == 0, res.stderr
        assert "FileNotFoundError" not in res.stderr

    def test_logging_before_bootstrap_does_not_crash_or_warn(self, tmp_path):
        """A record logged before the app dir exists is dropped, not reported.

        `logging` would otherwise print `--- Logging error ---` for every record.
        """
        res = _run(
            "from blackfish.server.logger import logger\n"
            "logger.warning('one')\n"
            "logger.warning('two')\n"
            "print('survived')",
            tmp_path / "nonexistent",
            "0",
        )

        assert res.returncode == 0, res.stderr
        assert "survived" in res.stdout
        assert "Logging error" not in res.stderr

    def test_log_file_is_private(self, tmp_path):
        """The log holds whatever the server logs, on a shared filesystem."""
        res = _run(
            "from blackfish.server.logger import logger\nlogger.warning('x')",
            tmp_path,
            "0",
        )

        assert res.returncode == 0, res.stderr
        log = tmp_path / "logs"
        assert log.exists()
        assert oct(log.stat().st_mode)[-3:] == "600"

    def test_existing_world_readable_log_is_tightened(self, tmp_path):
        """Installs that predate the 0600 creation get fixed on next start."""
        log = tmp_path / "logs"
        log.write_text("old entries\n")
        log.chmod(0o644)

        res = _run("import blackfish", tmp_path, "0")

        assert res.returncode == 0, res.stderr
        assert oct(log.stat().st_mode)[-3:] == "600"
        assert "old entries" in log.read_text()
