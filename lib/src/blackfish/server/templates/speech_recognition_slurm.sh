{% extends "base_slurm.sh" %}
{% block command %}

XDG_RUNTIME_DIR=""

apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ mount }}:/data/audio \
  --bind {{ container_config.model_dir }}:/data/models \
  {{ profile.cache_dir }}/images/speech-recognition-inference_0.1.2.sif \
  --model_dir /data/models \
  --model_id {{ model }} \
  --revision {{ container_config.revision }} \
  --port $port
{%- endblock %}
