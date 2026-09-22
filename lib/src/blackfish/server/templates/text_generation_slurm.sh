{% extends "base_slurm.sh" %}
{% block command %}
export SINGULARITY_NO_EVAL=1
apptainer run {{ '--nv' if job_config.gres else '' }} \
  --env PYTHONNOUSERSITE=1 \
  --bind {{ container_config.model_dir }}:/data \
  {{ profile.cache_dir }}/images/{{ image.sif }} \
  /data/snapshots/{{ container_config['revision'] }} \
  --port $port \
  --revision {{ container_config.revision }} \
  --trust-remote-code \
  --tensor-parallel-size {{ job_config.gres }} \
{%- if container_config.api_key %}
  --api-key {{ container_config.api_key | shquote }} \
{%- endif %}
  {{ container_config.launch_kwargs if container_config.launch_kwargs else '' }}
{%- endblock %}
