---
hide:
    - navigation
---

# Welcome to Blackfish

Blackfish is an open source "ML-as-a-Service" (MLaaS) platform that helps researchers use state-of-the-art, open source artificial intelligence and machine learning models. With Blackfish, researchers can spin up their own version of popular public cloud services (e.g., ChatGPT, Amazon Transcribe, Cloud Vision, etc.) using high-performance computing (HPC) resources already available on campus.

The primary goal of Blackfish is to facilitate **transparent** and **reproducible** research based on **open source** machine learning and artificial intelligence. We do this by providing mechanisms to run user-specified models with user-defined configurations. For academic research, open source models present several advantages over closed source models. First, whereas large-scale projects using public cloud services might cost $10K to $100K for [similar quality results](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1210559/full), open source models running on HPC resources are free to researchers. Second, with open source models you know *exactly* what model you are using and you can easily provide a copy of that model to other researchers. Closed source models can and do change without notice. Third, using open-source models allows complete transparency into how *your* data is being used.

## Why should you use Blackfish?

### 1. It's easy! 🌈

Researchers should focus on research, not tooling. We try to meet researchers where they're at by providing multiple ways to work with Blackfish, including a Python API, a command-line tool (CLI), and a browser-based user interface (UI).

Don't want to install a Python package? Ask your HPC admins to install [Blackfish OnDemand](https://github.com/princeton-ddss/blackfish-ondemand)!

### 2. It's transparent 🧐

You decide what model to run (down to the Git commit) and how you want it configured. There are no unexpected (or undetected) changes in performance because the model is always the same. All services are *private*, so you know exactly how your data is being handled.

### 3. It's free! 💸

You have an HPC cluster. We have software to run on it.

## Requirements

### Python

Blackfish requires Python to run locally. Alternatively, Blackfish can be added to your university's [Open OnDemand](https://openondemand.org/) portal, which allows users to run applications on HPC resources through a web browser. For more information, see our companion repo [blackfish-ondemand](https://github.com/princeton-ddss/blackfish-ondemand).

### Docker & Apptainer

Blackfish uses Docker or Apptainer to run service containers locally. HPC-based services require Apptainer to be installed on your university cluster.

## Quickstart

### Step 1 - Install blackfish

```shell
pip install blackfish-ai
```

### Step 2 - Create a profile

```shell
blackfish init

# Example responses
# > name: default
# > type: slurm
# > host: cluster.organization.edu
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /shared/.blackfish
```

### Step 3 - Start the API

```shell
blackfish start
```

### Step 4 - Obtain a model

```shell
blackfish model add --profile default openai/whisper-large-v3  # This will take a minute...
```

### Step 5 - Run a service

```shell
blackfish run --mount $HOME/Downloads speech-recognition openai/whisper-large-v3
```

### Step 6 - Submit a request

```shell
# First, check the service status...
blackfish ls

# Once the service is healthy...
curl -X POST 'http://localhost:8080/transcribe' -H 'Content-Type: application/json' -d '{"audio_path": "/data/audio/NY045.mp3", "response_format": "json"}'
```

## Next Steps

Ready to give Blackfish a try? Check out our [setup guide](setup/installation.md).

## Acknowledgements

Blackfish is maintained by research software engineers at Princeton University's [Data Driven Social Science Initiative](https://ddss.princeton.edu/).
