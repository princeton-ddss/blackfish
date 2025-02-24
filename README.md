# Blackfish
An open source machine learning as a service ("MLaaS") platform.

## Description
Blackfish provides a low-to-no-code solution for researchers to access and manage
machine learning "services"—machine learning models that perform specific
tasks, such as text generation, speech detection or object recognition. To use Blackfish,
a researcher selects a model that performs the ML task of interest and describes how to
run the service, i.e., which cluster to use, how many GPUs are required, etc.
Blackfish then starts an API running the model and ensures that the service is reachable.
Once the service is available, the researcher can submit requests directly to the API or
via the Blackfish user interface.

### Open Source
Blackfish is designed to run open source models and/or models for which the researcher has access to model snapshots. In the future, we may also support interactions with private services, such as ChatGPT, but our main focus is on open source models that are freely available from, e.g., the Hugging Face model hub.

### High-Performance Computing
Blackfish is geared towards researchers with access to a High-Performance
Computing (HPC) cluster (or any cluster with a Slurm job scheduler). Below, we describe
a few typical ways in which researchers might want to use it.

#### Option 1: Local-to-Remote
Researchers can install Blackfish on their laptop and interact with services running
on a remote cluster. Using this setup, a researcher starts remote services from their laptop and sends requests from their laptop to services running on the cluster. This is convenient if the researcher hasn't
transferred their data to the cluster and/or wants to collect results on their laptop. For tasks
that involve running inference on relatively large individual data points (e.g., videos), or large datasets,
the costs of transferring data across the network may make this an unattractive option.

#### Option 2: Remote-to-Remote
Instead, researchers might consider running Blackfish on the same system as
their services. There are two ways to accomplish this on an HPC cluster: either run
Blackfish on a login node, or run it on a compute node. By starting the application on a
login node, researchers can run as many *concurrent* services as they wish in separate
compute jobs. If Blackfish is run within a compute job, then all services it manages
must run on the resources requested by that job. This limits the number services that
the researcher can interact with *at the same time*, but allows the application to be
accessed from a browser if the cluster supports Open OnDemand.

#### Option 3: OnDemand
With the help of cluster administrators, Blackfish can also be setup to run via [Open OnDemand](https://openondemand.org/). This option provides users installation-free access to Blackfish. For details, see the [blackfish-ondemand](https://github.com/princeton-ddss/blackfish-ondemand) repo.

## Installation
Blackfish is a `pip`-installable python package. We recommend
installing Blackfish to its own virtual environment:
```shell
python -m venv .venv
source env/bin/activate
pip install blackfish-ml
```

For development, clone the package's repo and `pip` install:
```shell
git clone https://github.com/princeton-ddss/blackfish.git
python -m venv .venv
source env/bin/activate
cd blackfish && pip install -e .
```

To check if everything worked, type
```shell
source .venv/bin/activate
which blackfish
```
This command should return the path of the installed application.

Before you begin using Blackfish, you'll need to initialize the application. To do so, type
```shell
blackfish init
```
This command will prompt you to provide details for a Blackfish "profile". A typical default profile should look something like the following:
```toml
name: default
type: slurm
host: della.princeton.edu
user: <user_id>
home: <home_dir>/.blackfish
cache: <scratch_dir>/.blackfish
```
Additional details of profiles can be found [here](https://princeton-ddss.github.io/blackfish/getting_started/#profiles).

## Usage
There are two ways that reseachers can interact with Blackfish: in a browser, via the user
interface, or at the command-line using the Blackfish CLI. In either case, the starting
point is to type
```shell
blackfish start
```
in the command-line. This command launches the Blackfish API that both the UI and CLI interact interact with. If the API launches successfully, you should see something like the following in your terminal:
```shell
➜ blackfish start
INFO:     Added class SpeechRecognition to service class dictionary. [2025-02-24 11:55:06.639]
INFO:     Added class TextGeneration to service class dictionary. [2025-02-24 11:55:06.639]
WARNING:  Blackfish is running in debug mode. API endpoints are unprotected. In a production
          environment, set BLACKFISH_DEV_MODE=0 to require user authentication. [2025-02-24 11:55:06.639]
INFO:     Upgrading database... [2025-02-24 11:55:06.915]
WARNING:  Current configuration will not reload as not all conditions are met, please refer to documentation.
INFO:     Started server process [58591]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
```

At this point, we need to decide how we want to interact with Blackfish. The UI is available
in your browser by heading over to `http://localhost:8000`. It's large self-explanatory, so
let's instead take a look at the CLI.

### CLI
Open a new terminal tab/window. First, let's see what services are available.
```shell
blackfish run --help
```
The output displays a list of available "commands". One of these is called `text-generation`.
This is a service that generates text given a input prompt. There are a variety of models
that we might use to perform this task, so let's see what models are available to us:
```shell
blackfish model ls --image=text-generation
```

This command outputs a list of models that we can pass to the `blackfish run text-generation`
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
curl localhost:8080/generate \
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
BLACKFISH_HOST = 'localhost' # host for local instance of the Blackfish app
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


## Development

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
