# Getting Started

## Installation

### pip
```shell
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install blackfish
```

If everything worked, `which blackfish` should point to the installed command-line tool.

## Setup
There's a small amount of setup required before we get started with Blackfish. Fortunately,
it's mostly automated.

### SSH
Using Blackfish from your laptop requires a seamless (i.e., password-less) method of communicating
with remote clusters. On many systems, this is simple to setup with the `ssh-keygen` and
`ssh-copy-id` utilitites. First, make sure that you are connected to your institution's network
(or VPN), then type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC
server you need access to. You now have password-less access to your HPC server!

!!! warning

    Blackfish depends on seamless interaction with your university's HPC cluster. Before proceeding,
    make sure that you have enabled password-less login and are connected to your institutions
    network or VPN, if required.

### Initialization
To initialize Blackfish, just type
```shell
blackfish init
```
and answer the prompts to create a new default profile.

!!! note

    If your default profile connects to an HPC cluster, then Blackfish will attempt to set up
    the remote host at this point. Profile creation will fail if you're unable to connect to the HPC
    server and you'll need to re-run the `blackfish init` command or create a profile with
    `blackfish profile create` (see below).


### Models and Images
Blackfish works best with locally available model files and container images. Having these files
available locally allows Blackfish to avoid slow downloads during deployment. See the section on
[Obtaining Service Images and Models]() for more information, or talk to your institution's HPC
cluster admins.

### Configuration
The application and command-line interface (CLI) pull their settings from environment
variables and/or (for the application) arguments provided at start-up. The most important
environment variables are:
```shell
BLACKFISH_HOST = '127.0.0.1' # host for local instance of the Blackfish app
BLACKFISH_PORT = 8000 # port for local instance of the Blackfish app
BLACKFISH_HOME_DIR = '~/.blackfish' # location to store application data
BLACKFISH_DEV_MODE = 1 # run the application with development settings
```

Running the application in development mode is recommended for development only on a shared system
as it does not use authentication.

### Profiles
The `blackfish profile` command provides methods for managing Blackfish profiles. Profiles
are useful if you have access to multiple HPC resources or have multiple accounts on an HPC server.
Each profile consists of some combination of the following attributes, depending on the profile
type.

!!! tip

    Blackfish profiles are stored in `$BLACKFISH_HOME/profiles.cfg`. On Linux, this is
    `$HOME/.blackfish/profile` by default. You can modify this file directly, if needed, but you'll
    need to need setup any required remote resources by hand.

#### Types
Each profile specifies a number of attributes that allow Blackfish to find resources (e.g., model
files) and deploy services accordingly. The exact attributes depend on the profile *type*. There are currently two profile types: `LocalProfile` ("local") and `SlurmRemote` ("slurm"). All profiles require the following attributes:

- `name`: the unique profile name. The "default" profile is used by Blackfish when a profile isn't
explicitly provided.
- `type`: one of "slurm" or "local". The profile type determines how services associated with this
profile are deployed by Blackfish. Use "slurm" if this profile will run jobs on HPC and "local" to
run jobs on your laptop (or wherever Blackfish is installed).

The additional attribute requirements for specific types are listed below.

##### Slurm (Remote)
A remote Slurm profile specifies how to schedule services *on* a a remote server (e.g., HPC cluster) running Slurm *from* a local machine.

- `host`: a HPC server to run services on, e.g. `<cluster>@<university>.edu`.
- `user`: a user name on the HPC server.
- `home`: a location on the HPC server to store application data, e.g., `/home/<user>/.blackfish`
- `cache`: a location on the HPC server to store additional (typically shared) model images and
files. Blackfish does **not** attempt to create this directory for you, but it does require that it can be found.

##### Slurm (Local)
A local Slurm profile specifies how to schedule services *on* a cluster running Slurm *from* the cluster. This is useful if your cluster provides a login node where it is permissible to execute  long-running, low-resource programs.


