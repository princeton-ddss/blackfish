# Blackfish
Blackfish is an open source "ML-as-a-Service" (MLaaS) platform that helps researchers use state-of-the-art, open source artificial intelligence and machine learning models. With Blackfish, researchers can spin up their own version of popular public cloud services (e.g., ChatGPT, Amazon Transcribe, etc.) using high-performance computing (HPC) resources already available on campus.

The primary goal of Blackfish is to facilitate **transparent** and **reproducible** research based on **open source** machine learning and artificial intelligence. We do this by providing mechanisms to run user-specified models with user-defined configurations. For academic research, open source models present several advantages over closed source models. First, whereas large-scale projects using public cloud services might cost $10K to $100K for [similar quality results](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1210559/full), open source models running on HPC resources are free to researchers. Second, with open source models you know *exactly* what model you are using and you can easily provide a copy of that model to other researchers. Closed source models can and do change without notice. Third, using open-source models allows complete transparency into how *your* data is being used.

## Why Blackfish?

### 1. It's easy! 🌈
Researchers should focus on research, not tooling. We try to meet researchers where they're at by providing multiple ways to work with Blackfish, including a CLI and browser-based UI.

Don't want to install Python packages? [Ask your HPC admins to add Blackfish to your Open OnDemand portal](https://github.com/princeton-ddss/blackfish-ondemand)!

### 2. It's transparent 🧐
You decide what model to run (down to the Git commit) and how you want it configured. There are no unexpected (or undetected) changes in performance because the model is always the same. All services are private—always—so you know *exactly* how your data is being handled.

### 3. It's free! 💸
You have an HPC cluster. We have software to run on it.

## Installation
Blackfish is a `pip`-installable python package. We recommend installing Blackfish to its own virtual environment, for example:
```shell
python -m venv .venv
source env/bin/activate
pip install blackfish-ml
```

For development, clone the package's repo and `pip` install instead:
```shell
git clone https://github.com/princeton-ddss/blackfish.git
python -m venv .venv
source env/bin/activate
cd blackfish && pip install -e .
```

The following command should return the path of the installed application if installation was successful:
```shell
source .venv/bin/activate
which blackfish
```

## Quickstart
Before you begin using Blackfish, you'll need to initialize the application. To do so, type
```shell
blackfish init
```
at the command line. This command will prompt you to provide details for a Blackfish *profile*. A typical default profile will look something like this:
```shell
name=default
type=slurm
host=della.princeton.edu
user=dannyboy
home=/home/dannyboy/.blackfish
cache=/scratch/gpfs/shared/.blackfish
```
For further details on profiles, refer to our [documentation](https://princeton-ddss.github.io/blackfish/getting_started/#profiles).

There are two ways for reseachers to interact with Blackfish: in a browser, via the user interface, or at the command-line using the Blackfish CLI. In either case, the starting point is the command
```shell
blackfish start
```
This command launches the Blackfish API that the UI and CLI connect to. A successful launch will look something like this:
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
in your browser by heading over to `http://localhost:8000`. We've put together some [videos]() demonstrating its usage, so let's instead take a look at the CLI.

Open a new terminal tab or window. First, let's see what services are available.
```shell
blackfish run --help
```
The output displays a list of available "commands". One of these is called `text-generation`.
This is a service that generates text given a input prompt. There are a variety of models
that we might use to perform this task. You can view your available models by typing
```shell
blackfish model ls --image=text-generation
```

This command outputs a list of models that we can pass to the `blackfish run text-generation`
command. Because we haven't added any models yet (unless your profile connected to a shared model repo), our list is empty! Let's add a small model:
```shell
# This will take a minute...
blackfish model add bigscience/bloom-560m
```

Once the model is downloaded, you can check that it is available by re-running the `blackfish model ls` command. We are now ready to spin up a `text-generation` instance:
```shell
blackfish run --mem 16 --time 00:05:00 text-generation --model bigscience/bloom-560m
```

This command returns an ID for our new service. We can find more information about our
service by running
```shell
blackfish ls
```

It might take a few minutes for a Slurm job to start, and it will require additional time for the service to setup after the job starts. Until then, our service's status will be either `SUBMITTED` or `STARTING`. Now would be a good time to make some tea 🫖

!!! note
    While you're doing that, note that can obtain detailed information about an individual service with the `blackfish details <service_id>` command. Now back to that tea...

Now that we're refreshed, let's see how our service is getting along. Re-run the command above:
```shell
blackfish ls
```

If things went well, then the service's status should be `RUNNING`. At this point, we can interact with the service. Let's say "Hello":
```shell
curl localhost:8080/generate \
  -X POST \
  -d '{"inputs": "Hello", "parameters": {"max_new_tokens": 20}}' \
  -H 'Content-Type: application/json'

# Response:
# {"generated_text":", I just want to say that I am very new to blogging and site-building and honestly s"}
```

Success! Our service is responding, albeit with fairly nonsensical results (I said this model small, not good!). Feel free to play around with this model to your heart's delight. It should remain available for approximately five minutes (`--time 00:05:00`).

When we are done with our service, we should shut it off and return its resources to the cluster. To do so, simply type
```shell
blackfish stop <service_id>
```

If you run `blackfish ls` again, you should see that the service is no longer listed: `ls` only displays active services. You want to see a list of *all* services by including the `--all` flag. Services remain in your services database until you explicit remove them, like so:
```shell
blackfish rm --filters id=<service_id>
```

## Want to learn more?
You can find loads more details on our official [documentation page](https://princeton-ddss.github.io/blackfish/).
