from fnmatch import fnmatch
import os
import socket
from typing import Optional
from huggingface_hub import ModelCard, list_repo_commits
from huggingface_hub.errors import RepositoryNotFoundError
from fabric.connection import Connection
from app.models.profile import BlackfishProfile, SlurmRemote, LocalProfile
from app.logger import logger
from yaspin import yaspin
from log_symbols.symbols import LogSymbols


def get_latest_commit(repo_id: str, revisions: list[str]) -> str:  # pragma: no cover
    """Return the most recent revision for a model from a list of options."""
    if len(revisions) == 0:
        raise Exception("List of revisions should be non-empty.")
    commits = map(lambda x: x.commit_id, list_repo_commits(repo_id))
    for commit in commits:
        if commit in revisions:
            return revisions[revisions.index(commit)]
    raise Exception("List of revisions should be a (non-empty) subset of repo commits.")


def get_models(profile: BlackfishProfile) -> list[str]:
    """Return a list of models available to a given profile."""
    if isinstance(profile, SlurmRemote):
        models = set()
        with yaspin(text=f"Searching {profile.host} for available models") as spinner:
            with Connection(profile.host, profile.user) as conn, conn.sftp() as sftp:
                default_dir = os.path.join(profile.cache_dir, "models")
                spinner.text = f"Looking in cache directory {default_dir}"
                model_dirs = sftp.listdir(default_dir)
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    models.add(f"{namespace}/{model}")
                backup_dir = os.path.join(profile.home_dir, "models")
                spinner.text = f"Looking in home directory {backup_dir}"
                model_dirs = sftp.listdir(backup_dir)
                for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    _, namespace, model = model_dir.split("--")
                    models.add(f"{namespace}/{model}")
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(models)} models.")
        return list(models)
    elif isinstance(profile, LocalProfile):
        models = set()
        with yaspin(text="Searching localhost for available models") as spinner:
            default_dir = os.path.join(profile.cache_dir, "models")
            spinner.text = f"Looking in cache directory {default_dir}"
            model_dirs = os.listdir(default_dir)
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                models.add(f"{namespace}/{model}")
            backup_dir = os.path.join(profile.home_dir, "models")
            spinner.text = f"Looking in home directory {backup_dir}"
            model_dirs = os.listdir(backup_dir)
            for model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                _, namespace, model = model_dir.split("--")
                models.add(f"{namespace}/{model}")
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(models)} models.")
        return list(models)
    else:
        raise NotImplementedError


def get_revisions(repo_id: str, profile: BlackfishProfile) -> list[str]:
    """Return a list of revisions associated with a given model and profile."""
    if isinstance(profile, SlurmRemote):
        revisions = set()
        namespace, model = repo_id.split("/")
        model_dir = f"models--{namespace}--{model}"
        with yaspin(
            text=f"Searching {profile.host} for model {repo_id} commits"
        ) as spinner:
            with Connection(profile.host, profile.user) as conn, conn.sftp() as sftp:
                default_dir = os.path.join(profile.cache_dir, "models")
                spinner.text = f"Looking in cache directory {default_dir}"
                model_dirs = sftp.listdir(default_dir)
                if model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    revisions.update(
                        sftp.listdir(os.path.join(default_dir, model_dir, "snapshots"))
                    )
                backup_dir = os.path.join(profile.home_dir, "models")
                spinner.text = f"Looking in home directory {backup_dir}"
                model_dirs = sftp.listdir(backup_dir)
                if model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                    revisions.update(
                        sftp.listdir(os.path.join(backup_dir, model_dir, "snapshots"))
                    )
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(revisions)} snapshots.")
        return list(revisions)
    elif isinstance(profile, LocalProfile):
        revisions = set()
        namespace, model = repo_id.split("/")
        model_dir = f"models--{namespace}--{model}"
        with yaspin(text=f"Searching localhost for model {repo_id} commits") as spinner:
            default_dir = os.path.join(profile.cache_dir, "models")
            spinner.text = f"Looking in cache directory {default_dir}"
            model_dirs = os.listdir(default_dir)
            if model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                revisions.update(
                    os.listdir(os.path.join(default_dir, model_dir, "snapshots"))
                )
            backup_dir = os.path.join(profile.home_dir, "models")
            spinner.text = f"Looking in home directory {backup_dir}"
            model_dirs = os.listdir(backup_dir)
            if model_dir in filter(lambda x: x.startswith("models--"), model_dirs):
                revisions.update(
                    os.listdir(os.path.join(backup_dir, model_dir, "snapshots"))
                )
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(revisions)} snapshots.")
        return list(revisions)
    else:
        raise NotImplementedError


