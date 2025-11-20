# Command Line

This guide walks through usage of the Blackfish command line tool (CLI). In the current version of Blackfish, the CLI is the *only* way to perform certain management operations, such as creating profiles and adding models. Thus, it's highly recommended that users develop some level of familiarity with the CLI even if intend to primarily use the UI or Python API[^1].

## Configuration

The Blackfish application (i.e., REST API) and command-line interface (CLI) pull settings from environment variables and/or (for the application) arguments provided at start-up. The most important environment variables are:

- `BLACKFISH_HOST`: host for local instance of the Blackfish app (default: `'localhost'`)
- `BLACKFISH_PORT`: port for local instance of the Blackfish app (default: `8000`)
- `BLACKFISH_HOME_DIR`: location to store application data (default: `'~/.blackfish'`)
- `BLACKFISH_DEBUG`: whether to run the application in debug mode (default: `True`)
- `BLACKFISH_AUTH_TOKEN`: a user-defined secret authentication token. Ignored if `DEBUG=True`.

Running the application in debug mode is recommended for *development only* on shared systems
as it does not use authentication. In "production mode", Blackfish randomly generates an authentication token.

!!! note

    The settings for the REST API are determined when the Blackfish application is started via `blackfish start`. Subsequent interactions with the API via the command line assume that the CLI is using the same configuration and will fail if this is not the case. For example, if you start Blackfish with `BLACKFISH_PORT=8081` and then try to run commands in a new terminal where `BLACKFISH_PORT` isn't set, the CLI will not be able communicate with the API.

## Profiles

Blackfish's primary function is to launch services that perform AI tasks. These services are, in general, detached from the system Blackfish runs on. Thus, we require a method to instruct Blackfish *how* we want to run services: what cluster should Blackfish use, and where should it look for any resources it needs? *Profiles* are Blackfish's method of saving this information and applying it across commands. A default profiles is *required*, but multiple profiles are useful if you have access to multiple HPC resources or have multiple accounts on a single HPC cluster.

!!! tip

    Blackfish profiles are stored in `$BLACKFISH_HOME/profiles.cfg`. On Linux, this is
    `$HOME/.blackfish/profiles.cfg` by default. You can modify this file directly, if needed, but you'll
    need to need setup any required remote resources by hand.

### Schemas

Every profile specifies a number of attributes that allow Blackfish to find resources (e.g., model
files) and deploy services accordingly. The exact attributes depend on the profile *schema*. There are currently two profile schemas: `LocalProfile` ("local") and `SlurmProfile` ("slurm"). All profiles require the following attributes:

- `name`: a unique profile name. The profile named "default" is used by Blackfish when a profile isn't
explicitly provided.
- `schema`: one of "slurm" or "local". The profile schema determines how services associated with this
profile are deployed by Blackfish. Use "slurm" if this profile will run jobs on an HPC cluster (via a Slurm job scheduler) and "local" to run services on your laptop.

The additional attribute requirements for specific types are listed below.

#### Local

A *local profile* specifies how to run services on a local machine, i.e., your laptop or desktop, *without a job scheduler*. This is useful for development and running models that do not require significant resources, especially if the model is able to use the GPU on your laptop.

- `home_dir`: a user-owned location to store model and image files on the local machine, e.g., `/home/<user>/.blackfish`. User should have read-write access to this directory.
- `cache_dir`: a shared location to source model and image files from. Blackfish does *not* attempt to create this directory for you, but it does require that it can be found. User should *at least* have read access to this directory.

#### Slurm

A *Slurm profile* specifies how to schedule services *on* a (possibly) remote server (e.g., HPC cluster) running Slurm.

- `host`: a server to run services on, e.g. `<cluster>@<university>.edu` or `localhost` if also running Blackfish on the cluster.
- `user`: a user name used to connect to server.
- `home`: a location on the server to store application model, image and job data, e.g., `/home/<user>/.blackfish`. User should have read-write access to this directory.
- `cache`: a location on the server to source additional shared model and images files from. Blackfish does *not* attempt to create this directory for you, but it does require that it can be found. User should *at least* have read access to this directory.

### Managing Profiles

The `blackfish profile` command provides methods for managing Blackfish profiles.

#### ls - List profiles

To view all profiles, type

```shell
blackfish profile ls
```

#### add - Create a profile

Creating a new profile is as simple as typing

```shell
blackfish profile add
```

and following the prompts (see attribute descriptions above). Note that profile names
are unique.

#### show - View a profile

You can view a list of all profiles with the `blackfish profile ls` command. If you want to view a
specific profile, use the `blackfish profile show` command instead, e.g.

```shell
blackfish profile show --name <profile>
```

Leaving off the `--name` option above will display the default profile, which is used by most
commands if no profile is explicitly provided.

#### update - Modify a profile

To modify a profile, use the `blackfish profile update` command, e.g.

```shell
blackfish profile update --name <profile>
```

