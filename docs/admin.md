# Platform Administration


## Application Management
Blackfish is Litestar application that is managed using the `litestar` CLI. You
can get help with `litestar` by running `litestar --help` at the command line
from within the application's home directory. Below are some of the essential
tasks.

### Run the application
```shell
litestar run  --reload # refresh updates during development
```

### Run a database migration
First, check where your current migration:
```shell
litestar database show-current-revision
```
Make some updates to the database models, then run
```shell
litestar make-migration "a new migration"
```
to create a new migration.

Finally, check that the auto-generated migration file looks correct and run
```shell
litestar database upgrade
```

### Pull a container image

#### Apptainer
Services deployed on high-performance computing systems need to be run by Apptainer instead of Docker. Apptainer will not run Docker images directly. Instead, you need to convert Docker images to SIF files. For images hosted on Docker Hub, running `apptainer pull` will do this automatically. For example,

```shell
apptainer pull docker://ghcr.io/huggingface/text-generation-inference:latest
```

This command generates a file `text-generation-inference_latest.sif`. In order for
users of the remote to access the image, it should be moved to a shared cache directory,
e.g., `/scratch/gpfs/.blackfish/images`.

### Download a model snapshot

#### Hugging Face
Models should generally be pulled from the Hugging Face model hub. This can be done
by either visiting the web page for the model card or using of one Hugging Face's Python
packages. The latter is preferred as it stores files in a consistent manner in the
cache directory. E.g.,
```py
from transformers import pipeline
pipeline(
    task='text-generation',
    model='meta-llama/Meta-Llama-3-8B',
    token=<token>,
    revision=<revision>,

)
# or
from transformers import AutoTokenizer, AutoModelForCausalLM
tokenizer = AutoTokenizer.from_pretrained('meta-llama/Meta-Llama-3-8B')
model = AutoModelForCausalLM('meta-llama/Meta-Llama-3-8b')
# or
from huggingface_hub import shapshot_download
snapshot_download(repo_id="meta-llama/Meta-Llama-3-8B")
```
These commands store models files to `~/.cache/huggingface/hub/` by default. You can
modify the directory by setting `HF_HOME` in the local environment or providing a
`cache_dir` argument (where applicable). After the model files are downloaded, they
should be moved to a shared cache directory, e.g., `/scratch/gpfs/blackfish/models`,
and permissions on the new model directory should be updated to `755` (recursively)
to allow all users read and execute.

!!! note

    Users can only download new snapshots to `profile.home_dir`. Thus, if a model is found before running a service, then the image should look for model data in whichever cache directory the snapshot is found. Otherwise, the service should bind to `profile.home_dir` so that model files are stored there. **Users should not be given write access to `profile.cache_dir`.** If a user does *not* specify a revision, then we need to make sure that the image doesn't try to download a different revision in the case that a version of the requested model already exists in `profile.cache_dir` because this directory is assumed to be read-only and the Docker image might try to download a different revision.