- `user`: a user name on the HPC server.
- `home`: a location on the HPC server to store application data, e.g., `/home/<user>/.blackfish`
- `cache`: a location on the HPC server to store additional (typically shared) model images and
files. Blackfish does **not** attempt to create this directory for you, but it does require that it can be found.

##### Local
A local profile specifies how to run services on a local machine, i.e., your laptop or desktop. This is useful for development and for running models that do not require large amounts of resource, especially if the model is able to utilize a GPU on your local machine.

- `home`: a location on the local machine to store application data, e.g., `/home/<user>/.blackfish`
- `cache`: a location on the local machine to store additional (typically shared) model images and
files. Blackfish does **not** attempt to create this directory for you, but it does require that it can be found.

#### Commands

##### ls - List profiles
To view all profiles, type
```shell
blackfish profile ls
```

##### add - Create a profile
Creating a new profile is as simple as typing
```shell
blackfish profile add
```

and following the prompts (see attribute descriptions above). Note that profile names
are unique.

##### show - View a profile
You can view a list of all profiles with the `blackfish profile ls` command. If you want to view a
specific profile, use the `blackfish profile show` command instead, e.g.

```shell
blackfish profile show --name <profile>
```

Leaving off the `--name` option above will display the default profile, which is used by most
commands if no profile is explicitly provided.

##### update - Modify a profile
To modify a profile, use the `blackfish profile update` command, e.g.

```shell
blackfish profile update --name <profile>
```
This command updates the default profile if not `--name` is specified. Note that you cannot change
the name or type attributes of a profile.

##### rm - Delete a profile
To delete a profile, type `blackfish profile rm --name <profile>`. By default, the command
requires you to confirm before deleting.


## Usage
Once you've initialized Blackfish and created a profile, you're ready to go. Their are two ways ways
to interact with Blackfish: in a browser, via the user interface (UI), or at the command-line using
the Blackfish CLI. In either case, the entrypoint is to type
```shell
blackfish start
```
in the command-line. If everything worked, you should see a message stating the application
startup is complete.

At this point, we need to decide how we want to interact with Blackfish. The UI is available in your
browser by heading over to `http://127.0.0.1:8000`. It's a relatively straight-forward interface,
and we have detailed usage examples on the [user interface page](), so let's instead take a look at
the CLI.

