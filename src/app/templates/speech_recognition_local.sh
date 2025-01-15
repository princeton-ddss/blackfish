{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{container_config["port"]}}:{{ container_config.port }} \
  -v {{container_config["input_dir"]}}:/data/audio \
  -v {{container_config["model_dir"]}}:/data/models \
  --name {{ name }} \
  ghcr.io/princeton-ddss/speech-recognition-inference:{{ container_config.image_tag }} \
  --model_dir /data/models \
  --model_id {{ model }} \
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}} \
  {%- endif %}
  --port {{ container_config.port }}
{%- elif container_config.provider == 'apptainer' %}
apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{container_config["input_dir"]}}:/data/audio \
  --bind {{container_config["model_dir"]}}:/data/models \
  {{ job_config.cache_dir }}/images/speech-recognition-inference_{{ container_config.image_tag }}.sif \
  {{ name }}
  --model_dir /data/models \
  --model_id {{ model }} \
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}}\
  {%- endif %}
  --port {{ container_config.port }}
{%- endif %}
{%- endblock %}
