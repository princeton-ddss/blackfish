import requests
from typing import Union, Literal, Optional
from dataclasses import dataclass

from app.services.base import Service, BaseConfig
from app.logger import logger


@dataclass
class SpeechRecognitionConfig(BaseConfig):
    model_dir: Optional[str]
    revision: Optional[str] = None


class SpeechRecognition(Service):
    """A containerized service running a speech recognition API."""

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }

    # Call Blackfish API
    async def call(
        self,
        audio_path: str,
        language: Union[str, None] = None,
        response_format: Literal["json", "text"] = "json",
    ) -> requests.Response:
        logger.info(f"calling service {self.id}")
        try:
            body = {
                "audio_path": audio_path,
                "language": language,
                "response_format": response_format,
            }
            res = requests.post(f"http://localhost:{self.port}/transcribe", json=body)
        except Exception as e:
            raise e

        return res
