"""Model metadata fetching and caching for HPC resource recommendations."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from huggingface_hub import HfApi, get_safetensors_metadata
from huggingface_hub.utils import EntryNotFoundError, RepositoryNotFoundError


# Mapping of torch dtype strings to bytes per parameter
DTYPE_BYTES = {
    "float32": 4,
    "float16": 2,
    "bfloat16": 2,
    "int8": 1,
    "int4": 0.5,
    "uint8": 1,
}


@dataclass
class ModelMetadata:
    """Metadata about a model's size and characteristics."""

    model_size_gb: float
    size_source: str  # "safetensors" | "bin_files" | "calculated" | "unknown"
    parameter_count: Optional[int] = None
    dtype: Optional[str] = None
    fetched_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ModelMetadata":
        """Create from dictionary."""
        return cls(
            model_size_gb=data.get("model_size_gb", 0.0),
            size_source=data.get("size_source", "unknown"),
            parameter_count=data.get("parameter_count"),
            dtype=data.get("dtype"),
            fetched_at=data.get("fetched_at"),
        )


def _get_safetensors_size(repo_id: str, token: Optional[str] = None) -> Optional[tuple[float, Optional[int]]]:
    """Try to get model size from safetensors metadata.

    Returns:
        Tuple of (size_gb, parameter_count) or None if not available.
    """
    try:
        metadata = get_safetensors_metadata(repo_id, token=token)
        if metadata is None:
            return None

        # Sum up tensor sizes
        total_bytes = 0
        total_params = 0

        if hasattr(metadata, "tensors") and metadata.tensors:
            for tensor_info in metadata.tensors.values():
                if hasattr(tensor_info, "nbytes"):
                    total_bytes += tensor_info.nbytes
                # Count parameters from shape
                if hasattr(tensor_info, "shape"):
                    params = 1
                    for dim in tensor_info.shape:
                        params *= dim
                    total_params += params

        # Also check parameter_count attribute if available
        if hasattr(metadata, "parameter_count") and metadata.parameter_count:
            total_params = sum(metadata.parameter_count.values())

        if total_bytes > 0:
            size_gb = total_bytes / (1024**3)
            return (size_gb, total_params if total_params > 0 else None)

        return None
    except (EntryNotFoundError, RepositoryNotFoundError, Exception):
        return None


def _get_bin_files_size(repo_id: str, token: Optional[str] = None) -> Optional[float]:
    """Get model size by summing .bin file sizes from repository.

    Returns:
        Size in GB or None if not available.
    """
    try:
        api = HfApi()
        repo_info = api.repo_info(repo_id, token=token, files_metadata=True)

        if not repo_info.siblings:
            return None

        total_bytes = 0
        for sibling in repo_info.siblings:
            if sibling.rfilename.endswith((".bin", ".safetensors")):
                if sibling.size is not None:
                    total_bytes += sibling.size

        if total_bytes > 0:
            return total_bytes / (1024**3)

        return None
    except Exception:
        return None


def _calculate_from_config(repo_id: str, token: Optional[str] = None) -> Optional[tuple[float, int, str]]:
    """Estimate model size from config.json parameters.

    Returns:
        Tuple of (size_gb, parameter_count, dtype) or None if not available.
    """
    try:
        api = HfApi()
        config_path = api.hf_hub_download(
            repo_id,
            filename="config.json",
            token=token,
        )

        with open(config_path) as f:
            config = json.load(f)

        # Try to get parameter count from common config fields
        num_params = None

        # Check for explicit num_parameters
        if "num_parameters" in config:
            num_params = config["num_parameters"]

        # Estimate from architecture if num_parameters not available
        if num_params is None:
            hidden_size = config.get("hidden_size", config.get("d_model", 0))
            num_layers = config.get("num_hidden_layers", config.get("n_layer", 0))
            vocab_size = config.get("vocab_size", 0)
            intermediate_size = config.get("intermediate_size", hidden_size * 4)

            if hidden_size and num_layers and vocab_size:
                # Rough estimation: embeddings + transformer layers
                embedding_params = vocab_size * hidden_size * 2  # input + output embeddings
                layer_params = num_layers * (
                    4 * hidden_size * hidden_size +  # attention
                    2 * hidden_size * intermediate_size  # FFN
                )
                num_params = embedding_params + layer_params

        if num_params is None or num_params == 0:
            return None

        # Get dtype
        dtype = config.get("torch_dtype", "float16")
        bytes_per_param = DTYPE_BYTES.get(dtype, 2)

        size_bytes = num_params * bytes_per_param
        size_gb = size_bytes / (1024**3)

        return (size_gb, num_params, dtype)
    except Exception:
        return None


