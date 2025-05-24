# Developer Guide

## Setup

### SSH
Running Blackfish from your laptop to start remote services requires a seamless (i.e., password-less) method of communication with remote clusters. A simple to set up password-less login is with the `ssh-keygen` and `ssh-copy-id` utilitites.

First, make sure that you are connected to your institution's network (or VPN, if required). Then, type the following at the command-line:
```
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```
These commands create a secure public-private key pair and send the public key to the HPC server. You now have password-less access to your HPC server!

## API
Blackfish is Litestar application that is managed using the `litestar` CLI. You
can get help with `litestar` by running `litestar --help` at the command line
from within the application's home directory. Below are some of the essential
tasks.

### Litestar Commands

#### Run
```shell
litestar run  # add --reload to automatically refresh updates during development
```

#### Database
```shell
# First, check where your current migration:
litestar database show-current-revision
# Make some updates to the database models, then:
litestar database make-migration "a new migration"  # create a new migration
# check that the auto-generated migration file looks correct, then:
litestar database upgrade
```

### Configuration
The application and command-line interface (CLI) pull their settings from environment
variables and/or (for the application) arguments provided at start-up. The environment variables include:
```shell
HOST = "localhost"
PORT = 8000
STATIC_DIR = "/Users/colinswaney/GitHub/blackfish/src" # source of static files
HOME_DIR = "/Users/colinswaney/.blackfish" # source of application data
DEBUG = true # log debug statements
DEV_MODE = true # run server in development mode (no auth)
CONTAINER_PROVIDER = "docker" # determines how to launch containers
```


## Images

### Obtaining Apptainer images
Services deployed on high-performance computing systems need to be run by Apptainer
instead of Docker. Apptainer will not run Docker images directly. Instead, you need to
convert Docker images to SIF files. For images hosted on Docker Hub, running `apptainer
pull` will do this automatically. For example,

```shell
apptainer pull docker://ghcr.io/huggingface/text-generation-inference:latest
```

This command generates a file `text-generation-inference_latest.sif`. In order for
users of the remote to access the image, it should be moved to a shared cache directory,
e.g., `/scratch/gpfs/.blackfish/images`.


## Models

### Obtaining models

**Update** The recommended method to manage models is now via the `blackfish model` commands using a profile linked to the shared cache directory (make sure to use the `--use_cache` flag). This will ensure that `info.json` files are updated. If the shared cache permissions have been set properly, then there should be no need to update permissions on the newly added files.

Models should generally be pulled from the Hugging Face model hub. This can be done
by either visiting the web page for the model card or using of one Hugging Face's Python
packages. The latter is preferred as it stores files in a consistent manner in the
cache directory. E.g.,
```python
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

## UI

### Updating `build`
Blackfish ships with a copy of the built user interface so that users can run the user interface with having to install `npm`. To update the UI, you need:

1. Build the UI
Run `npm run build` in the `blackfish-ui` repo. The output of this command will be in `build/out`:
```shell
➜ tree build -d 1
build
└── out
    ├── _next
    │   ├── ssm_XfrOvugkYGVtNQ8ps
    │   └── static
    │       ├── chunks
    │       │   ├── app
    │       │   │   ├── _not-found
    │       │   │   ├── dashboard
    │       │   │   ├── login
    │       │   │   ├── speech-recognition
    │       │   │   └── text-generation
    │       │   └── pages
    │       ├── css
    │       ├── media
    │       └
```
2. Copy `blackfish-ui/build/out` to `blackfish/src/build`
```
cp -R build/out/* ~/GitHub/blackfish/src/build
```

3. Commit the change
```
git add .
git commit
# Add a useful message that includes the head of the UI, e.g.,
# Update UI to blackfish-ui@7943376
```
