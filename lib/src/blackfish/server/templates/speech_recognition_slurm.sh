{% extends "base_slurm.sh" %}
{% block command %}

XDG_RUNTIME_DIR=""

apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --env PYTHONNOUSERSITE=1 \
  --bind {{ mount }}:/data/audio \
  --bind {{ container_config.model_dir }}:/data/models \
  {{ profile.cache_dir }}/images/{{ image.sif }} \
  launch \
  --model-dir /data/models \
  --model-id {{ model }} \
  --revision {{ container_config.revision }} \
  --host 0.0.0.0 \
  --port $port
{%- endblock %}
