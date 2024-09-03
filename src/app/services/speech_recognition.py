import requests
from typing import Union, Literal, Optional
from dataclasses import dataclass

from jinja2 import Environment, PackageLoader

from app.services.base import Service, ContainerConfig
from app.job import LocalJobConfig, SlurmJobConfig, EC2JobConfig
from app.logger import logger

# The container options which are needed when setting up
# service API. These options are not in job.py
@dataclass
class SpeechRecognitionConfig(ContainerConfig):
    input_dir: str = None
    revision: Optional[str] = None
    port: Optional[int] = None



class SpeechRecognition(Service):
    """A containerized service running a speech recognition API."""

    __mapper_args__ = {
        "polymorphic_identity": "speech_recognition",
    }

    def launch_script(
        self, container_options: dict, job_options: dict, job_id: str = None
    ) -> str:
        if self.job_type == "local":
            job_config = LocalJobConfig().replace(job_options)
        elif self.job_type == "slurm":
            job_config = SlurmJobConfig().replace(job_options)
        elif self.job_type == "ec2":
            job_config = EC2JobConfig().replace(job_options)

        container_config = SpeechRecognitionConfig(**container_options)

        env = Environment(loader=PackageLoader("app", "templates"))
        template = env.get_template(f"speech_recognition_{self.job_type}.sh")
        job_script = template.render(
            model=self.model,
            name=self.name,
            job_config=job_config.data(),
            container_config=container_config.data(),
            job_id=job_id
        )
        return job_script

    # Call Blackfish API
    async def call(
        self,
        file_name: str,
        language: Union[str, None] = None,
        response_format: Literal["json", "text"] = "json",
    ) -> requests.Response:
        logger.info(f"calling service {self.service_id}")
        try:
            body = {
                "file_name": file_name,
                "language": language,
                "response_format": response_format,
            }
            res = requests.post(f"http://127.0.0.1:{self.port}/transcribe", json=body)
            logger.info(f"response state {res.status_code}")
        except Exception as e:
            raise e

        return res

    async def ping(self) -> dict:
        logger.debug(f"Pinging service {self.id}")
        try:
            res = requests.get(f"http://127.0.0.1:{self.port}")
            logger.debug(f"response state {res.status_code}")
            return {"ok": res.ok}
        except Exception as e:
            return {"ok": False, "error": e}