Open a new terminal tab or window. First, let's see what type of services are available.
```shell
❯ blackfish run --help

 Usage: blackfish run [OPTIONS] COMMAND [ARGS]...

 Run an inference service.
 The format of options approximately follows that of Slurm's `sbatch` command.

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --time                 TEXT     The duration to run the service for, e.g., 1:00 (one hour).               │
│ --ntasks_per_node      INTEGER  The number of tasks per compute node.                                     │
│ --mem                  INTEGER  The memory required per compute node in GB, e.g., 16 (G).                 │
│ --gres                 INTEGER  The number of GPU devices required per compute node, e.g., 1.             │
│ --partition            TEXT     The HPC partition to run the service on.                                  │
│ --constraint           TEXT     Required compute node features, e.g., 'gpu80'.                            │
│ --profile          -p  TEXT     The Blackfish profile to use.                                             │
│ --help                          Show this message and exit.                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ────────────────────────────────────────────────────────────────────────────────────────────────╮
│ speech-recognition  Start a speech recognition service hosting MODEL with access to INPUT_DIR on the      │
│                     service host. MODEL is specified as a repo ID, e.g., openai/whisper-tiny.             │
│ text-generation     Start a text generation service hosting MODEL, where MODEL is specified as a repo ID, │
│                     e.g., openai/whisper-tiny.                                                            │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
This command displays a list of available sub-commands. One of these is `text-generation`, which is
a service that generates text given an input prompt. There are a variety of models that we might use
to perform this task, so let's check out what's available on our setup.

### Models

#### Commands

##### `add` - Download a model

##### `rm` - Delete a model

##### `ls` - List available models
```shell
❯ blackfish model ls
REPO                                   REVISION                                   PROFILE   IMAGE
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   default   speech-recognition
openai/whisper-tiny                    be0ba7c2f24f0127b27863a23a08002af4c2c279   default   speech-recognition
openai/whisper-small                   973afd24965f72e36ca33b3055d56a652f456b4d   default   speech-recognition
bigscience/bloom-560m                  ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971   default   text-generation
meta-llama/Meta-Llama-3-70B            b4d08b7db49d488da3ac49adf25a6b9ac01ae338   macbook   text-generation
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   macbook   speech-recognition
bigscience/bloom-560m                  4f42c91d806a19ae1a46af6c3fb5f4990d884cd6   macbook   text-generation
```
As you can see, we have a number of models available.[^1] Notice that `bigscience/bloom-560m` is
listed twice. The first listing refers to a specific version of this model—
`ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971`—that is available to the `default` profile; the second
listing refers to a different version ("revision") of the same model—
`4f42c91d806a19ae1a46af6c3fb5f4990d884cd6`—that is available to the `macbook` profile. For
reproducibility, it's important to keep track of the exact revision used.

[^1]: The list of models you see will depend on your environment. If you do not have access to a
shared HPC cache, your list of models is likely empty. Not to worry—we will see how to add models
later on.

Let's go ahead and try to run one of these models.

### Services

#### Commands

##### `run` - Start a service
Looking back at the help message for `blackfish run`, we see that there are a few items that we
should provide. First, we need to select the type of service to run. We've already decide to run
`text-generation`, so we're good there. Next, there are a number of job options that we can provide.
With the exception of `profile`, job options are based on the Slurm `sbatch` command and tell
Blackfish the resources required to run a service. Finally, there are a number of "container
options" available. To get a list of these, type `blackfish run text-generation --help`:

```shell
❯ blackfish run text-generation --help

 Usage: blackfish run text-generation [OPTIONS] MODEL

 Start a text generation service hosting MODEL, where MODEL is specified as a repo ID, e.g.,
 openai/whisper-tiny.
 See https://huggingface.co/docs/text-generation-inference/en/basic_tutorials/launcher for
 additional option details.

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --name                    -n  TEXT     Assign a name to the service. A random name is assigned   │
│                                        by default.                                               │
│ --revision                -r  TEXT     Use a specific model revision. The most recent locally    │
│                                        available (i.e., downloaded) revision is used by default. │
│ --disable-custom-kernels               Disable custom CUDA kernels. Custom CUDA kernels are not  │
│                                        guaranteed to run on all devices, but will run faster if  │
│                                        they do.                                                  │
│ --sharded                     TEXT     Shard the model across multiple GPUs. The API uses all    │
│                                        available GPUs by default. Setting to 'true' with a       │
│                                        single GPU results in an error.                           │
│ --max-input-length            INTEGER  The maximum allowed input length (in tokens).             │
│ --max-total-tokens            INTEGER  The maximum allowed total length of input and output (in  │
│                                        tokens).                                                  │
│ --dry-run                              Print the job script but do not run it.                   │
│ --help                                 Show this message and exit.                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```
The most important of these is the `revision`, which specifies the exact version of the model we
want to run. By default, Blackfish selects the most recent locally available version. This container
option (as well as `--name`) is available for *all* tasks: the remaining options are task-specific.

We'll choose `bigscience/bloom-560m` for the required `MODEL` argument, which we saw earlier is
available to the `default` and `macbook` profiles. This is a relatively small model, but we still
want to ask for a GPU to speed things up. Putting it altogether, here's a command to start our
service:
```shell
❯ blackfish run \
  --mem 16 \
  --ntasks_per_node 4 \
  --gres 1 \
  --time 00:05 \
  text-generation \
  bigscience/bloom-560m
