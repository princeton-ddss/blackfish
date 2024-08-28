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
  {%- if 'revision' in container_config %}
  --env="REVISION={{container_config['revision']}}" \
  {%- endif %}
  --env="SPEECH_RECOGNITION_PORT=$port" \
  --env="MODEL_DIR={{job_config.model_dir}}" \
  --env="INPUT_DIR={{job_config.input_dir}}" \
  {{ job_config.cache_dir }}/images/audiototextapi_amd64_hf.sif
{%- endblock %}
