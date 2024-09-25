{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
{# The service API port is set as 8085 in the API Request#}
{# docker pull fjying/audiototextapi:arm64_hf #}
docker run -d \
  {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{container_config["port"]}}:{{container_config["port"]}} \
  -v "{{container_config["input_dir"]}}":"/data/audio" \
  -v "{{container_config["model_dir"]}}":"/data/model" \
  --name speech_recognition \
  fjying/audiototextapi:arm64_hf\
  --model_dir "/data/model" \
  --model_id {{container_config['model_id']}}\
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}}\
  {%- endif %}
  --port {{container_config["port"]}}
{%- elif container_config.provider == 'apptainer' %}
apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind "{{container_config["input_dir"]}}":"/data/audio" \
  --bind "{{container_config["model_dir"]}}":"/data/model" \
  {{ job_config.cache_dir }}/images/audiototextapi_amd64_hf.sif \
  --model_dir "/data/model" \
  --model_id {{container_config['model_id']}}\
  {%- if 'revision' in container_config %}
  --revision {{container_config['revision']}}\
  {%- endif %}
  --port $port
{%- endif %}
{%- endblock %}
