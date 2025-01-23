from typing import Optional, Literal
from dataclasses import dataclass, asdict, replace


@dataclass
class ContainerConfig:
    provider: Optional[str] = "apptainer"

    def data(self) -> dict:
        return {
            k: v
            for k, v in filter(lambda item: item[1] is not None, asdict(self).items())
        }

    def replace(self, changes: dict) -> None:
        return replace(self, **changes)


@dataclass
class TextGenerationConfig(ContainerConfig):
    model_dir: Optional[str] = None
    port: Optional[int] = None
    quantize: Optional[str] = None
    revision: Optional[str] = None
    validation_workers: Optional[int] = None
    sharded: Optional[Literal["true", "false"]] = None
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
class SpeechRecognitionConfig(ContainerConfig):
    model_id: str = (None,)
    model_dir: str = (None,)
    input_dir: str = (None,)
    port: int = (None,)
    revision: Optional[str] = None
