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

### Docker
```shell
docker pull princeton-ddss/blackfish:latest
```

If you only plan to use the UI, then you can run
```shell
docker run -p 3000 \
    -v /home/<user>/:/data \
    princeton-ddss/blackfish:latest
```

Supplying the `-v` argument will allow you to save application data across `docker
run` calls.

## Setup
There's a small amount of setup required before we get started with Blackfish. Fortunately, it's mostly automated.

### SSH
Using Blackfish from your laptop requires a seamless (i.e., password-less) method of communicating with remote clusters. On many systems, this is simple to setup with the `ssh-keygen` and `ssh-copy-id` utilitites. First, make sure that you are connected to your institution's network (or VPN), then type the following at the command-line:
```
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```
These commands create a secure public-private key pair and send the public key to the HPC
server you need access to. You now have password-less access to your HPC server!

!!! warning

    Blackfish depends on seemless interaction with your university's HPC cluster. Before proceeding,
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
    the remote host at this point. If you're unable to connect to the HPC server, then profile
    creation will fail and you'll need to re-run the `blackfish init` command or create a 
    profile with `blackfish profile create` (see below).


### Models and Images
Blackfish works best with locally available model files and container images. Having these files available locally allows Blackfish to avoid slow downloads during deployment. See our section on [Obtaining Service Images and Models]() for more information, or talk to your institution's HPC cluster admins.

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
The `blackfish profile` command provides methods for managing Blackfish profiles. Profiles
are useful if you have access to multiple HPC resources or have multiple accounts on an HPC server.
Each profile consists of some combination of the following attributes, depending on the profile type.

!!! tip

    Blackfish profiles are stored in `$BLACKFISH_HOME/profiles`. On Linux, this is `$HOME/.blackfish/profile`
    by default. You can modify this file directly, if needed, but you'll need to need setup any required remote
    resources by hand.

#### Profile Attributes
- `name`: the unique profile name. The "default" profile is used by Blackfish when a profile isn't explicitly provided.
- `type`: one of "slurm" or "local". The profile type determines how services associated with this profile are deployed by Blackfish. Use "slurm" if this profile will run jobs on HPC and "local" to run jobs on your laptop (or wherever Blackfish
is installed).
- `host`: the HPC server to run services on, e.g. `<cluster>@<university>.edu`.
- `user`: the user name on the HPC server.
- `home`: the location on the HPC server to store application data, e.g., `/home/<user>/.blackfish`
- `cache`: the location on the HPC server to store additional (typically shared) model images and files.
Blackfish does **not** attempt to create this directory for you, but it does require that it can be found.

#### Create a profile
Creating a new profile is as simple as typing
```shell
blackfish profile create
```

and following the prompts (see attribute descriptions above). Note that profile names
are unique.

#### View a profile
You can view all profiles with the `blackfish profile list` command. If you want to view a specific profile, use the `blackfish profile show` command instead, e.g.
```shell
blackfish profile show --name hpc
```

#### Modify a profile
To modify a profile, use the `blackfish profile update` command, e.g.
```shell
blackfish profile update --name hpc
```
Note that you cannot change the name attribute of a profile.

#### Delete a profile
To delete a profile, type `blackfish profile delete --name <profile>`. 

## Usage
Once you've initialized Blackfish and created a profile, you're ready to go. Their are two ways ways to interact with Blackfish: in a browser, via the user interface, or at the command-line using the Blackfish CLI. In either case, the entrypoint is to type
```shell
blackfish start --ui
```
in the command-line. If everything worked, you should see a message stating the application
startup is complete.

At this point, we need to decide how we want to interact with Blackfish. The UI is available
in your browser by heading over to `http://127.0.0.1:8000`. It's largely self-explanatory, so
let's instead take a look at the CLI.

