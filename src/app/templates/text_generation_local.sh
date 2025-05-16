{% extends "base_local.sh" %}
{% block command %}
{%- if provider == "docker" %}
docker run -d {{ '--runtime nvidia --gpus all' if job_config.gres else '' }} \
  -p {{ container_config.port }}:{{ container_config.port }} \
  -v {{ container_config.model_dir }}:/data \
  --name {{ name }} \
  vllm/vllm-openai:v0.8.5 \
  --model /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
  --revision {{ container_config.revision }}
{%- elif provider == 'apptainer' %}
apptainer instance run {{ ' --nv' if job_config.gres else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/vllm-openai_v0.8.5.sif \
  {{ name }} \
  --model /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
  --revision {{ container_config.revision }}
{%- endif %}
  {{ container_config.launch_kwargs }}
{%- endblock %}
