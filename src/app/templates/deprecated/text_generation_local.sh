{% extends "base_local.sh" %}
{% block command %}
{%- if provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{ container_config.port }}:{{ container_config.port }} \
  -v {{ container_config.model_dir }}:/data \
  --name {{ name }} \
  ghcr.io/huggingface/text-generation-inference:2.3.0 \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
{%- elif provider == 'apptainer' %}
apptainer instance run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/text-generation-inference_2.3.0.sif \
  {{ name }} \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
{%- endif %}
{%- if container_config.revision %}
  --revision {{ container_config.revision }} \
{%- endif %}
{%- if container_config.validation_workers %}
  --validation-workers {{ container_config.validation_workers }} \
{%- endif %}
{%- if container_config.sharded %}
  --sharded {{ container_config.sharded }} \
{%- endif %}
{%- if container_config.num_shard %}
  --num-shard {{ container_config.num_shard }} \
{%- endif %}
{%- if container_config.quantize %}
  --quantize {{ container_config.quantize }} \
{%- endif %}
{%- if container_config.dtype %}
  --dtype {{ container_config.dtype }} \
{%- endif %}
{%- if container_config.trust_remote_code %}
  --trust-remote-code \
{%- endif %}
{%- if container_config.max_best_of %}
  --max-best-of {{ container_config.max_best_of }} \
{%- endif %}
{%- if container_config.max_stop_sequences %}
  --max-stop-sequences {{ container_config.max_stop_sequences }} \
{%- endif %}
{%- if container_config.max_top_n_tokens %}
  --max-top-n-tokens {{ container_config.max_top_n_tokens }} \
{%- endif %}
{%- if container_config.max_input_tokens %}
  --max-input-tokens {{ container_config.max_input_tokens }} \
{%- endif %}
{%- if container_config.max_total_tokens %}
  --max-total-tokens {{ container_config.max_total_tokens }} \
{%- endif %}
{%- if container_config.max_batch_size %}
  --max-batch-size {{ container_config.max_batch_size }} \
{%- endif %}
{%- if container_config.disable_custom_kernels %}
  --disable-custom-kernels
{%- endif %}
{%- endblock %}
