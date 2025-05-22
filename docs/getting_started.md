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
There's a small amount of setup required before we get started with Blackfish. Fortunately, it's mostly automated.

### SSH
Using Blackfish from your laptop requires a seamless (i.e., password-less) method of communicating with remote clusters. On many systems, this is simple to setup with the `ssh-keygen` and `ssh-copy-id` utilitites. First, make sure that you are connected to your institution's network (or VPN), then type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC server you need access to. You now have password-less access to your HPC server!

!!! warning

    Blackfish depends on seamless interaction with your university's HPC cluster. Before proceeding, make sure that you have enabled password-less login and are connected to your institutions network or VPN, if required.

### Initialization
To initialize Blackfish, just type
```shell
blackfish init
```
and answer the prompts to create a new default profile.

!!! note

    If your default profile connects to an HPC cluster, then Blackfish will attempt to set up the remote host at this point. Profile creation will fail if you're unable to connect to the HPC server and you'll need to re-run the `blackfish init` command or create a profile with `blackfish profile create` (see below).


### Models and Images
Blackfish works best with locally available model files and container images. Having these files available locally allows Blackfish to avoid slow downloads during deployment. See the section on [Obtaining Service Images and Models]() for more information, or talk to your institution's HPC cluster admins.

### Configuration
The application and command-line interface (CLI) pull their settings from environment variables and/or (for the application) arguments provided at start-up. The most important environment variables are:
```shell
BLACKFISH_HOST='localhost' # host for local instance of the Blackfish app
BLACKFISH_PORT=8000 # port for local instance of the Blackfish app
BLACKFISH_HOME_DIR='~/.blackfish' # location to store application data
BLACKFISH_DEV_MODE=1 # run the application with development settings
BLACKFISH_TOKEN='sealsaretasty' # a user-defined secret auth token
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
    `$HOME/.blackfish/profiles.cfg` by default. You can modify this file directly, if needed, but you'll
    need to need setup any required remote resources by hand.

#### Schemas
Each profile specifies a number of attributes that allow Blackfish to find resources (e.g., model
files) and deploy services accordingly. The exact attributes depend on the profile *schema*. There are currently two profile schemas: `LocalProfile` ("local") and `SlurmProfile` ("slurm"). All profiles require the following attributes:

- `name`: the unique profile name. The "default" profile is used by Blackfish when a profile isn't
explicitly provided.
- `schema`: one of "slurm" or "local". The profile schema determines how services associated with this
profile are deployed by Blackfish. Use "slurm" if this profile will run jobs on HPC and "local" to
run jobs on your laptop (or wherever Blackfish is installed).

The additional attribute requirements for specific types are listed below.

##### Slurm
A Slurm profile specifies how to schedule services *on* a (possibly) remote server (e.g., HPC cluster) running Slurm *from* a local machine.

- `host`: a HPC server to run services on, e.g. `<cluster>@<university>.edu` or `localhost` (if running Blackfish on an  HPC cluster).
- `user`: a user name on the HPC server.
- `home`: a location on the HPC server to store application data, e.g., `/home/<user>/.blackfish`
- `cache`: a location on the HPC server to store additional (typically shared) model images and
files. Blackfish does **not** attempt to create this directory for you, but it does require that it can be found.

##### Local
A local profile specifies how to run services on a local machine, i.e., your laptop or desktop, *without a job scheduler*. This is useful for development and for running models that do not require large amounts of resource, especially if the model is able to use the GPU on your laptop.

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
```shell
blackfish profile rm --name <profile>
```


## Usage
Once you've initialized Blackfish and created a profile, you're ready to go. Their are two ways ways to interact with Blackfish: in a browser, via the user interface (UI), or at the command-line using the Blackfish CLI. In either case, the entrypoint is to type
```shell
blackfish start
```
in the command-line. If everything worked, you should see a message stating the application
startup is complete.

At this point, we need to decide how we want to interact with Blackfish. The UI is available in your browser by heading over to `http://localhost:8000`. It's a relatively straight-forward interface, and we have detailed usage examples on the [user interface page](), so let's instead take a look at the CLI.

