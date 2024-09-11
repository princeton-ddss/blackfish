{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
{# The service API port is set as 8085 in the API Request#}
{# docker pull fjying/audiototextapi:arm64_hf #}
docker run -d \
  {{ ' --gpus all' if job_config.gres else '' }} \
  -p {{container_config["port"]}}:{{container_config["port"]}} \
  {%- if 'revision' in container_config %}
  -e REVISION={{container_config['revision']}}\
  {%- endif %}
  -e SPEECH_RECOGNITION_PORT={{container_config["port"]}}\
  -v "{{container_config["input_dir"]}}":/app/files \
  -e MODEL_DIR="/app/files/models/Whisper_hf/models--openai--whisper-tiny"\
  -e INPUT_DIR="/app/files/data"\
  --name speech_recognition \
  fjying/audiototextapi:arm64_hf
{%- elif container_config.provider == 'apptainer' %}
apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  {%- if 'revision' in container_config %}
  --env="REVISION={{container_config['revision']}}" \
  {%- endif %}
  --env="SPEECH_RECOGNITION_PORT={{container_config["port"]}}" \
  --env="MODEL_DIR="{{job_config.model_dir}}"" \
  --env="INPUT_DIR="{{container_config['input_dir']}}"" \
  "{{ job_config.cache_dir }}/images/audiototextapi_amd64_hf.sif"
{%- endif %}
{%- endblock %}
