import requests
from typing import Optional
from dataclasses import dataclass

from jinja2 import Environment, PackageLoader

from app.services.base import Service, ContainerConfig
from app.job import LocalJobConfig, SlurmJobConfig, EC2JobConfig
from app.logger import logger


# NOTE: TextGeneration container is optimized for NVIDIA A100, A10G and T4 GPUs with
# CUDA 12.2+ and requires NVIDIA Container Toolkit on the service host. The image
# was built to run on GPU and will not reliably work wihtout GPU support.


TextGenerationModels = {
    "bigscience/bloom-560m": {
        "quantizations": [],
    },
    "google/flan": {},
    "facebook/galactica": {},
    "EleutherAI/gpt-neox": {},
    "facebook/opt": {},
    "bigcode/santacoder": {},
    "bigcode/starcoder": {},
    "tiiuae/falcon": {},
    "mosaicml/mpt": {},
    "meta-llama/Meta-Llama-3": {},
    "meta-llama/Meta-Llama-2": {},
    "meta-llama/CodeLlama": {},
    "mistralai/Mistral": {},
    "microsoft/phi-2": {},
}


@dataclass
class TextGenerationConfig(ContainerConfig):
    quantize: Optional[str] = None
    revision: Optional[str] = None
    validation_workers: Optional[int] = None
    sharded: Optional[bool] = True
    num_shard: Optional[int] = None
    quantize: Optional[str] = None
    speculate: Optional[int] = None
    dtype: Optional[str] = None
    trust_remote_code: Optional[bool] = None
    max_concurrent_requests: Optional[int] = None
    max_best_of: Optional[int] = None
    max_stop_sequences: Optional[int] = None
    max_top_n_tokens: Optional[int] = None
    max_input_tokens: Optional[int] = None
    max_input_length: Optional[int] = None
    max_total_tokens: Optional[int] = None
    max_batch_size: Optional[int] = None
    disable_custom_kernels: bool = False


@dataclass
class TextGenerationParameters:
    best_of: Optional[int] = None
    decoder_input_details: bool = True
    details: bool = True
    do_sample: bool = False
    max_new_tokens: Optional[int] = None
    repetition_penalty: float = 1.03
    return_full_text: bool = False
    seed: Optional[int] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_n_tokens: Optional[int] = None
    top_p: Optional[float] = None
    truncate: Optional[int] = None
    typical_p: Optional[float] = None
    watermark: Optional[bool] = False


class TextGeneration(Service):
    """A containerized service running a text-generation API."""

    __mapper_args__ = {
        "polymorphic_identity": "text_generation",
    }

    def launch_script(self, container_options: dict, job_options: dict) -> str:

        if self.job_type == "local":
            job_config = LocalJobConfig().replace(job_options)
        elif self.job_type == "slurm":
            job_config = SlurmJobConfig().replace(job_options)
        elif self.job_type == "ec2":
            job_config = EC2JobConfig().replace(job_options)
        elif self.job_type == "test":
            job_config = SlurmJobConfig().replace(job_options)

        container_config = TextGenerationConfig(**container_options)

        env = Environment(loader=PackageLoader("app", "templates"))
        template = env.get_template(f"text_generation_{self.job_type}.sh")
        job_script = template.render(
            model=self.model,
            name=self.name,
            job_config=job_config.data(),
            container_config=container_config.data(),
        )

        return job_script

    async def call(self, inputs: str, **kwargs) -> requests.Response:
        logger.info(f"calling service {self.service_id}")
        try:
            headers = {
                "Content-Type": "application/json",
            }
            body = {
                "inputs": inputs,
                "parameters": TextGenerationParameters(**kwargs).model_dump(
                    exclude_defaults=True
                ),
            }
            res = requests.post(
                f"http://127.0.0.1:{self.port}/generate", json=body, headers=headers
            )
            logger.info(f"response state {res.status_code}")
        except Exception as e:
            raise e

        return res

    async def ping(self) -> dict:
        logger.debug(f"Pinging service {self.id}")
        try:
            res = requests.get(f"http://127.0.0.1:{self.port}/health")
            logger.debug(f"response state {res.status_code}")
            return {"ok": res.ok}
        except Exception as e:
            return {"ok": False, "error": e}
