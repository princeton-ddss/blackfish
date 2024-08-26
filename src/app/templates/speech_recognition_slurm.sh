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

apptainer run {{ ' --nv' if job_config.gres > 0 else '' }}\
  --env="SPEECH_RECOGNITION_PORT=$port" \
  --env="MODEL_NAME={{container_config['model_name']}}" \
  --env="MODEL_SIZE={{container_config['model_size']}}" \
  --env="MODEL_FOLDER={{job_config.model_dir}}" \
  --env="INPUT_FOLDER={{job_config.input_dir}}" \
  /scratch/gpfs/{{ job_config.user }}/images/audiototextapi_amd64_hf.sif
{%- endblock %}