This command updates the default profile if not `--name` is specified. Note that you cannot change
the `name` or `schema` attributes of a profile.

#### rm - Delete a profile

To delete a profile, type `blackfish profile rm --name <profile>`. By default, the command
requires you to confirm before deleting.

```shell
blackfish profile rm --name <profile>
```

## Services

Once you've initialized Blackfish and created a profile, you're ready to get to work! The entrypoint for working with the blackfish CLI is to type

```shell
blackfish start
```

in your terminal. If everything worked, you should see a message stating the application startup is complete. This command starts the Blackfish API *and* UI. At this point, you're free to switch over to the UI, if desired: just mosey on over to `http://localhost:8000` in your favorite browser. It's a relatively straight-forward interface, and we provide a detailed [usage guide](ui.md). But let's stay focus on the CLI.

Open a new terminal tab or window. First, let's see what type of services are available.

```shell
blackfish run --help
```

This command displays a list of available sub-commands. One of these is `text-generation`, which is a service that generates text given an input prompt. There are a variety of models that we might use to perform this task, so let's check out what's available on our setup.

### Obtaining Models

The command to list available models is:

```shell
blackfish model ls
```

Once you've added some models or if you already have access a shared cache directory of model, the output should look something like the following:

```
REPO                                   REVISION                                   PROFILE   IMAGE
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   default   speech-recognition
openai/whisper-tiny                    be0ba7c2f24f0127b27863a23a08002af4c2c279   default   speech-recognition
openai/whisper-small                   973afd24965f72e36ca33b3055d56a652f456b4d   default   speech-recognition
TinyLlama/TinyLlama-1.1B-Chat-v1.0     ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971   default   text-generation
meta-llama/Meta-Llama-3-70B            b4d08b7db49d488da3ac49adf25a6b9ac01ae338   macbook   text-generation
openai/whisper-tiny                    169d4a4341b33bc18d8881c4b69c2e104e1cc0af   macbook   speech-recognition
TinyLlama/TinyLlama-1.1B-Chat-v1.0     4f42c91d806a19ae1a46af6c3fb5f4990d884cd6   macbook   text-generation
```

As you can see, there are a number of models available[^2]. Notice that `TinyLlama/TinyLlama-1.1B-Chat-v1.0` is listed twice. The first listing refers to a specific "revision" (i.e., version) of this model—
`ac2ae5fab2ce3f9f40dc79b5ca9f637430d24971`—that is available to the `default` profile; the second listing refers to a different version of the same model—`4f42c91d806a19ae1a46af6c3fb5f4990d884cd6`—that is available to the `macbook` profile. For reproducibility, it's important to keep track of the exact revision used.

Let's say you would really prefer to use a smaller version of `Llama` than the 70 billion parameter model shown above, say `meta-llama/Meta-Llama-3-1B`. To add the new model, we would simply type

```shell
blackfish model add meta-llama/Meta-Llama-3-1B
```

This command downloads the model files, store them to the default profile's `home_dir`, and updates the model database. Note that the `model add` command currently only supports local downloads: if your default profile points to a remote cluster, then you'll need to run the command on that server instead.

Let's go ahead and run a service using one of these models.

### Managing Services

A *service* is a containerized API that is called to perform a specific task, such a text generation, using a model specified by the user when the API is created. Services perform inference in an "online" fashion, meaning that, in general, they process requests one at a time[^3]. Users can create as many services as they like (up to resource availability) and interact with them simultaneously. Services are completely managed by the user: as the creator of a service, you can stop or restart the service, and you control access to the service via an authentication token.

#### `run` - Start a service

Looking back at the help message for `blackfish run`, we see that there are a few items that we should provide. First, we need to select the type of service to run. We've already decide to run
`text-generation`, so we're good there. Next, there are a number of job options that we can provide. With the exception of `profile`, job options are based on the Slurm `sbatch` command and tell Blackfish the resources required to run a service. Finally, there are a number of "container options" available. To get a list of these, type `blackfish run text-generation --help`:

```shell
blackfish run text-generation --help
```

The most important of these is the `revision`, which specifies the exact version of the model we want to run. By default, Blackfish selects the most recent locally available version. This container option (as well as `--name`) is available for *all* tasks: the remaining options are task-specific.

We'll choose `TinyLlama/TinyLlama-1.1B-Chat-v1.0` for the required `MODEL` argument, which we saw earlier is available to the `default` and `macbook` profiles. This is a relatively small model, but we still want to ask for a GPU to speed things up. Putting it altogether, here's the command to start your service:

```shell
blackfish run \
  --gres 1 \
  --mem 8 \
  --ntasks-per-node 4 \
  --time 00:30:00 \
  text-generation TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --api-key sealsaretasty
```

!!! warning

    Omitting the `--api-key` argument leaves your service naked. Others users of the system where your service is running could potentially hijack your server or even gain access to your files via the service.

