{% extends "base_slurm.sh" %}
{% block command %}

export XDG_RUNTIME_DIR=""

apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ mount }}:/data/audio \
  --bind {{ container_config.model_dir }}:/data/models \
  {{ profile.cache_dir }}/images/speech-recognition-inference_0.2.1.sif \
  pipeline \
  /data/audio \
  --model-dir /data/models \
  --model-id {{ model }} \
  --revision {{ container_config.revision }} \
  --job-id {{ uuid }} \
{%- if container_config.kwargs %}
  {{ " ".join(container_config.kwargs) }}
{%- endif %}
{%- endblock %}
