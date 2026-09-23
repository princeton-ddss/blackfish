"""Delegate the MkDocs build to Zensical.

`mike deploy` shells out to `mkdocs build --clean` and then commits whatever
lands in `site_dir`. Zensical has no deploy command, so this hook lets mike
drive the versioning while Zensical produces the site.
"""

import subprocess


def on_post_build(config, **kwargs):
    subprocess.run(
        ["zensical", "build", "--clean", "--config-file", "zensical.toml"],
        check=True,
    )
