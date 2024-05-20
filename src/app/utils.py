import os
import socket
from typing import Optional, Tuple
from huggingface_hub import ModelCard
from huggingface_hub.utils._errors import RepositoryNotFoundError
from fabric.connection import Connection
from paramiko.sftp_client import SFTPClient
from app.config import BlackfishProfile, SlurmRemote
from app.logger import logger


def model_available(
    model_id: str,
    profile: BlackfishProfile,
    revision: Optional[str] = None,
):
    """Look for model files in the specified environment.

    Args:
        model_id:
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
        ModelCard.load(model_id)
    except RepositoryNotFoundError:
        print(
            f"Repository not found. Is this model hosted on Hugging Face? Check that https://huggingface.co/{model_id} is a valid url and that you are authenticated (if this is a private or gated repo)."
        )
        return False

    if isinstance(profile, SlurmRemote):
        remote = SlurmRemote(
            profile["host"],
            profile["user"],
            profile["home_dir"],
            profile["cache_dir"],
        )
        with Connection(remote.host, remote.user) as conn, conn.sftp() as sftp:
            _, cache_dir = model_dir_exists(
                model_id, remote.cache_dir, remote.home_dir, sftp
            )
            if cache_dir is not None:
                if revision is not None:
                    return revision_dir_exists(revision, cache_dir, sftp)
                else:
                    return True
    else:
        raise NotImplementedError


def model_dir_exists(
    model_id: str, cache_dir: str, home_dir: str, sftp: SFTPClient
) -> Tuple[bool, Optional[str]]:
    """Check if the expected model directory exists and return the location if found."""

    namespace, repo = model_id.split("/")
    model_dir = f"models--{'--'.join(model_id.split('/'))}"

    models = sftp.listdir(cache_dir)
    if f"models--{namespace}--{repo}" in models:
        return True, os.path.join(cache_dir, model_dir)

    backup_dir = os.path.join(home_dir, ".cache", "huggingface", "hub")
    models = sftp.listdir(backup_dir)
    if f"models--{namespace}--{repo}" in models:
        return True, os.path.join(backup_dir, model_dir)

    return False, None


def revision_dir_exists(revision: str, cache_dir: str, sftp: SFTPClient):
    """Check if the model revision directory exists."""

    if revision in sftp.listdir(os.path.join(cache_dir, "refs")):
        return True
    elif revision in sftp.listdir(os.path.join(cache_dir, "snapshots")):
        return True
    else:
        return False


def find_port(host="127.0.0.1", lower=8080, upper=8900) -> int:
    for port in range(lower, upper):
        try:
            client = socket.socket()
            client.bind((host, port))
            client.close()
            return int(port)
        except OSError:
            logger.debug(f"OSError: failed to bind port {port} on host {host}")
    raise OSError(f"OSError: no ports available in range {lower}-{upper}")