def get_model_dir(
    repo_id: str, revision: str, profile: BlackfishProfile
) -> Optional[str]:
    """Find the directory of a specific model revision.

    The job launcher needs to know where to find model files, but these can be split across the managed cache and a user's private cache.
    """
    namespace, model = repo_id.split("/")
    model_dir = f"models--{namespace}--{model}"
    if isinstance(profile, SlurmRemote):
        with yaspin(
            text=f"Searching {profile.host} for {repo_id}[{revision}]"
        ) as spinner:
            with Connection(profile.host, profile.user) as conn, conn.sftp() as sftp:
                default_dir = os.path.join(profile.cache_dir, "models")
                spinner.text = f"Looking in default directory {default_dir}"
                if model_dir in sftp.listdir(default_dir):
                    if revision in sftp.listdir(
                        os.path.join(default_dir, model_dir, "snapshots")
                    ):
                        spinner.text = ""
                        spinner.ok(
                            f"{LogSymbols.SUCCESS.value} Found model"
                            f" {repo_id}[{revision}] in {default_dir}."
                        )
                        return os.path.join(default_dir, model_dir)
                backup_dir = os.path.join(profile.home_dir, "models")
                spinner.text = f"Looking in backup directory {backup_dir}"
                if model_dir in sftp.listdir(backup_dir):
                    if revision in sftp.listdir(
                        os.path.join(backup_dir, model_dir, "snapshots")
                    ):
                        spinner.text = ""
                        spinner.ok(
                            f"{LogSymbols.SUCCESS.value} Found model"
                            f" {repo_id}[{revision}] in {backup_dir}."
                        )
                        return os.path.join(backup_dir, model_dir)
            spinner.text = ""
            spinner.fail(
                f"{LogSymbols.ERROR.value} Unable to find {repo_id}[{revision}] on"
                f" {profile.host}."
            )
        return None
    if isinstance(profile, LocalProfile):
        with yaspin(text=f"Searching localhost for {repo_id}[{revision}]") as spinner:
            default_dir = os.path.join(profile.cache_dir, "models")
            spinner.text = f"Looking in default directory {default_dir}"
            if model_dir in os.listdir(default_dir):
                if revision in os.listdir(
                    os.path.join(default_dir, model_dir, "snapshots")
                ):
                    spinner.text = ""
                    spinner.ok(
                        f"{LogSymbols.SUCCESS.value} Found model"
                        f" {repo_id}[{revision}] in {default_dir}."
                    )
                    return os.path.join(default_dir, model_dir)
            backup_dir = os.path.join(profile.home_dir, "models")
            spinner.text = f"Looking in backup directory {backup_dir}"
            if model_dir in os.listdir(backup_dir):
                if revision in os.listdir(
                    os.path.join(backup_dir, model_dir, "snapshots")
                ):
                    spinner.text = ""
                    spinner.ok(
                        f"{LogSymbols.SUCCESS.value} Found model"
                        f" {repo_id}[{revision}] in {backup_dir}."
                    )
                    return os.path.join(backup_dir, model_dir)
            spinner.text = ""
            spinner.fail(
                f"{LogSymbols.ERROR.value} Unable to find {repo_id}[{revision}] on"
                f" {profile.host}."
            )
        return None
    else:
        raise NotImplementedError


