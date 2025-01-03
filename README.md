# Blackfish
An open source machine learning as a service ("MLaaS") platform.

## Description
Blackfish provides a low-to-no-code solution for researchers to access and manage
machine learning "services"—machine learning models that perform specific
tasks, such as text generation, image classification, speech detection, etc. With
Blackfish, a researcher that needs to perform an ML task can start a service to perform
the task by choosing from a list of available models. Blackfish will start an API
running that model and ensure that the service is reachable. Once the service is
up an running, researchers can submit requests through the command line, user interface,
or directly to the API. The researcher can change the service (i.e., switch models), start
another service or stop services as needed.

### HPC Clusters
Blackfish is geared towards academic researchers with access to a High Performance
Computing (HPC) cluster (or any cluster with a Slurm job scheduler). Below, we describe
a few typical ways in which researchers might want to use it.

#### Option 1: Local Mode
Researchers can install Blackfish on their laptop and interact with services running
on a remote cluster. Under this setup, the researcher can pass data from their laptop to
requests to services running on the cluster. This is convenient if the researcher hasn't
transferred their data to the cluster and wants to collect results on their laptop. For tasks
that involve running inference on relatively large individual data points (e.g., videos),
the costs of transferring data across the network may be prohibitive for large datasets.

#### Option 2: Remote Mode
In that case, researchers might want to consider running Blackfish on the same system as
their services. There are two ways to accomplish this on an HPC cluster: either run
Blackfish on a login node, or run it on a compute node. By starting the application on a
login node, researchers can run as many *concurrent* services as they wish in separate
compute jobs. If Blackfish is run within a compute job, then all services it manages
must run on the resources requested by that job. This limits the number services that
the researcher can interact with *at the same time*, but allows the application to be
accessed from a browser if the cluster supports Open OnDemand.

## Installation
Blackfish is a `pip`-installable python package. To keep things clean, we recommend
installing Blackfish to its own environment:
```shell
python -m venv env
source env/bin/activate
pip install blackfish
```

For development, clone the package's repo and pip install:
```shell
git clone ...
python -m venv env
source env/bin/activate
cd blackfish && pip install -e .
```

## Usage
Their are two ways that reseachers can interact with Blackfish: in a browser, via the user
interface, or at the command-line using the Blackfish CLI. In either case, the starting
point is to type
```shell
blackfish start
```
in the command-line. If this is your first time starting the application, then you'll need
to answer a few prompts to set things up. Once you're setup, the application will launch.
At this point, we need to decide how we want to interact with Blackfish. The UI is available
in your browser by heading over to `http://127.0.0.1:8000`. It's large self-explanatory, so
let's instead take a look at the CLI.

### CLI
Open a new terminal tab/window. First, let's see what type of services are available.
```shell
blackfish run --help
```
This command displays a list of available commands. One of these is called `text-generate`.
This is a service that generates text given a input prompt. There are a variety of models
that we might use to perform this task, so let's check out what's available on Blackfish:
```shell
blackfish image ls --filter name=text-generate
```

This command returns a list of models that we can pass to the `blackfish run text-generate`
command. One of these should be `bigscience/bloom560m`. (The exact list you see will depend
on your application settings/deployment). Let's spin it up:
```shell
blackfish run --profile hpc text-generation --model bigscience/bloom-560m
```

The CLI returns an ID for our new service. We can find more information about our
service by running

```shell
blackfish ls
blackfish ls --filter id=<service_id>
```

In this case, `--profile hpc` was setup to connect to a (remote) HPC cluster, so the
service will be run as a Slurm job. It might take a few minutes for a Slurm job to start,
and it will take some time for the service to setup after the job starts. Until then, our
service's status will be either `SUBMITTED` or `STARTING`. Now would be a good time to make some
tea...

While you're doing that, note that if you ever want more detailed information about
a service, you can get that with the `blackfish details <service_id>` command. Back to
that tea...

Now that we're refreshed, let's see how our service is doing. Re-run the command above.
If things went well, then we should see that the service's status has changed to `RUNNING`.
At this point, we can start interacting with the service. Let's say "Hello":

```shell
curl 127.0.0.1:8080/generate \
  -X POST \
  -d '{"inputs": "Hello", "parameters": {"max_new_tokens": 20}}' \
  -H 'Content-Type: application/json'
```
*TODO* demonstrate how to reach the service via `blackfish fetch`.

When we are done with our service, we should shut it off and return its resources to the
cluster. To do so, simply type
```shell
blackfish stop <service_id>
```

If you check that service's status, you'll see that it is now `STOPPED`. The service will
remain in your services list until you delete it:
```shell
blackfish rm <service_id>
```

### Configuration

