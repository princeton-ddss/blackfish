{% block sbatch %}
#!/bin/bash

#SBATCH --job-name={{ job_config.name }}
#SBATCH --nodes={{ job_config.nodes }}
#SBATCH --ntasks-per-node={{ job_config.ntasks_per_node }}
#SBATCH --mem={{ job_config.mem }}G
#SBATCH --time={{ job_config.time }}
#SBATCH --gres=gpu:{{ job_config.gres }}
{%- if 'constraint' in job_config %}
#SBATCH --constraint={{ job_config.constraint }}
{% endif %}
{%- if 'partition' in job_config %}
#SBATCH --partition={{ job_config.partition }}
{% endif %}
{%- endblock %}
{% block prelude %}
export APPTAINER_CACHEDIR={{ app_config.apptainer_cache }}
export APPTAINER_TMPDIR={{ app_config.apptainer_tmpdir }}
{% raw %}
port=$(comm -23 <(seq 8080 8899 | sort) <(ss -Htan | awk '{{print $4}}' | cut -d':' -f2 | sort -u) | shuf | head -n 1)
{% endraw %}
mkdir {{ app_config.remote }}/$SLURM_JOB_ID
mkdir {{ app_config.remote }}/$SLURM_JOB_ID/$port
{% endblock %}
{%- block command %}
{% endblock %}