### CLI
Open a new terminal tab/window. First, let's see what type of services are available.
```shell
➜ blackfish run --help
                                                                                
 Usage: blackfish run [OPTIONS] COMMAND [ARGS]...                               
                                                                                
 Run an inference service                                                       
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --time               TEXT     The duration to run the service for, e.g.,     │
│                               1:00:00 (one hour).                            │
│                               (TEXT)                                         │
│ --ntasks_per_node    INTEGER  The number of tasks per compute node.          │
│                               (INTEGER)                                      │
│ --mem                INTEGER  The memory required per compute node in GB,    │
│                               e.g., 16 (G).                                  │
│                               (INTEGER)                                      │
│ --gres               INTEGER  The number of GPU devices required per compute │
│                               node, e.g., 1.                                 │
│                               (INTEGER)                                      │
│ --partition          TEXT     The HPC partition to run the service on.       │
│                               (TEXT)                                         │
│ --constraint         TEXT     Required compute node features, e.g., 'gpu80'. │
│                               (TEXT)                                         │
│ --profile            TEXT     The Blackfish profile to use. (TEXT)           │
│ --help                        Show this message and exit.                    │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ text-generate                   Start service MODEL.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```
This command displays a list of available sub-commands. One of these is `text-generate`, which is a service that generates text given an input prompt. There are a variety of models that we might use to perform this task, so let's check out what's available on our setup.

#### Models

##### `ls` - List available models
```shell
blackfish models ls --refresh
ID                                     REPO                                   REVISION                                   PROFILE      
1cfd44ac-ce42-4eae-8f74-9387c3420001   meta-llama/Meta-Llama-3-70B            b4d08b7db49d488da3ac49adf25a6b9ac01ae338   default      
d76857ca-2244-47d5-a309-897682f2d414   meta-llama/Meta-Llama-3-8B             62bd457b6fe961a42a631306577e622c83876cb6   default      
87d0d03f-3c56-4c73-a358-dbad39cd5bf1   meta-llama/Meta-Llama-3-70B-instruct   7129260dd854a80eb10ace5f61c20324b472b31c   default      
764c0ae8-5785-4ab5-8a50-b0ad60b220cc   bigscience/bloom-560m                  ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971   default      
d04de34b-1418-4ba1-a7a1-a16e92444f2b   meta-llama/Meta-Llama-3-8B-instruct    e1945c40cd546c78e41f1151f4db032b271faeaa   default
b3aee869-10e9-4b35-ab20-cb943b400add   bigscience/bloom-560m                  4f42c91d806a19ae1a46af6c3fb5f4990d884cd6   test        
```
As you can see, we ahve a number of models available.[^1] Notice that `bigscience/bloom-560m` is listed twice. The first listing refers to a specific version of this model—`ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971`—that is available to the `default` profile; the second listing refers to a *different* version of the same model—`4f42c91d806a19ae1a46af6c3fb5f4990d884cd6`—that is available to the `test` profile. For reproducability, it's important to keep track of the exact revision used. 

[^1]: The list of models you see will depend on your environment. If you do not have access to a shared HPC cache, your list of models is likely empty. Not to worry—we will see how to add models later on.

Let's go ahead and try to run one of these models.

#### Services

##### `run` - Start a service
Looking back at the help message for `blackfish run`, we see that there are a few items that we should provide. First, we need to select the type of service to run. We've already decide to run `text-generate`, so we're good there. Next, we have a number of job options that we can provide. With the exception of `profile`, job options are based on the Slurm `sbatch` command and tell Blackfish the resources required to run a service. Finally, there are a number of "container options" that we can use. To get a list, type `blackfish run text-generate --help`:
```shell
blackfish run text-generate --help                                                   
                                                                                
 Usage: blackfish run text-generate [OPTIONS]                                   
                                                                                
 Start service MODEL.                                                           
                                                                                
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --model                       TEXT     Model to serve. (TEXT)                │
│ --name                        TEXT     (TEXT)                                │
│ --revision                -r  TEXT     Use a specific model revision (commit │
│                                        id or branch)                         │
│                                        (TEXT)                                │
│ --quantize                -q  TEXT     Quantize the model. Supported values: │
│                                        awq (4bit), gptq (4-bit),             │
│                                        bitsandbytes (8-bit).                 │
│                                        (TEXT)                                │
│ --disable-custom-kernels               Disable custom CUDA kernels.          │
│ --sharded                                                                    │
│ --max-input-length            INTEGER  The maximum allowed input length (in  │
│                                        tokens).                              │
│                                        (INTEGER)                             │
│ --max-total-tokens            INTEGER  The maximum allowed total length of   │
│                                        input and output (in tokens).         │
│                                        (INTEGER)                             │
│ --dry-run                              Print Slurm script only.              │
│ --help                                 Show this message and exit.           │
╰──────────────────────────────────────────────────────────────────────────────╯
```
The most important of these is the `model`. We'll choose the `bigscience/bloom-560m` that we saw earlier is available to the `default` and `test` profiles. This is a small model, but we still need to ask for a GPU because the text generation service requires it. Putting it altogether, here's the command to start our service:
```shell
blackfish run \
  --mem 16 \
  --ntasks_per_node 4 \
  --gres 1 \
  --time 00:05 \
  text-generate \
  --model bigscience/bloom-560m
✔ Found 5 models. 
✔ Found 1 snapshots. 
✔ Found model bigscience/bloom-560m[ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971] in /scratch/gpfs/ddss/.blackfish/models. 
⚠ No revision provided. Using latest available commit ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971.
✔ Started service: fddefdaf-d9d2-4392-82d8-c3c4fd2588c6 
```
What just happened? Blackfish checked to make sure that the requested model is available to the `default` profile, found an available revision and sent a request to deploy the model. Helpfully, the CLI returned an ID associated with the new service: `fddefdaf-d9d2-4392-82d8-c3c4fd2588c6`. We can get more information about our service using the `blackfish ls` command.

