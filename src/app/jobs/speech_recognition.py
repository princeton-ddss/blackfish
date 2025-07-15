import json
import os
import subprocess
from typing import Optional
from dataclasses import dataclass

from litestar.datastructures import State


from app.jobs.base import BatchJob, BaseConfig, BatchJobProgress
from app.logger import logger
from app.models.profile import SlurmProfile


@dataclass
class SpeechRecognitionBatchConfig(BaseConfig):
    model_dir: Optional[str]
    revision: Optional[str] = None
    kwargs: Optional[list[str]] = None


class SpeechRecognitionBatch(BatchJob):
    """A containerized batch job running speech recognition inference."""

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }

    def get_progress(self, app_config: State) -> BatchJobProgress | None:
        """Fetch the progress of the batch job."""
        profile = self.get_profile(app_config)
        if profile is None:
            logger.warning(
                f"Unable to fetch progress: batch job {self.id} is missing a `profile`."
            )
            return None
        if self.mount is None:
            logger.warning(
                f"Unable to fetch progress: batch job {self.id} is missing a `mount`."
            )
            return None
        logger.debug(
            f"Fetching progress from {os.path.join(self.mount, f'.checkpoint-{self.id.hex}')}"
        )
        if profile.is_local():
            logger.debug("Using local profile to fetch progress.")
            try:
                with open(
                    os.path.join(self.mount, f".checkpoint-{self.id.hex}"),
                    "r",
                ) as f:
                    data = json.load(f)
            except FileNotFoundError:
                logger.warning(
                    f"Checkpoint file not found for batch job {self.id}. Returning None."
                )
                return None
        elif isinstance(profile, SlurmProfile):
            try:
                res = subprocess.check_output(
                    [
                        "ssh",
                        f"{profile.user}@{profile.host}",
                        "cat",
                        f"{self.mount}/.checkpoint-{self.id.hex}",
                    ]
                )
                data = json.loads(res.decode("utf-8"))
            except Exception:
                logger.warning(
                    f"Checkpoint file not found for batch job {self.id}. Returning None."
                )
                return None
        else:
            logger.error(
                f"Unable to fetch profile: unsupported profile type {type(profile)}."
            )
            return None

        logger.debug(f"Found progress: {data}")
        return BatchJobProgress(**data)
