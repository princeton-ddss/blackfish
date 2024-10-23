{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
docker run -d {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{container_config["port"]}}:{{ container_config.port }} \
  -v {{container_config["input_dir"]}}:/data/audio \
  -v {{container_config["model_dir"]}}:/data/models \
  --name {{ name }} \
  ghcr.io/princeton-ddss/speech-recognition-inference:latest \
  --model_dir /data/models \
  --model_id {{container_config['model_id']}} \
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}} \
  {%- endif %}
  --port {{ container_config.port }}
{%- elif container_config.provider == 'apptainer' %}
apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{container_config["input_dir"]}}:/data/audio \
  --bind {{container_config["model_dir"]}}:/data/models \
  {{ job_config.cache_dir }}/images/speech-recognition-inference_0.1.1.sif \
  {{ name }}
  --model_dir /data/models \
  --model_id {{ container_config['model_id'] }} \
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}}\
  {%- endif %}
  --port {{ container_config.port }}
{%- endif %}
{%- endblock %}
