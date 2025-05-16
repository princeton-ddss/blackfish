{% extends "base_slurm.sh" %}
{% block command %}
apptainer instance run {{ '--nv' if job_config.gres else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/vllm-openai_v0.8.5.sif \
  {{ name }} \
  --model /data/snapshots/{{ container_config['revision'] }} \
  --trust-remote-code \
  --port $port \
  --revision {{ container_config.revision }}
  {{ container_config.launch_kwargs }}
{%- endblock %}
