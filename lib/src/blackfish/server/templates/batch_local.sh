{% extends "base_local.sh" %}
{#
  Batch job (local profile): run a tigerflow `local` pipeline inside the
  tigerflow-ml container on the local machine. Docker or Apptainer.

  Expects context:
    name, image, provider, profile, job_config,
    pipeline_yaml, pipeline_path, input_dir, output_dir, cache_dir, idle_timeout
#}
{% block command %}
cat > {{ pipeline_path }} << 'BLACKFISH_PIPELINE_EOF'
{{ pipeline_yaml }}
BLACKFISH_PIPELINE_EOF

{%- if provider == "docker" %}
docker run --rm {{ '--runtime nvidia --gpus all' if job_config.gres else '' }} \
  -v {{ cache_dir }}:/cache \
  -v {{ input_dir }}:{{ input_dir }} \
  -v {{ output_dir }}:{{ output_dir }} \
  -v {{ pipeline_path }}:{{ pipeline_path }} \
  {{ image.docker_ref }} \
  run {{ pipeline_path }} {{ input_dir }} {{ output_dir }} \
  --idle-timeout {{ idle_timeout }}
{%- elif provider == 'apptainer' %}
export SINGULARITY_NO_EVAL=1
apptainer run {{ '--nv' if job_config.gres else '' }} \
  --env PYTHONNOUSERSITE=1 \
  --bind {{ cache_dir }}:/cache \
  --bind {{ input_dir }} \
  --bind {{ output_dir }} \
  --bind {{ pipeline_path }} \
  {{ profile.cache_dir }}/images/{{ image.sif }} \
  run {{ pipeline_path }} {{ input_dir }} {{ output_dir }} \
  --idle-timeout {{ idle_timeout }}
{%- endif %}
{%- endblock %}
