{% extends "base_slurm.sh" %}
{% block command %}
apptainer run {{ '--nv' if job_config.gres else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/vllm-openai_v0.8.4.sif \
  --model /data/snapshots/{{ container_config['revision'] }} \
  --port $port \
  --revision {{ container_config.revision }} \
  --trust-remote-code \
  --tensor-parallel-size {{ job_config.gres }} \
  {{ container_config.launch_kwargs if container_config.launch_kwargs else '' }}
{%- endblock %}