def has_model(
    repo_id: str,
    profile: BlackfishProfile,
    revision: Optional[str] = None,
) -> bool:
    """Check if files exist for a given model and profile.

    Args:
        repo_id:
            A namespace (user or organization name) and repo separated by a `/`.
        revision:
            An optional Git revision id, which can be a branch name (e.g., 'main'),
            a tag (e.g., 'v0.1.0') or a commit hash (e.g., "ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971").
        profile:
            The name of a profile to search for model files, e.g., "default".

    Returns:
        bool
    """
    try:
        ModelCard.load(repo_id)
    except RepositoryNotFoundError:
        print(
            "Repository not found. Is this model hosted on Hugging Face? Check that"
            f" https://huggingface.co/{repo_id} is a valid url and that you are"
            " authenticated (if this is a private or gated repo)."
        )
        return False

    if revision is None:
        return repo_id in get_models(profile)
    else:
        if repo_id in get_models(profile):
            return revision in get_revisions(repo_id, profile)
        else:
            return False


def find_port(host="127.0.0.1", lower=8080, upper=8900, use_stdout=False) -> int:
    """Find a available port in the range `[lower, upper)`."""
    for port in range(lower, upper):
        try:
            client = socket.socket()
            client.bind((host, port))
            client.close()
            if use_stdout:
                print(f"{LogSymbols.SUCCESS.value} Found available port {port}.")
            else:
                logger.debug(f"Found available port {port}.")
            return int(port)
        except OSError:
            if port == upper - 1:
                if use_stdout:
                    print(
                        f"{LogSymbols.ERROR.value} Failed to bind port {port} on host"
                        f" {host}."
                    )
                else:
                    logger.debug(f"Failed to bind port {port} on host {host}.")
            else:
                if use_stdout:
                    print(
                        f"{LogSymbols.WARNING.value} Failed to bind port {port} on host"
                        f" {host}. Trying next port."
                    )
                else:
                    logger.debug(
                        f"Failed to bind port {port} on host {host}. Trying next port."
                    )
    raise OSError(f"OSError: no ports available in range {lower}-{upper}")


def get_images(profile: BlackfishProfile) -> list[str]:
    """Return a list of image files available to a given profile."""

    if isinstance(profile, SlurmRemote):
        matched_files = set()
        with yaspin(text=f"Searching {profile.host} for available images") as spinner:
            with Connection(profile.host, profile.user) as conn, conn.sftp() as sftp:
                for dir in [profile.cache_dir, profile.home_dir]:
                    spinner.text = f"Checking directory: {dir}"
                    files = sftp.listdir(os.path.join(dir, "images"))
                    matched_files.update([f for f in files if fnmatch(f, "*.sif")])
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(matched_files)} images.")
        return list(matched_files)

    elif isinstance(profile, LocalProfile):
        matched_files = set()
        with yaspin(text=f"Searching {profile.host} for available images") as spinner:
            for dir in [profile.cache_dir, profile.home_dir]:
                spinner.text = f"Checking directory: {dir}"
                files = os.listdir(os.path.join(dir, "images"))
                matched_files.update([f for f in files if fnmatch(f, "*.sif")])
            spinner.text = ""
            spinner.ok(f"{LogSymbols.SUCCESS.value} Found {len(matched_files)} images.")
        return list(matched_files)

    else:
        raise NotImplementedError


def has_image(
    image: str,
    image_tag: str,
    profile: BlackfishProfile,
) -> bool:
    """Check if the image file exists for the given profile.

    Args:
        image:
            Task image name (e.g., "text_generation", "speech_recognition").
        profile:
            Blackfish profile to search for the image file.
        image_tag:
            The version of the image file (e.g., "2.3.0"). If not provided,
            the function searches for any available versions.

    Returns:
        bool
    """
    image_file = f"{image.replace('_', '-')}-inference_{image_tag}.sif"

    with yaspin(text=f"Searching {profile.host} for available images") as spinner:
        spinner.text = ""
        if image_file in get_images(profile):
            spinner.ok(f"{LogSymbols.SUCCESS.value} Matching image found.")
            return True
        else:
            spinner.fail(f"{LogSymbols.ERROR.value} Matching image not found.")
            return False