✔ Found 5 models.
✔ Found 1 snapshots.
✔ Found model bigscience/bloom-560m[ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971] in /scratch/gpfs/ddss/.blackfish/models.
⚠ No revision provided. Using latest available commit ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971.
✔ Started service: fddefdaf-d9d2-4392-82d8-c3c4fd2588c6
```
What just happened? First, Blackfish checked to make sure that the requested model is available to
the `default` profile. Next, it found a list of available revisions of the model and selected the
most recently published version because no revision was specified. Finally, it sent a request to
deploy the model. Helpfully, the CLI returned an ID associated with the new service
`fddefdaf-d9d2-4392-82d8-c3c4fd2588c6`, which we can use get information about our service via the
`blackfish ls` command.

!!! note

    If no `--revision` is provided, Blackfish automatically suggests the most recently
    available *downloaded* version of the requested model. This reduces the
    time-to-first-inference, but may not be desirable for your use case. Download the
    model *before* starting your service if you need the [most recent version]() available
    on Hugging Face.

!!! tip

    Add the `--dry-run` flag to preview the start-up script that Blackfish will submit.

##### `ls` - List services
To view a list of your Blackfish services, type
```shell
❯ blackfish ls # --filter id=<service_id>,status=<status>
SERVICE ID                             IMAGE             MODEL                         CREATED                       UPDATED                       STATUS    PORTS   NAME              PROFILE   MOUNTS
12bb9574-28a8-4cdd-80a4-ad8430bd8d82   text_generation   meta-llama/Meta-Llama-3-8B    2024-07-31T15:16:32.825331Z   2024-07-31T15:30:03.860402Z   TIMEOUT   None    blackfish-10205   default
9c128c84-a908-4f17-995d-5780b2c0895d   text_generation   meta-llama/Meta-Llama-3-70B   2024-08-01T15:37:46.345488Z   2024-08-01T15:40:13.828408Z   FAILED    None    blackfish-12575   macbook
fddefdaf-d9d2-4392-82d8-c3c4fd2588c6   text_generation   bigscience/bloom-560m         2024-08-27T20:00:53.553854Z   2024-08-27T20:00:53.553864Z   PENDING   None    blackfish-11753   default
```
The last item in this list is the service we just started. In this case, the `default` profile
happens to be set up to connect to a remote HPC cluster, so the service is run as a Slurm job. It
may take a few minutes for our Slurm job to start, and it will require additional time for the
service to be ready after that. Until then, our service's status will be either `SUBMITTED`,
`PENDING` or `STARTING`. Now would be a good time to brew a hot beverage ☕️.

!!! tip

    If you ever want more detailed information about a service, you can get it with the
    `blackfish details <service_id>` command. Again, `--help` is your friend if you want more
    information.

Now that we're refreshed, let's see how our service is doing. Re-run the command above. If things
went smoothly, then we should see that the service's status has changed to `HEALTHY` (if your
service is still `STARTING`, give it another minute and try again). At this point, we can start
interacting with the service. Let's say "Hello", shall we?

The details of calling a service depend on the service you are trying to connect to. For the
`text-generation` service, the primary endpoint is accessed like so:
```shell
❯ curl 127.0.0.1:8080/generate \
  -X POST \
  -d '{"inputs": "Hello!", "parameters": {"max_new_tokens": 20}}' \
  -H 'Content-Type: application/json'
{"generated_text":" I am a very good person, I am very kind, I am very caring, I am"}
```

Most services provide a single endpoint that performs a task or pipeline. For text generation, the
main endpoint is `/generate` (or `generate_stream` for a streamed response). Running services are
yours to use as you see fit.

##### `stop` - Stop a service
When we are done with our service, we should shut it off and return its resources to the cluster. To do so, simply type
```shell
blackfish stop fddefdaf-d9d2-4392-82d8-c3c4fd2588c6
```
You should receive a nice message stating that the service was stopped, which you can confirm by checking its status with `blackfish ls`.

##### `rm` - Delete a service
Services aren't automatically deleted from your list, so it's a good idea to remove them when you're done if you don't need them for record keeping:
```shell
blackfish rm fddefdaf-d9d2-4392-82d8-c3c4fd2588c6
```