Open a new terminal tab or window. First, let's see what type of services are available.
```shell
blackfish run --help

 Usage: blackfish run [OPTIONS] COMMAND [ARGS]...

 Run an inference service.
 The format of options approximately follows that of Slurm's `sbatch` command.

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --time                 TEXT     The duration to run the service for, e.g., 1:00 (one hour).               │
│ --ntasks-per-node      INTEGER  The number of tasks per compute node.                                     │
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
This command displays a list of available sub-commands. One of these is `text-generation`, which is a service that generates text given an input prompt. There are a variety of models that we might use to perform this task, so let's check out what's available on our setup.

### Models

```shell
blackfish model ls
REPO                                   REVISION                                   PROFILE   IMAGE
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   default   speech-recognition
openai/whisper-tiny                    be0ba7c2f24f0127b27863a23a08002af4c2c279   default   speech-recognition
openai/whisper-small                   973afd24965f72e36ca33b3055d56a652f456b4d   default   speech-recognition
TinyLlama/TinyLlama-1.1B-Chat-v1.0     ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971   default   text-generation
meta-llama/Meta-Llama-3-70B            b4d08b7db49d488da3ac49adf25a6b9ac01ae338   macbook   text-generation
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   macbook   speech-recognition
TinyLlama/TinyLlama-1.1B-Chat-v1.0     4f42c91d806a19ae1a46af6c3fb5f4990d884cd6   macbook   text-generation
```
As you can see, we have a number of models available.[^1] Notice that `TinyLlama/TinyLlama-1.1B-Chat-v1.0` is listed twice. The first listing refers to a specific version of this model—
`ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971`—that is available to the `default` profile; the second listing refers to a different version ("revision") of the same model—`4f42c91d806a19ae1a46af6c3fb5f4990d884cd6`—that is available to the `macbook` profile. For reproducibility, it's important to keep track of the exact revision used.

[^1]: The list of models you see depends on your environment. If you do not have access to a shared HPC cache, your list of models is likely empty. Not to worry—we will see how to add models later on.

Let's go ahead and try to run one of these models.

### Services
A *service* is a containerized API that is called to perform a specific task, such a text generation, using a model specified by the user when the API is created. Services perform inference in an "online" fashion, meaning that, in general, they process requests one input at a time. Users can create as many services as they like (and have resources to support) and interact with them simultaneously. Services are completely managed by the user: as the creator of a service, you are the only person that can stop or restart the service, and you control access to the service via an authentication token.

#### Commands

##### `run` - Start a service
Looking back at the help message for `blackfish run`, we see that there are a few items that we should provide. First, we need to select the type of service to run. We've already decide to run
`text-generation`, so we're good there. Next, there are a number of job options that we can provide. With the exception of `profile`, job options are based on the Slurm `sbatch` command and tell Blackfish the resources required to run a service. Finally, there are a number of "container options" available. To get a list of these, type `blackfish run text-generation --help`:

```shell
blackfish run text-generation --help

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
The most important of these is the `revision`, which specifies the exact version of the model we want to run. By default, Blackfish selects the most recent locally available version. This container option (as well as `--name`) is available for *all* tasks: the remaining options are task-specific.

We'll choose `TinyLlama/TinyLlama-1.1B-Chat-v1.0` for the required `MODEL` argument, which we saw earlier is available to the `default` and `macbook` profiles. This is a relatively small model, but we still want to ask for a GPU to speed things up. Putting it altogether, here's a command to start our service:
```shell
blackfish run --profile della --gres 1 --mem 16 --ntasks-per-node 4 --time 00:30:00 --constraint 'amd&gpu40' text-generation TinyLlama/TinyLlama-1.1B-Chat-v1.0 --api-key sealsaretasty
✔ Found 49 models.
✔ Found 1 snapshots.
⚠ No revision provided. Using latest available commit: fe8a4ea1ffedaf415f4da2f062534de366a451e6.
✔ Found model TinyLlama/TinyLlama-1.1B-Chat-v1.0!
✔ Started service: fed36739-70b4-4dc4-8017-a4277563aef9
```
What just happened? First, Blackfish checked to make sure that the requested model is available to the `della` profile. Next, it found a list of available revisions of the model and selected the
most recently published version because no revision was specified. Finally, it sent a request to deploy the model. Helpfully, the CLI returned an ID associated with the new service `fed36739-70b4-4dc4-8017-a4277563aef9`, which we can use get information about our service via the `blackfish ls` command.

!!! note

    If no `--revision` is provided, Blackfish automatically suggests the most recently available *downloaded* version of the requested model. This reduces the
    time-to-first-inference, but may not be desirable for your use case. Download the model *before* starting your service if you need the [most recent version]() available on Hugging Face.

!!! tip

    Add the `--dry-run` flag to preview the start-up script that Blackfish will submit.

