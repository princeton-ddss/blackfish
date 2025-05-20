from __future__ import annotations

from typing import Tuple, Optional
import json
import shutil
from pathlib import Path
from log_symbols.symbols import LogSymbols
from huggingface_hub import snapshot_download, model_info, scan_cache_dir, ModelInfo
from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy.orm import Mapped
from app.models.profile import BlackfishProfile as Profile


PIPELINE_IMAGES = {
    None: "none",
    # audio
    "automatic-speech-recognition": "speech-recognition",
    # computer vision
    "image-classification": "image-classification",
    "object-detection": "object-detection",
    "video-classification": "video-classification",
    # multimodel
    "image-text-to-text": "image-text-to-text",
    "audio-text-to-text": "audio-text-to-text",
    "video-text-to-text": "video-text-to-text",
    "any-to-any": "any-to-any",
    # natural language processing
    "text-classification": "text-classification",
    "text-generation": "text-generation",
    "text-to-image": "text-to-image",
}


class Model(UUIDAuditBase):
    __tablename__ = "model"
    repo: Mapped[str]  # e.g., bigscience/bloom-560m
    profile: Mapped[str]  # e.g.,  hpc
    revision: Mapped[str]
    image: Mapped[str]  # e.g., "text-generation"
    model_dir: Mapped[str]  # e.g., "<home_dir>/models/models--<namespace>--<model>"


class ModelNotFoundError(FileNotFoundError): ...


class RevisionNotFoundError(FileNotFoundError): ...


def split(repo_id: str) -> Tuple[str, str]:
    repo_id, revision = repo_id.split("/")
    return repo_id, revision


def remove_model(
    repo_id: str, profile: Profile, revision: str | None = None, use_cache: bool = False
) -> None:
    """Delete a model's snapshot files and remove its data from the local info cache.

    This method only works for *local* profiles, i.e., the model files can only be
    deleted locally. In addition to deleting the model files, the method deletes the entry
    in models/info.json that serves as a local cache of the model's pipeline tag, i.e.,
    which API image(s) the model is compatible with.

    Args:
        repo_id: the model to remove, e.g., "bigscience/bloom-560m".
        profile: the profile to remove the model from.
        revision: an optional revision to remove. *All* revisions are removed by default.
        use_cache: remove files from the profile's cache directory. If False, files are
            removed from the profile's home directory. Default: False.
    """

    namespace, model_id = split(repo_id)
    cache_dir = (
        Path(*[f"{profile.cache_dir}", "models"])
        if use_cache
        else Path(*[f"{profile.home_dir}", "models"])
    )
    model_dir = cache_dir.joinpath(f"models--{namespace}--{model_id}")

    if revision is None:
        try:
            shutil.rmtree(model_dir)
        except FileNotFoundError:
            raise ModelNotFoundError(f"{repo_id} not found in directory {cache_dir}.")
    else:
        op = scan_cache_dir().delete_revisions(revision)
        if len(list(op.blobs)) == 0:
            raise RevisionNotFoundError(
                f"{revision} not found in directory {cache_dir}."
            )
        else:
            op.execute()

    with open(f"{cache_dir}/info.json", mode="r") as f:
        data = json.load(f)
        if repo_id in data.keys():
            del data[repo_id]

    with open(f"{cache_dir}/info.json", mode="w") as f:
        f.write(json.dumps(data))


def get_pipeline(res: ModelInfo) -> str | None:
    if res.pipeline_tag is not None:
        return res.pipeline_tag
    if res.card_data is not None:
        pipeline: str | None = res.card_data.get("pipeline_tag", None)
        return pipeline

    return None


def add_model(
    repo_id: str,
    profile: Profile,
    revision: str | None = None,
    use_cache: bool = False,
) -> Optional[Tuple[Model, str]]:
    """Download a model from Hugging Face and makes it available to Blackfish.

    This method only works for *local* profiles, i.e., the model files can only be
    downloaded locally. In addition to downloading the model files, the method creates
    or updates an entry in models/info.json that serves as a local cache of the model's
    pipeline tag, i.e., which API image(s) the model is compatible with.

    Args:
        repo_id: the model to download, e.g., "bigscience/bloom-560m".
        profile: the profile to add the model to. This argument determines where
            model snapshot files are stored and provides access to gated model.
            through associated Hugging Face access tokens.
        revision: an optional revision to download. The most recently available
            revision is downloaded by default.
        use_cache: store files to the profile's cache directory. If False, files are
            stored to the profile's home directory. Default: False.

    Returns:
        A mapped Model object

    Raises:
        RepositoryNotFoundError
        RevisionNotFoundError
        GatedRepoError
    """

    cache_dir = (
        Path(*[profile.cache_dir, "models"])
        if use_cache
        else Path(*[profile.home_dir, "models"])
    )

    if hasattr(profile, "token"):
        token = profile.token
    else:
        token = None

    path = snapshot_download(
        repo_id=repo_id,
        token=token,
        cache_dir=cache_dir,
        revision=revision,
    )

    revision = path.split("/")[-1]
    res = model_info(repo_id=repo_id)
    pipeline = get_pipeline(res)  # e.g., "text-generation"

    try:
        with open(cache_dir.joinpath("info.json"), mode="r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(
            f"{LogSymbols.WARNING.value} No info.json file found. Creating a new one."
        )
        data = dict()

    data[repo_id] = PIPELINE_IMAGES[pipeline]

    with open(f"{cache_dir}/info.json", mode="w") as f:
        f.write(json.dumps(data))

    return (
        Model(
            repo=repo_id,
            revision=revision,
            profile=profile.name,
            image=PIPELINE_IMAGES[pipeline],
        ),
        path,
    )
