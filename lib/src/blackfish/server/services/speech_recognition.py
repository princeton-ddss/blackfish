from typing import Optional
from dataclasses import dataclass

from blackfish.server.services.base import Service, BaseConfig


@dataclass
class SpeechRecognitionConfig(BaseConfig):
    # Defaulted to match TextGenerationConfig: BaseConfig now carries the
    # defaulted `api_key`, and a dataclass cannot place a non-default field
    # after one with a default. Both call sites construct by keyword.
    model_dir: Optional[str] = None
    revision: Optional[str] = None


class SpeechRecognition(Service):
    """A containerized service running a speech recognition API."""

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }

    def auth_headers(self) -> dict[str, str]:
        """speech-recognition-inference compares a bare `Token` header.

        No bearer prefix: its `run_transcription` takes `Token: str = Header(None)`
        and compares the value directly.
        """
        if not self._api_key:
            return {}
        return {"Token": self._api_key}
