{% extends "base_slurm.sh" %}
{#
  Batch job: run a tigerflow `local` pipeline inside the tigerflow-ml container
  as a single Slurm allocation. Walltime is handled by Blackfish resubmitting
  this script (tigerflow resumes on the same output directory).

  Overrides the base `prelude` block because batch jobs need no port discovery.
  Expects context:
    uuid, name, image, profile, job_config,
    pipeline_yaml   - the rendered tigerflow pipeline config (YAML string)
    pipeline_path   - absolute path to write the config on the cluster
    input_dir, output_dir, cache_dir, idle_timeout
#}
{% block prelude %}
export APPTAINER_TMPDIR=/tmp
{%- if job_config.gres > 0 %}
export APPTAINERENV_CUDA_VISIBLE_DEVICES={{ range(job_config.gres) | join(',') }}
{%- endif %}
{% endblock %}
{% block command %}
export SINGULARITY_NO_EVAL=1

cat > {{ pipeline_path }} << 'BLACKFISH_PIPELINE_EOF'
{{ pipeline_yaml }}
BLACKFISH_PIPELINE_EOF

apptainer run {{ '--nv' if job_config.gres else '' }} \
  --env PYTHONNOUSERSITE=1 \
  --bind {{ cache_dir }}:/cache \
  --bind {{ input_dir }} \
  --bind {{ output_dir }} \
  --bind {{ pipeline_path }} \
  {{ profile.cache_dir }}/images/{{ image.sif }} \
  run {{ pipeline_path }} {{ input_dir }} {{ output_dir }} \
  --idle-timeout {{ idle_timeout }}
{%- endblock %}
