{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{ container_config.port }}:{{ container_config.port }} \
  -v {{ container_config.model_dir }}:/data \
  --name {{ name }} \
  ghcr.io/huggingface/text-generation-inference:2.3.0 \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
{%- elif container_config.provider == 'apptainer' %}
apptainer instance run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ job_config.cache_dir }}/images/text-generation-inference_2.3.0.sif \
  {{ name }} \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
{%- endif %}
{%- if 'revision' in container_config %}
  --revision {{ container_config['revision'] }} \
{%- endif %}
{%- if 'validation_workers' in container_config %}
  --validation-workers {{ container_config['validation_workers'] }} \
{%- endif %}
{%- if 'sharded' in container_config %}
  --sharded {{ container_config['sharded'] }} \
{%- endif %}
{%- if 'num_shard' in container_config %}
  --num-shard {{ container_config['num_shard'] }} \
{%- endif %}
{%- if 'quantize' in container_config %}
  --quantize {{ container_config['quantize'] }} \
{%- endif %}
{%- if 'dtype' in container_config %}
  --dtype {{ container_config['dtype'] }} \
{%- endif %}
{%- if container_config.get('trust_remote_code') == True %}
  --trust-remote-code \
{%- endif %}
{%- if 'max_best_of' in container_config %}
  --max-best-of {{ container_config['max_best_of'] }} \
{%- endif %}
{%- if 'max_stop_sequences' in container_config %}
  --max-stop-sequences {{ container_config['max_stop_sequences'] }} \
{%- endif %}
{%- if 'max_top_n_tokens' in container_config %}
  --max-top-n-tokens {{ container_config['max_top_n_tokens'] }} \
{%- endif %}
{%- if 'max_input_tokens' in container_config %}
  --max-input-tokens {{ container_config['max_input_tokens'] }} \
{%- endif %}
{%- if 'max_total_tokens' in container_config %}
  --max-total-tokens {{ container_config['max_total_tokens'] }} \
{%- endif %}
{%- if 'max_batch_size' in container_config %}
  --max-batch-size {{ container_config['max_batch_size'] }} \
{%- endif %}
{%- if container_config.get('disable_custom_kernels') == True %}
  --disable-custom-kernels
{%- endif %}
{%- endblock %}
