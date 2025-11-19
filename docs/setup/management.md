# Management Guide

This guide explains how to perform tasks to ensure that Blackfish has access to everything it needs in order to run services. If you are using Blackfish Ondemand, these steps have already been taken care of by your system admin.

If you are a system admin, or you do not have access to Blackfish Ondemand, these notes are for you.

## Architecture Overview

Blackfish consists of four components: a core REST API, a command-line interface (CLI), a browser-based user interface (UI), and a Python API. The core REST API performs all key service management operations while the Blackfish CLI and UI provide convenient methods for interacting with the Blackfish API. The Python API allows researchers to use Blackfish within Python scripts and pipelines.

The Blackfish REST API automates the process of hosting AI models as APIs. Users instruct the Blackfish API  via the CLI or UI to deploy a model and the REST API creates a "service API" running that model. The researcher that starts a service "owns" that service: she has exclusive access to its use. Blackfish tracks the status of the users' services and provides methods to stop and delete services when they are no longer needed.

In general, service APIs do not run on the same machine as the Blackfish application. Thus, when a researcher requests a model, she must specify a host for the service. The service API runs on the specifieid host and Blackfish ensures that the interface is able to communicate with the remote service API. There are several ways for researchers to setup and use Blackfish depending on their requirements. For testing and development purposes, users can run *everything* on their laptop, but his option is only practical for models with light resource requirements. Typically, users will want to run services on high-performance GPUs available on an HPC cluster with a Slurm job scheduler. In that case, researchers can run the Blackfish API on their local laptop *or* on an HPC login node.

!!! note

    Blackfish doesn't synchronize application data across machines. Services started by an instance of Blackfish running on your laptop will not show up on an HPC cluster. However, job data for services initiated by your laptop *will* be stored on the remote cluster.

![image](../assets/img/architecture-slurm.png)

**Figure** The Blackfish architecture for running remote services on a Slurm cluster.

### Application Data

Blackfish stores data in several different locations:

- Core application data is stored on the system where the Blackfish application is running (`~/.blackfish` by default).
- Profile data

## Images

Blackfish does **not** ship with the Docker (OCI) or Apptainer (SFI) container images required to run services. These images should be downloaded before running services[^1]. The current required images are:

- Text generation: `vllm/vllm-openai:v0.8.4`
- Speech recognition: `princeton-ddss/speech-recognition-inference:0.1.2`

These images are expected to change over time, so be sure to check release notes for updates.

### Obtaining Images

#### Apptainer

Services deployed on high-performance computing systems should be run with Apptainer instead of Docker. Apptainer requires Single Image Format (SIF) images instead of the Open Container Image (OCI) format used by Docker. Thus, Docker images must be converted to SIF files before Blackfish can use them. For most images—including those hosted on the GitHub container registry—running `apptainer pull` will do this automatically. For example,

```shell
apptainer pull docker://ghcr.io/princeton-ddss/speech-recognition-inference:0.1.2
```

This command generates a file `speech-recognition-inference_0.1.2.sif` in the directory where it is run. If you are setting up Blackfish for your own account, you should move this image to your home directory, `/home/shamu/.blackfish/image`. If you are setting up a shared Blackfish environment, move the image to a shared cache directory,
e.g., `/shared/.blackfish/images`.

#### Docker

For local service deployment, Docker handles file management, so you can simply pull the required image, e.g.:

```shell
docker pull vllm/vllm-openai:v0.8.4
```

## Models

### Automatic Downloads

- Blackfish will download modelsfor you
- Only support Hugging Face Model Hub

### Manual Downloads

Internally, model downloads and management are performed by `huggingface_hub`. You can download models yourself using the same method:

```python
from huggingface_hub import shapshot_download
snapshot_download(repo_id="meta-llama/Meta-Llama-3-8B")
```

The `snapshot_download` method store models files to `~/.cache/huggingface/hub/` by default. You should modify the directory by setting `HF_HOME` in the local environment or providing a
`cache_dir` argument. Otherwise, after the model files are downloaded, they must be manually moved to your home or shared (cache) directory, e.g., `/shared/.blackfish/models`. For shared models, remember to set permissions on the model directory to `755` (recursively) to allow all users read and execute access.

!!! note

    Users can only download new snapshots to `profile.home_dir`. Thus, if a model is found before running a service, then the image should look for model data in whichever cache directory the snapshot is found. Otherwise, the service should bind to `profile.home_dir` so that model files are stored there. **Users should not be given write access to `profile.cache_dir`.** If a user does *not* specify a revision, then we need to make sure that the image doesn't try to download a different revision in the case that a version of the requested model already exists in `profile.cache_dir` because this directory is assumed to be read-only and the Docker image might try to download a different revision.

[^1]: If you only intend to run services on your laptop, Blackfish will attempt to download each image automatically the first time you run its corresponding service. In this case, expect the startup time for the first run of each service type to take much longer than subsequent runs.
