{% extends "base_slurm.sh" %}
{% block command %}
# get tunneling info
XDG_RUNTIME_DIR=""
node=$(hostname -s)
user=$(whoami)
cluster="della-gpu"

# print tunneling instructions jupyter-log
echo -e "
Command to create ssh tunnel:
ssh -N -f -L ${port}:${node}:${port} ${user}@${cluster}.princeton.edu"

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
{%- endblock %}
