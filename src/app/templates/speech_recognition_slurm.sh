{% extends "base_slurm.sh" %}
{% block command %}

XDG_RUNTIME_DIR=""
node=$(hostname -s)
user=$(whoami)
cluster="della-gpu"

apptainer run {{ ' --nv' if job_config.gres > 0 else '' }} \
  --bind {{ container_config["input_dir"] }}:/data/audio \
  --bind {{ container_config["model_dir"] }}:/data/models \
  {{ job_config.cache_dir }}/images/speech-recognition-inference_{{ container_config.image_tag }}.sif \
  --model_dir /data/models \
  --model_id {{ model }} \
  {%- if 'revision' in container_config %}
  --revision {{ container_config['revision'] }} \
  {%- endif %}
  --port $port
{%- endblock %}
