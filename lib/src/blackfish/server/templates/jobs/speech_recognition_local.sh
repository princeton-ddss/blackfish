{% extends "base_local.sh" %}
{% block command %}
{%- if provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -v {{ mount }}:/data/audio \
  -v {{ container_config.model_dir }}:/data/models \
  ghcr.io/princeton-ddss/speech-recognition-inference:0.2.1 \
  pipeline \
  /data/audio \
  --model-id {{ model }} \
  --model-dir /data/models \
  --revision {{container_config.revision }} \
  --job-id {{ uuid }} \
{%- elif provider == 'apptainer' %}
apptainer instance run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ mount }}:/data/audio \
  --bind {{ container_config.model_dir }}:/data/models \
  {{ profile.cache_dir }}/images/speech-recognition-inference_0.2.1.sif \
  pipeline \
  /data/audio \
  --model-dir /data/models \
  --model-id {{ model }} \
  --revision {{ container_config.revision }} \
  --job-id {{ uuid }} \
{%- endif %}
{%- if container_config.kwargs %}
  {{ " ".join(container_config.kwargs) }}
{%- endif %}
{%- endblock %}
