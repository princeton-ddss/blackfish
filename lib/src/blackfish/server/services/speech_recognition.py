from typing import Optional
from dataclasses import dataclass

from blackfish.server.services.base import Service, BaseConfig


@dataclass
class SpeechRecognitionConfig(BaseConfig):
    model_dir: Optional[str]
    revision: Optional[str] = None


class SpeechRecognition(Service):
    """A containerized service running a speech recognition API."""

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }
