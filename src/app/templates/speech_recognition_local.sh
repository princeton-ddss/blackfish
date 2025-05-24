{% extends "base_local.sh" %}
{% block command %}
{%- if provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{ container_config.port }}:{{ container_config.port }} \
  -v {{ mount }}:/data/audio \
  -v {{ container_config.model_dir }}:/data/models \
  --name {{ name }} \
  ghcr.io/princeton-ddss/speech-recognition-inference:latest \
  --model_dir /data/models \
  --model_id {{ model }} \
  {%- if container_config.revision %}
  --revision {{container_config.revision }} \
  {%- endif %}
  --port {{ container_config.port }}
{%- elif provider == 'apptainer' %}
apptainer instance run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ mount }}:/data/audio \
  --bind {{ container_config.model_dir }}:/data/models \
  {{ profile.cache_dir }}/images/speech-recognition-inference_0.1.2.sif \
  {{ name }} \
  --model_dir /data/models \
  --model_id {{ model }} \
  {%- if container_config.revision %}
  --revision {{ container_config.revision }}\
  {%- endif %}
  --port {{ container_config.port }}
{%- endif %}
{%- endblock %}