#### SSH Setup
Using Blackfish from your laptop requires a seamless (i.e., password-less) method of
communicating with remote clusters. This is simple to setup with the `ssh-keygen` and
`ssh-copy-id` utilitites. First, make sure that you are connected to your institution's
network (or VPN), then type the following at the command-line:
```
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```
These commands create a secure public-private key pair and send the public key to the HPC
server you need access to. You now have password-less access to your HPC server!

### Model Selection
Every service should specify at least one "recommended" model. Admins will
download these models to a directory that users assign as `profile.cache_dir` and
which is public read-only.

Available models are stored in the application database. The availability of a model
is based on whether the model has at least one snapshot directory on a given remote.
To find available models, we look for snapshots in `profile.cache_dir`, then `profile.home_dir`.
On application startup, we compare the application database with the files found
on each remote and update accordingly.

| model                  | revision     | profile | ... |
| ---------------------- | ------------ | ------- | --- |
| bigscience/bloom-560m  | e32fr9l...   | della   | ... |

When a user requests a service, we first check if the model is available. If not, then we
warn the user that it will require downloading the model files to their `profile.home_dir`
and make sure that the job uses `profile.home_dir` instead of `profile.cache_dir` for
model storage. After a service launches, we check whether the model is present in the database and,
if not, update the database.

From the CLI, you can list available (downloaded) models for a given profile with
```
blackfish models ls --profile della --refresh
```

Behind the scenes, this command calls the API endpoint:
```
GET /models/?profile=della&refresh=true
```

The `refresh` option tells Blackfish to confirm availability by directly accessing the remote's cache directories; omitting the refresh option tells Blackfish to return the list of models found in its database, which might differ if a model was added since the last time the database was refreshed.

#### Snapshot Storage
Users can only download new snapshots to `profile.home_dir`. Thus, if a model is found
before running a service, then the image should look for model data in whichever cache directory
the snapshot is found. Otherwise, the service should bind to `profile.home_dir` so that
model files are stored there. **Users should not be given write access to `profile.cache_dir`.**
If a user does *not* specify a revision, then we need to make sure that the image
doesn't try to download a different revision in the case that a version of the requested model
already exists in `profile.cache_dir` because this directory is assumed to be read-only and
the Docker image might try to download a different revision.


## Management
Blackfish is Litestar application that is managed using the `litestar` CLI. You
can get help with `litestar` by running `litestar --help` at the command line
from within the application's home directory. Below are some of the essential
tasks.

### Run the application
```shell
litestar run  # add --reload to automatically refresh updates during development
```

### Run a database migration
```shell
# First, check where your current migration:
litestar database show-current-revision
# Make some updates to the database models, then:
litestar make-migration "a new migration"  # create a new migration
# check that the auto-generated migration file looks correct, then:
litestar database upgrade
```

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

### Obtaining models
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

### Configuration
The application and command-line interface (CLI) pull their settings from environment
variables and/or (for the application) arguments provided at start-up. The most important
environment variables are:
```shell
BLACKFISH_HOST = '127.0.0.1' # host for local instance of the Blackfish app
BLACKFISH_PORT = 8000 # port for local instance of the Blackfish app
BLACKFISH_HOME_DIR = '~/.blackfish' # location to store application data
```

### Profiles
The CLI uses "profiles.cfg" to store details of environments where Blackfish has been setup.
Generally, Blackfish will be setup up on a local environment, i.e., a laptop, as well
as a remote environment, e.g., an HPC cluster. When running commands, you can tell the
CLI which of these environments to use with the `--profile` option. For example, you might
start a service on a remote HPC cluster like so:
```
blackfish run --profile hpc ...
```

This command tells the *local* CLI to start a service using the information stored in the
`hpc` profile. The `hpc` profile might look something like this:
```
[hpc]
type='slurm'
host='<cluster>.<university>.edu'
user='<user>'
home_dir='/home/<user>/.blackfish'
cache_dir='/scratch/gpfs/<user>/'
```

The `type` field indicates that this profile corresponds to an HPC cluster running the
Slurm job manager. Services started with this profile will have their `job_type` set to
`slurm` and use the `host`, `user`, 'home_dir' and 'cache_dir' specified in the profile.

As another example, consider the command:
```
blackfish start --profile hpc
```

This command tells Blackfish to start an application on the remote system specified by the
`hpc` profile. Blackfish will pass the profile's `home_dir` and `cache_dir` values to the
apps configuration.

Profiles are stored in `~/.blackfish/profiles.cfg` and can be modified using the CLI commands
`blackfish profile create`, `blackfish profile delete`, and `blackfish profile update`,
or by directly modifying the file.

#### Remotes
Blackfish makes many calls to remote servers. You'll want to have a system setup to avoid entering your credentials for those servers each time. For HPC clusters, SSH keys should do
the trick. Setting up SSH keys is as simple as running the following on your local (macOS or Linux) machine:
```
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```