def fetch_model_metadata(repo_id: str, token: Optional[str] = None) -> ModelMetadata:
    """Fetch model metadata from Hugging Face Hub.

    Uses fallback chain:
    1. Safetensors metadata (most accurate)
    2. Sum of .bin/.safetensors file sizes
    3. Calculated from config.json

    Args:
        repo_id: Hugging Face model repository ID (e.g., "meta-llama/Llama-2-7b")
        token: Optional HF API token for private/gated models

    Returns:
        ModelMetadata with size and source information
    """
    fetched_at = datetime.now(timezone.utc).isoformat()

    # Try safetensors first
    safetensors_result = _get_safetensors_size(repo_id, token)
    if safetensors_result is not None:
        size_gb, param_count = safetensors_result
        return ModelMetadata(
            model_size_gb=round(size_gb, 2),
            size_source="safetensors",
            parameter_count=param_count,
            fetched_at=fetched_at,
        )

    # Try bin files
    bin_size = _get_bin_files_size(repo_id, token)
    if bin_size is not None:
        return ModelMetadata(
            model_size_gb=round(bin_size, 2),
            size_source="bin_files",
            fetched_at=fetched_at,
        )

    # Try calculating from config
    calc_result = _calculate_from_config(repo_id, token)
    if calc_result is not None:
        size_gb, param_count, dtype = calc_result
        return ModelMetadata(
            model_size_gb=round(size_gb, 2),
            size_source="calculated",
            parameter_count=param_count,
            dtype=dtype,
            fetched_at=fetched_at,
        )

    # Fallback to unknown
    return ModelMetadata(
        model_size_gb=0.0,
        size_source="unknown",
        fetched_at=fetched_at,
    )


def get_cached_metadata(repo_id: str, cache_dir: str) -> Optional[ModelMetadata]:
    """Read cached metadata from info.json.

    Args:
        repo_id: Hugging Face model repository ID
        cache_dir: Path to cache directory containing info.json

    Returns:
        ModelMetadata if cached, None otherwise
    """
    info_path = Path(cache_dir) / "info.json"

    if not info_path.exists():
        return None

    try:
        with open(info_path) as f:
            data = json.load(f)

        if repo_id not in data:
            return None

        entry = data[repo_id]

        # Handle old format (string only)
        if isinstance(entry, str):
            return None

        # Handle new format (dict with metadata)
        if isinstance(entry, dict) and "metadata" in entry:
            return ModelMetadata.from_dict(entry["metadata"])

        return None
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def update_cached_metadata(
    repo_id: str,
    cache_dir: str,
    metadata: ModelMetadata,
    image: Optional[str] = None,
) -> None:
    """Update metadata in info.json cache.

    Args:
        repo_id: Hugging Face model repository ID
        cache_dir: Path to cache directory containing info.json
        metadata: Metadata to cache
        image: Optional pipeline image type (e.g., "text-generation")
    """
    info_path = Path(cache_dir) / "info.json"

    # Load existing data
    if info_path.exists():
        try:
            with open(info_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, TypeError):
            data = {}
    else:
        data = {}

    # Get existing image if not provided
    if image is None:
        existing = data.get(repo_id)
        if isinstance(existing, str):
            image = existing
        elif isinstance(existing, dict):
            image = existing.get("image", "unknown")
        else:
            image = "unknown"

    # Update with new format
    data[repo_id] = {
        "image": image,
        "metadata": metadata.to_dict(),
    }

    # Write back
    with open(info_path, "w") as f:
        json.dump(data, f, indent=2)


def refresh_metadata(
    repo_id: str,
    cache_dir: str,
    token: Optional[str] = None,
) -> ModelMetadata:
    """Force refresh metadata from HF Hub and update cache.

    Args:
        repo_id: Hugging Face model repository ID
        cache_dir: Path to cache directory
        token: Optional HF API token

    Returns:
        Fresh ModelMetadata
    """
    metadata = fetch_model_metadata(repo_id, token)
    update_cached_metadata(repo_id, cache_dir, metadata)
    return metadata
