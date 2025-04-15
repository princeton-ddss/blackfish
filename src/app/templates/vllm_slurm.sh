{% extends "base_slurm.sh" %}
{% block command %}
apptainer instance run {{ ' --nv' if job_config.gres else '' }} \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/vllm_vllm-openai_v0.8.3.sif \
  {{ name }} \
  --model /data/snapshots/{{ container_config['revision'] }} \
  --port {{ container_config.port }} \
  --revision {{ container_config.revision }}
{%- endif %}
{% for key, value in container_config.launch_kwargs.iteritems() %}
  --{{ key }} {{ value }} \
{% endfor %}
{%- endblock %}
