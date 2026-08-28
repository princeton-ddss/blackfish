#!/bin/bash
{#
  One Ray node allocation. Joins the cluster the coordinator started on the
  login node, then blocks for the allocation's walltime. It runs no pipeline
  work of its own -- the coordinator places actors onto it -- so a single
  allocation can serve several jobs of the pipeline over its lifetime.

  Context: name, head_address, image, payload_dir, account, resources
#}
#SBATCH --job-name="{{ name }}"
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task={{ resources.cpus }}
#SBATCH --mem={{ resources.mem }}G
#SBATCH --time={{ resources.time }}
{%- if resources.gpus %}
#SBATCH --gres=gpu:{{ resources.gpus }}
{%- endif %}
{%- if resources.partition %}
#SBATCH --partition={{ resources.partition }}
{%- endif %}
{%- if resources.constraint %}
#SBATCH --constraint={{ resources.constraint }}
{%- endif %}
{%- if account %}
#SBATCH --account={{ account }}
{%- endif %}

set -euo pipefail

export APPTAINER_TMPDIR=/tmp
# Ray's object store defaults to /dev/shm, which is small on many compute
# nodes. Point its spill directory at node-local scratch instead of letting it
# fail partway through a large batch.
export RAY_TMPDIR="${TMPDIR:-/tmp}/ray-$SLURM_JOB_ID"
mkdir -p "$RAY_TMPDIR"

# Bound Ray's view of the node to what Slurm actually granted. Without this Ray
# reads the whole physical node and oversubscribes every actor placed on it.
NUM_CPUS="${SLURM_CPUS_PER_TASK:-1}"
NUM_GPUS="{{ resources.gpus or 0 }}"

RAY_ARGS=(
  --address="{{ head_address }}"
  --num-cpus="$NUM_CPUS"
  --num-gpus="$NUM_GPUS"
  --temp-dir="$RAY_TMPDIR"
  --block
)

cleanup() {
  ray stop --force || true
}
trap cleanup EXIT

{% if image -%}
apptainer exec {{ '--nv' if resources.gpus else '' }} \
  --env PYTHONNOUSERSITE=1 \
  --bind "{{ payload_dir }}" \
  --bind "$RAY_TMPDIR" \
  {{ image }} \
  ray start "${RAY_ARGS[@]}"
{%- else -%}
ray start "${RAY_ARGS[@]}"
{%- endif %}
