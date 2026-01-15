import requests
from typing import Union, Literal, Optional
from dataclasses import dataclass

from blackfish.server.services.base import Service, BaseConfig
from blackfish.server.logger import logger


@dataclass
class SpeechRecognitionConfig(BaseConfig):
    model_dir: Optional[str]
    revision: Optional[str] = None


class SpeechRecognition(Service):
    """A containerized service running a speech recognition API.

    Examples:
        ```python
        svc = SpeechRecognition(...)
        res = svc("/audio/test.mp3")
        ```
    """

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }

    async def __call__(
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
