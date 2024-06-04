{%- if container_config.platform == "docker" %}
docker run {{ ' --gpus all' if job_config.gres else '' }}\
  --volume {{ job_config.model_dir }}:/data \
  ghcr.io/huggingface/text-generation-inference:latest \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port $port \
{%- elif container_config.platform == 'apptainer' %}
apptainer run {{ ' --nv' if job_config.gres > 0 else '' }}\
  --bind {{ job_config.model_dir }}:/data \
  {{ job_config.cache_dir }}/images/text-generation-inference_latest.sif \
  --model-id /data/snapshots/{{ container_config['revision'] }} \
  --port $port \
{%- endif %}
{%- if 'revision' in container_config %}
  --revision {{ container_config['revision'] }} \
{%- endif %}
{%- if 'validation_workers' in container_config %}
  --validation-workers {{ container_config['validation_workers'] }} \
{%- endif %}
{%- if container_config.get('sharded') == True %}
  --sharded \
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