!!! note

    If no `--revision` is provided, Blackfish automatically suggests the most recently
    available *downloaded* version of the requested model. This reduces the
    time-to-first-inference, but may not be desirable for your use case. Download the
    model *before* starting your service if you need the [most recent version]() available
    on Hugging Face.

!!! tip

    Add the `--dry-run` flag to any service command in order to preview the job Blackfish
    will submit to Slurm.

##### `ls` - List available services
To view a list of all your Blackfish services, type
```shell
blackfish ls # --filter id=<service_id>,status=<status>
SERVICE ID                             IMAGE             MODEL                         CREATED                       UPDATED                       STATUS    PORTS   NAME              
12bb9574-28a8-4cdd-80a4-ad8430bd8d82   text_generation   meta-llama/Meta-Llama-3-8B    2024-07-31T15:16:32.825331Z   2024-07-31T15:30:03.860402Z   TIMEOUT   None    blackfish-10205   
9c128c84-a908-4f17-995d-5780b2c0895d   text_generation   meta-llama/Meta-Llama-3-70B   2024-08-01T15:37:46.345488Z   2024-08-01T15:40:13.828408Z   FAILED    None    blackfish-12575      
fddefdaf-d9d2-4392-82d8-c3c4fd2588c6   text_generation   bigscience/bloom-560m         2024-08-27T20:00:53.553854Z   2024-08-27T20:00:53.553864Z   PENDING   None    blackfish-11753 
```
The last item in this list is the service we just started. In this case, the `default` profile happens to be set up to connect to a remote HPC cluster, so the service is run as a Slurm job. It might take a few minutes for our Slurm job to start, and it will take some additional time for the service to be ready after that. Until then, our service's status will be either `SUBMITTED`, `PENDING` or `STARTING`. Now would be a good time to brew some tea...

!!! tip

    While you're brewing that tea, now is a good time to note that if you ever want more detailed information about a service, you can get that with the `blackfish details <service_id>` command. Again, `--help` is your friend if you want more information. But back to that tea...

Now that we're refreshed, let's see how our service is doing. Re-run the command above. If things went well, then we should see that the service's status has changed to `HEALTHY` (if you're service is still `STARTING`, give it another minute and try again). At this point, we can start interacting with the service. Let's say "Hello".

##### `fetch` - Call a service
The details of calling a service depend on the service you are trying to connect to. For the `text-generation` service, the primary endpoint is accessed like so:
```shell
curl 127.0.0.1:8080/generate \
  -X POST \
  -d '{"inputs": "Hello", "parameters": {"max_new_tokens": 20}}' \
  -H 'Content-Type: application/json'
```
Alternatively, we could call the service through the Blackfish UI or CLI, either of which will handle the connection details for you, with the limitation of only supporting the core features of each service API.

##### `stop` - Stop a service
When we are done with our service, we should shut it off and return its resources to the cluster. To do so, simply type
```shell
blackfish stop fddefdaf-d9d2-4392-82d8-c3c4fd2588c6
```
You should receive a nice message stating that the service was stoppped, which you can confirm by checking its status with `blackfish ls`.

##### `rm` - Delete a service
Services aren't automatically deleted from your list, so it's a good idea to remove them when you're done if you don't need them for record keeping:
```shell
blackfish rm fddefdaf-d9d2-4392-82d8-c3c4fd2588c6
```