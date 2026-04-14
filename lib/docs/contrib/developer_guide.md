# Developer Guide

## Setup

### uv
`uv` is optional, but highly recommended. To install Blackfish for development with `uv` run:
```
git clone https://github.com/princeton-ddss/blackfish.git
cd blackfish
uv sync
```

### pre-commit
You should install the `pre-commit` script: `uv run pre-commit install`.

### just
Development tasks run through a `justfile` in `lib/`. From that directory, use `just lint` (pre-commit), `just test` (pytest + coverage), `just coverage` (refresh the coverage badge), or `just docs` (build the MkDocs site).

### ssh
Running Blackfish from your laptop to start remote services requires a seamless (i.e., password-less) method of communication with remote clusters. A simple to set up password-less login is with the `ssh-keygen` and `ssh-copy-id` utilitites.

First, make sure that you are connected to your institution's network or VPN, if required. Then, type the following at the command-line:
```
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```
These commands create a secure public-private key pair and send the public key to the HPC server. You now have password-less access to your HPC server!

### Apptainer
Services deployed on high-performance computing systems need to be run by Apptainer
instead of Docker. Apptainer will not run Docker images directly. Instead, you need to
convert Docker images to SIF files. For images hosted on Docker Hub, running `apptainer
pull` will do this automatically. For example,

```shell
apptainer pull docker://vllm/vllm-openai:v0.10.2
```

This command generates a file `vllm-openai_v0.10.2.sif`. In order for
users of the remote to access the image, it should be moved to a shared cache directory,
e.g., `/scratch/gpfs/.blackfish/images`.

## API Development
Blackfish is a Litestar application that is managed using the `litestar` CLI. You
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
DEBUG = true # run server in development mode (no auth)
CONTAINER_PROVIDER = "docker" # determines how to launch containers
```

### UI Updates
The backend ships with a pre-built copy of the UI so users don't need `npm` installed to run Blackfish. To update it, run `npm run build:lib` from `web/`. This builds the UI with Vite and copies the output to `lib/src/blackfish/build/`. Commit the resulting build tree alongside your source changes.
