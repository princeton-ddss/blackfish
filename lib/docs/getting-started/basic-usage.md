# Basic Usage

## Requirements

- **Python 3.12+**
- **Docker or Apptainer** — Blackfish runs services inside containers. HPC-based services require Apptainer to be installed on your university cluster.
- **Container images** — Blackfish does not ship container images. Your HPC admin may provide these in a shared cache directory, or you can [add them yourself](../admin/management.md#images).

## Quickstart

Here's what the typical Blackfish workflow looks like on an HPC cluster:

### Step 1 - Install Blackfish

```shell
python -m venv .venv
source .venv/bin/activate
pip install blackfish-ai
```

### Step 2 - Create a profile

```shell
blackfish init

# Example responses
# > name: default
# > type: slurm
# > host: localhost
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /scratch/gpfs/shared/.blackfish
```

### Step 3 - Start Blackfish

```shell
blackfish start
```

### Step 4 - Obtain a model

```shell
blackfish model add TinyLlama/TinyLlama-1.1B-Chat-v1.0  # This will take a minute...
```

### Step 5 - Run a service

```shell
blackfish run --gres 1 --time 00:30:00 text-generation TinyLlama/TinyLlama-1.1B-Chat-v1.0 --api-key sealsaretasty
```

### Step 6 - Submit a request

```shell
# First, check the service status...
blackfish ls

# Once the service is healthy...
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sealsaretasty" \
  -d '{
        "messages": [
            {"role": "system", "content": "You are an expert marine biologist."},
            {"role": "user", "content": "Why are orcas so awesome?"}
        ],
        "max_completion_tokens": 100,
        "temperature": 0.1,
        "stream": false
    }' | jq
```