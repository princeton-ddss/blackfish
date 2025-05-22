{% block sbatch -%}
#!/bin/bash

#SBATCH --job-name={{ name }}
#SBATCH --nodes={{ job_config.nodes }}
#SBATCH --ntasks-per-node={{ job_config.ntasks_per_node }}
#SBATCH --mem={{ job_config.mem }}G
#SBATCH --time={{ job_config.time }}
{%- if job_config.gres %}
#SBATCH --gres=gpu:{{ job_config.gres }}
{%- endif %}
{%- if job_config.constraint %}
#SBATCH --constraint={{ job_config.constraint }}
{%- endif %}
{%- if job_config.partition %}
#SBATCH --partition={{ job_config.partition }}
{%- endif %}
{%- endblock %}
{% block prelude %}
export APPTAINER_CACHEDIR=/scratch/gpfs/{{ profile.user }}/APPTAINER_CACHE
export APPTAINER_TMPDIR=/tmp
{% raw %}
port=$(comm -23 <(seq 8080 8899 | sort) <(ss -Htan | awk '{{print $4}}' | cut -d':' -f2 | sort -u) | shuf | head -n 1)
{% endraw %}
mkdir {{ profile.home_dir }}/jobs/{{ uuid }}/$SLURM_JOB_ID
mkdir {{ profile.home_dir }}/jobs/{{ uuid }}/$SLURM_JOB_ID/$port
{% endblock %}
{%- block command %}
{% endblock %}