If everything worked, you should see output that looks something like this:

```shell
✔ Found 49 models.
✔ Found 1 snapshots.
⚠ No revision provided. Using latest available commit: fe8a4ea1ffedaf415f4da2f062534de366a451e6.
✔ Found model TinyLlama/TinyLlama-1.1B-Chat-v1.0!
✔ Started service: fed36739-70b4-4dc4-8017-a4277563aef9
```

What just happened? First, Blackfish checked to make sure that the requested model is available to the `default` profile. Next, it found a list of available revisions of the model and selected the
most recently published version because no revision was specified. Finally, it sent a request to deploy the model. Helpfully, the CLI returned an ID associated with the new service `fed36739-70b4-4dc4-8017-a4277563aef9`, which you can use get information about our service via the `blackfish ls` command.

!!! note

    If no `--revision` is provided, Blackfish automatically selects the most recently available *downloaded* version of the requested model. This reduces the
    time-to-first-inference, but may not be desirable for your use case. Download the model *before* starting your service if you need the [most recent version]() available on Hugging Face.

!!! tip

    Add the `--dry-run` flag to preview the start-up script that Blackfish will submit.

#### `ls` - List services

To view a list of your *running* Blackfish services, type

```shell
blackfish ls # --filter id=<service_id>,status=<status>
```

This will output a table similar to the following:

```shell
SERVICE ID      IMAGE                MODEL                                CREATED       UPDATED     STATUS    PORT   NAME              PROFILE
97ffde37-7e02   speech_recognition   openai/whisper-large-v3              7 hours ago   1 min ago   HEALTHY   8082   blackfish-11846   default
fed36739-70b4   text_generation      TinyLlama/TinyLlama-1.1B-Chat-v1.0   7 sec ago     5 sec ago   PENDING   None   blackfish-89359   della
```

The last item in this list is the service we just started. In this case, the `default` profile happens to be set up to connect to a remote HPC cluster, so the service is run as a Slurm job. It may take a few minutes for our Slurm job to start, and it will require additional time for the service to be ready after that[^4]. Until then, our service's status will be either `SUBMITTED`, `PENDING` or `STARTING`. Now would be a good time to brew a hot beverage ☕️.

!!! tip

    You can get more detailed information about a service with the `blackfish details <service_id>` command. Again, `--help` is your friend if you want more
    information.

Now that you're refreshed, let's see how our service is doing. Re-run the command above. If things went smoothly, then you should see that the service's status has changed to `HEALTHY` (if your service is still `STARTING`, give it another minute and try again).

At this point, we can start interacting with the service. Let's say "Hello", shall we?

The details of calling a service depend on the service you are trying to connect to. For the `text-generation` service, the primary endpoint is `/v1/chat/completions`. Here's a typical request from the command-line:

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
```

A successful response will look like this:

```
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

You can, of course, use any language you like for communicating with services: Python, R, JavaScript, etc. In the case of `text-generation`, you can also use client-libraries like [`openai-python`](https://github.com/openai/openai-python) to simplify API workflows.

!!! tip

    The `text-generation` service runs [vLLM's](https://docs.vllm.ai/en/latest/serving/openai_compatible_server/) OpenAI-compatible server. If you are used to working with ChatGPT, this API should be familiar and your scripts will generally "just work" if you point them to Blackfish instead. `vllm serve` supports a number of endpoints depending on the arguments provided. Any unrecognized arguments passed to the `text-generation` command are passed through to `vllm serve`, allowing users to control the precise deploy details of the `vllm` server.

#### `stop` - Stop a service

When you are done with a service, you should shut it down and return its resources to the cluster. To do so, simply type:

```shell
blackfish stop fed36739-70b4-4dc4-8017-a4277563aef9
```

You should receive a nice message stating that the service was stopped, which you can confirm by checking its status with `blackfish ls`.

#### `rm` - Delete a service

Blackfish keeps a record of every service that you've ever run. These records aren't automatically cleaned up, so it's a good idea to delete them when you're done using a service (if you don't need them for record keeping):

```shell
blackfish rm --filters id=fed36739-70b4-4dc4-8017-a4277563aef9
```

[^1]: Researchers that only intend to use Blackfish OnDemand should not generally need to interact with the CLI.
[^2]: The list of models displayed depends on your environment. If you do not have access to a shared HPC cache, your list of models is likely empty. Not to worry—we will see how to add models later on. If this is your first time running the command, use the `--refresh` flag to tell Blackfish to search for models in your cache directories and update the model database.
[^3]: In practice, services like `vLLM` can use dynamic batching to process requests concurrently. The number of concurrent requests these service can process is limited by a number of factors including the amount of memory available and properties of the requests themselves.
[^4]: The bulk of this time is spent loading model weights into memory. For small models (< 1B parameters), the service might be ready in a matter of seconds. Large models (~8B) might take 5-10 minutes to load.
