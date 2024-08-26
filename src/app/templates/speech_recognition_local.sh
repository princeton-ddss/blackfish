{% extends "base_local.sh" %}
{% block command %}
{%- if container_config.provider == "docker" %}
docker pull fjying/audiototextapi:arm64_hf
docker run -d \
  {{ ' --gpus all' if job_config.gres else '' }} \
  -p $port:$port \
  -e MODEL_NAME={{container_config['model_name']}}\
  -e MODEL_SIZE={{container_config['model_size']}}\
  -e MODEL_FOLDER={{job_config.model_dir}}\
  -e INPUT_FOLDER={{job_config.input_dir}}\
  -v {{job_config.input_dir}}:/app/files \
  --name speech_recognition_api_container
  fjying/audiototextapi:arm64_hf