##### `ls` - List services
To view a list of your Blackfish services, type
```shell
blackfish ls # --filter id=<service_id>,status=<status>
SERVICE ID      IMAGE                MODEL                                CREATED       UPDATED     STATUS    PORT   NAME              PROFILE
97ffde37-7e02   speech_recognition   openai/whisper-large-v3              7 hours ago   1 min ago   HEALTHY   8082   blackfish-11846   default
fed36739-70b4   text_generation      TinyLlama/TinyLlama-1.1B-Chat-v1.0   7 sec ago     5 sec ago   PENDING   None   blackfish-89359   della
```
The last item in this list is the service we just started. In this case, the `default` profile happens to be set up to connect to a remote HPC cluster, so the service is run as a Slurm job. It
may take a few minutes for our Slurm job to start, and it will require additional time for the service to be ready after that. Until then, our service's status will be either `SUBMITTED`, `PENDING` or `STARTING`. Now would be a good time to brew a hot beverage ☕️.

!!! tip

    If you ever want more detailed information about a service, you can get it with the
    `blackfish details <service_id>` command. Again, `--help` is your friend if you want more
    information.

Now that we're refreshed, let's see how our service is doing. Re-run the command above. If things went smoothly, then we should see that the service's status has changed to `HEALTHY` (if your service is still `STARTING`, give it another minute and try again).

```shell
blackfish ls
SERVICE ID      IMAGE                MODEL                                CREATED       UPDATED      STATUS    PORT   NAME              PROFILE
97ffde37-7e02   speech_recognition   openai/whisper-large-v3              7 hours ago   19 sec ago   HEALTHY   8082   blackfish-11846   default
fed36739-70b4   text_generation      TinyLlama/TinyLlama-1.1B-Chat-v1.0   2 min ago     19 sec ago   HEALTHY   8080   blackfish-12328   della
```

At this point, we can start
interacting with the service. Let's say "Hello", shall we?

The details of calling a service depend on the service you are trying to connect to. For the `text-generation` service, the primary endpoint is accessed like so:

```shell
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
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1192  100   911  100   281   1652    509 --:--:-- --:--:-- --:--:--  2159
{
  "id": "chatcmpl-b6452981728f4f3cb563960d6639f8a4",
  "object": "chat.completion",
  "created": 1747826716,
  "model": "/data/snapshots/fe8a4ea1ffedaf415f4da2f062534de366a451e6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "reasoning_content": null,
        "content": "Orcas (also known as killer whales) are incredibly intelligent and social animals that are known for their incredible abilities. Here are some reasons why orcas are so awesome:\n\n1. Intelligence: Orcas are highly intelligent and have been observed using tools, communicating with each other, and even learning from their trainers.\n\n2. Social behavior: Orcas are highly social animals and form complex social structures, including family groups, pods,",
        "tool_calls": []
      },
      "logprobs": null,
      "finish_reason": "length",
      "stop_reason": null
    }
  ],
  "usage": {
    "prompt_tokens": 40,
    "total_tokens": 140,
    "completion_tokens": 100,
    "prompt_tokens_details": null
  },
  "prompt_logprobs": null
}
```

Most services provide a single endpoint that performs a task or pipeline. For text generation, there two main endpoints, `/v1/completions` and `/v1/chat/completions`. Running services are yours to use as you see fit.

##### `stop` - Stop a service
When we are done with our service, we should shut it off and return its resources to the cluster. To do so, simply type
```shell
blackfish stop fed36739-70b4-4dc4-8017-a4277563aef9
✔ Stopped service fed36739-70b4-4dc4-8017-a4277563aef9
```
You should receive a nice message stating that the service was stopped, which you can confirm by checking its status with `blackfish ls`.

##### `rm` - Delete a service
Services aren't automatically deleted from your list, so it's a good idea to remove them when you're done if you don't need them for record keeping:
```shell
blackfish rm --filters id=fed36739-70b4-4dc4-8017-a4277563aef9
✔ Removed 1 service.
```

## Speech Recognition
```shell
blackfish run --profile default speech-recognition openai/whisper-large-v3
✔ Found 4 models.
✔ Found 1 snapshots.
⚠ No revision provided. Using latest available commit: 06f233fe06e710322aca913c1bc4249a0d71fce1.
✔ Found model openai/whisper-large-v3!
✔ Started service: 70e59004-84d4-4f7c-bf78-95ef96054289
```

```shell
curl http://localhost:8080/transcribe \
  -H "Content-Type: application/json" \
  -d '{
        "audio_path": "/data/audio/NY045-0.mp3",
        "response_format": "text"
    }' | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   465  100   375  100    90     10      2  0:00:45  0:00:35  0:00:10    91
{
  "audio_path": "/data/audio/NY045-0.mp3",
  "text": " Oh, going to Cuba. I went to Cuba on Prohibition time, too. And I brought a lot of fancy bottles, a little, like one drink in for souvenirs for all my friends. Well, Atlantic City, the ship was stopped. It was all in the newspapers about it, too. The crew had ripped the walls and put all",
  "segments": null,
  "task": "transcribe"
}
```
