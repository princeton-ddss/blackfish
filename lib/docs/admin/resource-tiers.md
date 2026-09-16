# Resource Tiers

Resource tiers allow HPC administrators to define pre-configured resource bundles that users can select when launching services through the Blackfish UI. This simplifies the user experience by presenting meaningful options like "Small", "Medium", and "Large" instead of requiring users to manually specify GPU counts, memory, and CPU cores.

## Configuration File

Resource tiers are configured in a `resource_specs.yaml` file placed in the profile's `cache_dir`. For shared HPC environments, this is typically a shared directory like `/shared/.blackfish/resource_specs.yaml`.

If no configuration file exists, Blackfish uses sensible defaults with four tiers: CPU Only, Small (1 GPU), Medium (2 GPUs), and Large (4 GPUs).

## Schema

```yaml
time:
  default: 30
  max: 180

partitions:
  gpu:
    default: true
    tiers:
      - name: Small
        description: "Small models (up to 16GB)"
        max_model_size_gb: 16
        gpu_count: 1
        gpu_type: a100
        cpu_cores: 4
        memory_gb: 16
        slurm:
          constraint: "gpu80"

      - name: Medium
        description: "Medium models (up to 80GB)"
        max_model_size_gb: 80
        gpu_count: 2
        cpu_cores: 8
        memory_gb: 32

      - name: Large
        description: "Large models (80GB+)"
        max_model_size_gb: null
        gpu_count: 4
        cpu_cores: 16
        memory_gb: 64

  cpu:
    default: false
    tiers:
      - name: CPU Only
        description: "For testing or small models"
        max_model_size_gb: 2
        gpu_count: 0
        cpu_cores: 4
        memory_gb: 8

models:
  "meta-llama/Llama-2-70b-hf": "gpu.Large"
  "openai/whisper-large-v3": "gpu.Medium"
```

## Tier Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Display name for the tier |
| `description` | string | Yes | User-facing description |
| `max_model_size_gb` | number/null | Yes | Maximum model size (null = no limit) |
| `gpu_count` | integer | Yes | Number of GPUs to request |
| `gpu_type` | string | No | GPU type label shown in the UI |
| `cpu_cores` | integer | Yes | Number of CPU cores |
| `memory_gb` | integer | Yes | Memory in GB |
| `slurm` | object | No | Additional Slurm flags |

## Slurm Configuration

The optional `slurm` section supports:

- `constraint`: Passed directly to Slurm's `--constraint` flag (e.g., `"gpu80"` for 80GB GPUs)
- `gres`: Custom gres specification (e.g., `"gpu:a100"`)

## Tier Selection

When a user launches a service, Blackfish automatically recommends a tier based on the model's size:

1. **Model override**: If the model appears in the `models` section, that tier is used
2. **Size matching**: Otherwise, the smallest tier whose `max_model_size_gb` exceeds the model size is selected
3. **Catch-all**: If no tier matches, the tier with `max_model_size_gb: null` is used

Users can override the automatic selection in the UI.

[^1]: If you only intend to run services on your laptop, Blackfish will attempt to download each image automatically the first time you run its corresponding service. In this case, expect the startup time for the first run of each service type to take much longer than subsequent runs.
