# Cache Management

Blackfish stages container images and model files into a
profile's cache before services and batch jobs can run.

## Storage locations

Blackfish stores data in several different locations:

- Core application data is stored in `BLACKFISH_HOME_DIR` on the system where Blackfish is running (`~/.blackfish` by default). Core application data includes profile configuration, application logs, and database storage.
- Models and images are stored in the user-defined locations `home_dir` and `cache_dir`. These are profile-specific locations that need not reside on the machine where Blackfish is running. `home_dir` also stores job files created each time a service launches.

## Images

Blackfish does **not** ship with the container images required to run services and batch jobs. These images should be downloaded before use[^1]. To see the images required by your installed version of Blackfish, run:

```shell
blackfish image ls
```

This lists each pinned image — one per service, plus the tigerflow-ml image used for batch jobs — and whether it is available in the configured cache. Pinned versions change over time as Blackfish releases bump the underlying runtimes.

### Obtaining Images

Services deployed on HPC systems require Apptainer, which uses Single Image Format (SIF) images instead of Docker's OCI format. Docker images must be converted to SIF files before Blackfish can use them. For most images—including those hosted on the GitHub container registry—running `apptainer pull` will do this automatically. For example,

```shell
apptainer pull docker://ghcr.io/princeton-ddss/speech-recognition-inference:<tag>
```

This command generates a file `speech-recognition-inference_<tag>.sif` in the directory where it is run. Use the version reported by `blackfish image ls`. The tigerflow-ml image used for batch jobs is staged the same way:

```shell
apptainer pull docker://ghcr.io/princeton-ddss/tigerflow-ml:<tag>
```

Blackfish looks for images in the `cache_dir/images` directory specified by your profile. If you are an HPC admin setting up a shared environment, move images to the shared cache directory (e.g., `/shared/.blackfish/images`). If you are an individual user and your cache directory is read-only, ask your admin to add the required images or set your profile's `cache_dir` to a directory you can write to.

## Models

### Hugging Face Authentication

Some models on Hugging Face are "gated" and require authentication to download. You can create access tokens on the [Hugging Face security tokens](https://huggingface.co/docs/hub/en/security-tokens) page. Blackfish uses the [`huggingface_hub`](https://github.com/huggingface/huggingface_hub) library, which automatically detects authentication tokens from:

1. The `HF_TOKEN` environment variable
2. A token stored at `~/.cache/huggingface/token` (set via `huggingface-cli login`)

#### Setting a Token via Environment Variable

You can set the `HF_TOKEN` environment variable:

```shell
export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Add this to your shell profile (`.bashrc`, `.zshrc`, etc.) for persistence.

#### Setting a Token via CLI

You can also use the Hugging Face CLI:

```shell
huggingface-cli login
```

This stores the token at `~/.cache/huggingface/token`.

### Automatic Downloads

You can download models with the `blackfish model add` command. Blackfish stores downloaded models in the `home_dir` of the specified profile by default. If you are downloading models to share with other users, add the `--use-cache` flag to save files to the `cache_dir` instead. Model download support is currently limited to Slurm profiles configured with `host=localhost` (e.g. Blackfish running on the cluster head node, such as within an Open OnDemand session). To download models for use on a remote Slurm cluster, you need to run Blackfish on the cluster itself.

### Manual Downloads

Internally, model downloads and management are performed by [`huggingface_hub`](https://github.com/huggingface/huggingface_hub). You can download models yourself using the same method:

```python
from huggingface_hub import snapshot_download
snapshot_download(repo_id="meta-llama/Meta-Llama-3-8B")
```

The `snapshot_download` method stores model files to `~/.cache/huggingface/hub/` by default. You should modify the directory by setting `HF_HOME` in the local environment or providing a `cache_dir` argument. Otherwise, after the model files are downloaded, they must be manually moved to your home or shared (cache) directory, e.g., `/shared/.blackfish/models`. For shared models, remember to set permissions on the model directory to `755` (recursively) to allow all users read and execute access.

!!! note

    In addition to downloading model files, the `blackfish model add` command extracts metadata from the model and adds it to an internal database of models available to the profile that was used to add the model. Manually added models will not show up when running `blackfish model ls` (because they are not added to this database), but Blackfish will still be able to discover and run these models.

## Batch Jobs

Blackfish runs batch jobs inside the [tigerflow-ml](https://github.com/princeton-ddss/tigerflow-ml) container image, a companion project for running task-based pipelines on Slurm clusters. Like service images, the tigerflow-ml image must be available in the profile's cache — see [Images](#images) for how to stage it. Once the image is present, any Slurm profile can run batch jobs; `blackfish profile repair` verifies the image is in place.
