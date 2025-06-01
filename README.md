# Blackfish
Blackfish is an open source "ML-as-a-Service" (MLaaS) platform that helps researchers use state-of-the-art, open source artificial intelligence and machine learning models. With Blackfish, researchers can spin up their own version of popular public cloud services (e.g., ChatGPT, Amazon Transcribe, etc.) using high-performance computing (HPC) resources already available on campus.

The primary goal of Blackfish is to facilitate **transparent** and **reproducible** research based on **open source** machine learning and artificial intelligence. We do this by providing mechanisms to run user-specified models with user-defined configurations. For academic research, open source models present several advantages over closed source models. First, whereas large-scale projects using public cloud services might cost $10K to $100K for [similar quality results](https://www.frontiersin.org/journals/big-data/articles/10.3389/fdata.2023.1210559/full), open source models running on HPC resources are free to researchers. Second, with open source models you know *exactly* what model you are using and you can easily provide a copy of that model to other researchers. Closed source models can and do change without notice. Third, using open-source models allows complete transparency into how *your* data is being used.

## Why should you use Blackfish?

### 1. It's easy! 🌈
Researchers should focus on research, not tooling. We try to meet researchers where they're at by providing multiple ways to work with Blackfish, including a CLI and browser-based UI.

Don't want to install Python packages? [Ask your HPC admins to add Blackfish to your Open OnDemand portal](https://github.com/princeton-ddss/blackfish-ondemand)!

### 2. It's transparent 🧐
You decide what model to run (down to the Git commit) and how you want it configured. There are no unexpected (or undetected) changes in performance because the model is always the same. All services are *private*, so you know exactly how your data is being handled.

### 3. It's free! 💸
You have an HPC cluster. We have software to run on it.

## Installation
Blackfish is a `pip`-installable python package. We recommend installing Blackfish to its own virtual environment, for example:
```shell
python -m venv .venv
source .venv/bin/activate
pip install blackfish-ai
```
Or, using `uv`:
```shell
uv venv
uv pip install blackfish-ai
```

For development, clone the package's repo and `pip` install instead:
```shell
git clone https://github.com/princeton-ddss/blackfish.git
python -m venv .venv
source .venv/bin/activate
cd blackfish && pip install -e .
```

The following command should return the path of the installed application if installation was successful:
```shell
which blackfish
```

## Quickstart

### HPC Setup
Before you begin using Blackfish, you'll need to initialize the application. To do so, type
```shell
blackfish init
```
at the command line. This command will prompt you to provide details for a Blackfish *profile*. Let's create a default profile that will allow us to run services on compute nodes via the Slurm job scheduler:
```
name=default
type=slurm
host=localhost
user=shamu
home=/home/shamu/.blackfish
cache=/scratch/gpfs/shared/.blackfish
```
The `cache` is a shared directory set up by your HPC admin for storing shared model and image files. This guide assumes you have access to a cache directory with all required Docker images downloaded. If your HPC does not have a cache set up, you can assign the same directory used for `home` and [add the images yourself](#image-support).

Once Blackfish is properly initialized, you can run the `blackfish start` command to launch the application:
```shell
blackfish start
```

```shell
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

Congratulations! Blackfish is now up and running! The core API serves the user interface as well as endpoints to manage services and Blackfish itself. The rest of this guide will walk through how to use the CLI to interact with these endpoints.

### Running Services

Let's start by exploring what services are available. In a new terminal (with your virtual environment activated), type
```shell
blackfish run --help
```
The output displays a list of available commands. One of these is commands `text-generation`, which launches a service to generate text given an input prompt or message history (for models supporting chat). There are *many* [models](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending) to choose from to perform this task, but Blackfish only allows you to run models you have already downloaded. To view a list of available models, run
```shell
blackfish model ls --image=text-generation --refresh
```

This command shows all models that we can pass to the `blackfish run text-generation` command. Because we haven't downloaded any models yet (unless your profile connected to a shared model repo), our list is empty! Let's add a "tiny" model:
```shell
blackfish model add TinyLlama/TinyLlama-1.1B-Chat-v1.0  # This will take a minute...
```

Once the model is done downloading, you can check that it is available by re-running the `blackfish model ls --refresh` command. We're now ready to spin up a `text-generation` service:
```shell
blackfish run --gres 1 --time 00:30:00 text-generation TinyLlama/TinyLlama-1.1B-Chat-v1.0 --api-key sealsaretasty
```

```
✔ Found 49 models.
✔ Found 1 snapshots.
⚠ No revision provided. Using latest available commit: fe8a4ea1ffedaf415f4da2f062534de366a451e6.
✔ Found model TinyLlama/TinyLlama-1.1B-Chat-v1.0!
✔ Started service: 55862e3b-c2c2-428d-ac2d-89bdfa911fa4
```

This command returns an ID for our new service. We can view more information about our
service by running
```shell
blackfish ls
```
```
SERVICE ID      IMAGE             MODEL                                CREATED     UPDATED     STATUS    PORT   NAME              PROFILE
55862e3b-c2c2   text_generation   TinyLlama/TinyLlama-1.1B-Chat-v1.0   3 sec ago   3 sec ago   PENDING   None   blackfish-77771   default
```

As you can see, our service is still waiting in the job queue (`PENDING`). It might take a few minutes for a Slurm job to start, and it will require additional time for the service to load after it starts. Until then, our service's status will be either `SUBMITTED` or `STARTING`. Now would be a good time to make some tea 🫖

> [!TIP]
> While you're doing that, note that you can obtain additional information about an individual service with the `blackfish details <service_id>` command. Now back to that tea...

Now that we're refreshed, let's see how our service is getting along. Re-run the command above:
```shell
blackfish ls
```
```
SERVICE ID      IMAGE             MODEL                                CREATED     UPDATED     STATUS    PORT   NAME              PROFILE
55862e3b-c2c2   text_generation   TinyLlama/TinyLlama-1.1B-Chat-v1.0   3 min ago   3 min ago   HEALTHY   8080   blackfish-90846   default
```

If things went well, then the service's status should be `HEALTHY`. At this point, we can start using the service. Let's ask an important question:
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
```shell
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1191  100   910  100   281   1332    411 --:--:-- --:--:-- --:--:--  1743
{
  "id": "chatcmpl-93f94b03258044cba7ad8ada48b01e5b",
  "object": "chat.completion",
  "created": 1748628455,
  "model": "/data/snapshots/fe8a4ea1ffedaf415f4da2f062534de366a451e6",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "reasoning_content": null,
        "content": "Orcas, also known as killer whales, are incredibly intelligent and social animals that are known for their incredible abilities. Here are some reasons why orcas are so awesome:\n\n1. Intelligence: Orcas are highly intelligent and have been observed using tools, communication, and social behavior to achieve their goals. They are also highly adaptable and can live in a variety of environments, including marine and freshwater habitats.\n\n2. Strength:",
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

Success! Our service is responding as expected. Feel free to play around with this model to your heart's delight. It should remain available for approximately thirty minutes in total (`--time 00:30:00`).

> [!TIP]
> You can interact with text generation services using OpenAI's official Python library, `openai`. If you're already using `openai` to work with private models like ChatGPT, your existing scripts should work with minimal modification!

When we're done with our service, we should shut it off and return its resources to the cluster. To do so, simply type
```shell
blackfish stop 55862e3b-c2c2-428d-ac2d-89bdfa911fa4
```
```
✔ Stopped service 55862e3b-c2c2-428d-ac2d-89bdfa911fa4.
```

If you run `blackfish ls` once more, you should see that the service is no longer listed: `ls` only displays *active* services by default. You can view *all* services by including the `--all` flag. Services remain in your services database until you explicit remove them, like so:
```shell
blackfish rm --filters id=55862e3b-c2c2-428d-ac2d-89bdfa911fa4
```
```
✔ Removed 1 service.
```

### Local Setup
Using Blackfish from your laptop requires a seamless (i.e., password-less) method of communicating with remote clusters. On many systems, this is simple to setup with the `ssh-keygen` and `ssh-copy-id` utilitites. First, make sure that you are connected to your institution's network or VPN (if required), then type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC server you need access to. You now have password-less access to your HPC server!

> [!WARNING]
> Blackfish depends on seamless interaction with your university's HPC cluster. Before proceeding, make sure that you have enabled password-less login and are connected to your institutions network or VPN, if required.

#### Local Profile
Before we start using services, we'll need to initialize Blackfish and create a profile. Type
```shell
blackfish init
```
at the command line. This command will prompt you to provide details for a default Blackfish profile. If you want to run services on your laptop by default, then your profile should look something like this:

```
name=default
type=local
home=/home/shamu/.blackfish # local directory
cache=/scratch/gpfs/shared/.blackfish # shared local directory to store model and image data
```

#### Slurm Profile
On the other hand, if you normally want to run services on a remote Slurm cluster, then your profile should look as follows:
```
name=default
type=slurm
host=della.princeton.edu
user=shamu
home=/home/shamu/.blackfish # directory on host
cache=/scratch/gpfs/shared/.blackfish # shared directory on host to store model and image data
```

For further details on profiles, refer to our [documentation](https://princeton-ddss.github.io/blackfish/latest/getting_started/#profiles).

## Images
The current version of Blackfish does not ship Docker images required to run services. When running jobs locally, Docker will attempt to download the required image before starting the service, resulting in delays during the launching step. Instead, it's recommended that users pre-download the required images listed below.


> [!NOTE]
> When running services on Slurm clusters, Blackfish looks for the required SIF file in `$PROFILE_CACHE_DIR/images`.


| Version | Text Generation   | Speech Recognition                 | Object Detection |
|:--------|:-----------------:|:----------------------------------:|:----------------:|
| 0.1.0   | vllm-openai:0.8.4 | speech-recognition-inference:0.1.2 | -                |
<!-- | 0.1.1   | vllm-openai:0.8.4 | speech-recognition-inference:0.1.2 | -                | -->

## Models
Blackfish (or rather, the services Blackfish runs) does not guarantee support for every model available from the [Hugging Face's Model Hub](https://huggingface.co/models). As a practical matter, however, services support nearly all "popular" models listed under their corresponding pipeline, including many "quantized" models (in the case of LLMs). Below is an evolving list of models that we have tested on HPC, including the resources requested and utilized by the service.

The main requirement to run online inference is sufficient GPU memory. As a rule-of-thumb, the *minimum* memory required for a model is obtained by multiplying the number of parameters (in billions) times the number of bytes per parameter (`dtype / 8`). In practice, you need to budget an additional 5-10 GB for KV caching and keep in mind that default GPU utilization is typically set to around 90-95% by service images.


| Model                                        | Pipeline                     | Supported | Chat     | Gated | Reasoning | Memory | GPUs       | Cores | Size  | Dtype | Notes                                                                                          |
|----------------------------------------------|------------------------------|-----------|----------|-------|-----------|--------|------------|-------|-------|-------|------------------------------------------------------------------------------------------------|
| Qwen/QwQ-32B                                 | Text-generation              | ✅        | ✅       |       | ✅        | 16G    |  61.0/160G | 4     | 32.8B | bf16  | See https://docs.vllm.ai/en/stable/features/reasoning_outputs.html for reasoning content.      |
| Qwen/Qwen3-32B                               | Text-generation              | ✅        | ✅       |       | ✅        | 16G    |  64.4/160G | 4     | 32.8B | bf16  | See https://docs.vllm.ai/en/stable/features/reasoning_outputs.html for reasoning content.      |
| Qwen/Qwen2.5-72B                             | Text-generation              | ✅        |          |       |           | 16G    | 144.8/320G | 4     | 72.7B | bf16  | Possible to fit on 2x80B by decreasing `max_model_len` or increasing `gpu_memory_utilization`. |
| Qwen/Qwen2.5-72B-Instruct                    | Text-generation              | ✅        | ✅       |       |           | 16G    | 144.8/320g | 4     | 72.7B | bf16  | Possible to fit on 2x80B by decreasing `max_model_len` or increasing `gpu_memory_utilization`. |
| Qwen/Qwen2.5-32B                             | Text-generation              | ✅        |          |       |           | 16G    |   63.1/80G | 4     | 32.8B | bf16  |                                                                                                |
| Qwen/Qwen2.5-32B-Instruct                    | Text-generation              | ✅        | ✅       |       |           | 16G    |   63.1/80G | 4     | 32.8B | bf16  |                                                                                                |
| google/gemma-3-27b-it                        | Text-generation              | ✅        | ✅       | ✅    |           | 16G    |   54.1/80G | 4     | 27.4B | bf16  |                                                                                                |
| google/gemma-3-1b-it                         | Text-generation              | ✅        | ✅       | ✅    |           | 8G     |       /10G | 4     | 27.4B | bf16  |                                                                                                |
| meta-llama/Llama-4-Scout-17B-16E-Instruct    | Text-generation              | ✅        | ✅       | ✅    |           | 32G    |      /320G | 4     |  109B | bf16  | Supports multimodal inputs. See https://docs.vllm.ai/en/latest/features/multimodal_inputs.html#online-serving. |
| meta-llama/Llama-4-Scout-17B-16E             | Text-generation              | ✅        |          | ✅    |           | 32G    |      /320G | 4     |  109B | bf16  | Supports multimodal inputs. See https://docs.vllm.ai/en/latest/features/multimodal_inputs.html#online-serving. |
| meta-llama/Llama-3.3-70B-Instruct            | Text-generation              | ✅        | ✅       | ✅    |           | 16G    | 140.4/320G | 4     | 70.6B | bf16  |                                                                                                |
| deepseek-ai/DeepSeek-R1-Distill-Llama-70B    | Text generation              | ✅        | ✅       |       | ✅        | 16G    | 141.2/320G | 4     | 70.6B | bf16  | See https://docs.vllm.ai/en/stable/features/reasoning_outputs.html for reasoning content.      |
| deepseek-ai/DeepSeek-R1-Distill-Qwen-32B     | Text generation              | ✅        | ✅       |       | ✅        | 16G    |   64.6/80G | 4     | 32.8B | bf16  | See https://docs.vllm.ai/en/stable/features/reasoning_outputs.html for reasoning content.      |
| deepseek-ai/DeepSeek-V2-Lite                 | Text generation              | ✅        |          |       |           | 16G    |   30.5/40G | 4     | 15.7B | bf16  |                                                                                                |
| deepseek-ai/DeepSeek-V2-Lite-Chat            | Text generation              | ✅        | ✅       |       |           | 16G    |   30.5/40G | 4     | 15.7B | bf16  |                                                                                                |
| openai/whisper-large-v3                      | Automatic-speech-recognition | ✅        |          |       |           | -      |    3.6/10G | 1     | 1.54B | f16   |                                                                                                |



<!--
| Qwen/Qwen2.5-Omni-7B                         | Text-generation              | ✅        | ✅       |       |           |        |            |       | 10.7B | f32, bf16 | Supports multimodal inputs. See https://docs.vllm.ai/en/latest/features/multimodal_inputs.html#online-serving. |
| Qwen/Qwen3-14B                               | Text-generation              | ✅        | ✅       |       |           |        |            |       | 14.8B | bf16  |                                                                                           |
| Qwen/Qwen3-8B                                | Text-generation              | ✅        | ✅       |       |           |        |            |       |  8.2B | bf16  |                                                                                           |
| google/gemma-3-1b-it                         | Text-generation              | ✅        | ✅       | ✅    |           | -      | /20G    | 1     |   1.0B | bf16  | Unknown error attempting to run on MIG. |
| meta-llama/Llama-3.2-1B                      | Text-generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-1B-Instruct             | Text-generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-3B                      | Text-generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-3B-Instruct             | Text-generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.1-8B                      | Text generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.1-8B-Instruct             | Text generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.1-70B                     | Text generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.1-70B-Instruct            | Text generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Meta-Llama-3-8B                   | Text generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Meta-Llama-3-70B                  | Text generation              | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Meta-Llama-3-8B-Instruct          | Text generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Meta-Llama-3-70B-Instruct         | Text generation              | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-11B-Vision              | Image-text-to-text           | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-11B-Vision-Instruct     | Image-text-to-text           | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-90B-Vision              | Image-text-to-text           | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| meta-llama/Llama-3.2-90B-Vision-Instruct     | Image-text-to-text           | ✅        | ✅       | ✅    |           |        |            |       |       |       |                                                                                           |
| stabilityai/stable-diffusion-3.5-large       | Text-to-image                | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| stabilityai/stable-diffusion-3.5-medium      | Text-to-image                | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| stabilityai/stable-diffusion-3-medium        | Text-to-image                | ✅        |          | ✅    |           |        |            |       |       |       |                                                                                           |
| openai/whisper-base                          | Automatic-speech-recognition | ✅        |          |       |           | -      |    ?/10G   | 1     |   72M | f32   |                                                                                           |
| openai/whisper-small                         | Automatic-speech-recognition | ✅        |          |       |           | -      |  0.6/10G   | 1     |  242M | f32   |                                                                                           |
| openai/whisper-medium                        | Automatic-speech-recognition | ✅        |          |       |           | -      | 1.54/10G   | 1     |  764M | f32   |                                                                                           |
-->

## Want to learn more?
You can find additional details and examples on our official [documentation page](https://princeton-ddss.github.io/blackfish/).
