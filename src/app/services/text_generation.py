import requests
from typing import Optional, Any
from dataclasses import dataclass, asdict

from app.services.base import Service, BaseConfig
from app.logger import logger


# NOTE: TextGeneration container is optimized for NVIDIA A100, A10G and T4 GPUs with
# CUDA 12.2+ and requires NVIDIA Container Toolkit on the service host. The image
# was built to run on GPU and will not reliably work without GPU support.


@dataclass
class TextGenerationConfig(BaseConfig):
    model_dir: Optional[str] = None
    revision: Optional[str] = None
    validation_workers: Optional[int] = None
    sharded: Optional[bool] = None
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
    launch_kwargs: Optional[dict[str, Any]] = None


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

    async def call(
        self, inputs: str, params: TextGenerationParameters
    ) -> requests.Response:
        logger.info(f"calling service {self.id}")
        try:
            headers = {
                "Content-Type": "application/json",
            }
            body = {
                "inputs": inputs,
                "parameters": asdict(params),
            }
            res = requests.post(
                f"http://localhost:{self.port}/generate", json=body, headers=headers
            )
        except Exception as e:
            raise e

        return res
