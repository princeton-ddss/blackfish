# Basic Usage

Once Blackfish is [installed](installation.md) and running (via
`blackfish start`), you're ready to launch an inference service.

## Step 1 - Obtain a model

List what's already available in your shared cache directory:

```shell
blackfish model ls --refresh
```

If no models are present, download a small test model (this shouldn't take long):

```shell
blackfish model add TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

## Step 2 - Start a service

Services are REST APIs that run on your cluster and are configured so that you can reach them from wherever Blackfish is running (your laptop or a login node).

```shell
blackfish run \
  --gres 1 \
  --time 00:30:00 \
  text-generation TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --api-key sealsaretasty
```

`--gres` and `--time` are the Slurm resources; `text-generation` and the model
ID say what to serve; `--api-key` secures the service's own API.

!!! tip "Slurm resources"

    In most cases, the only essential resources to specify are the number of GPUs needed (`--gres`) and the duration of the service job (`--time`). Depending on your cluster policies, you may also need to specify an `--account`, `--partition`, or add a `--constraint` (e.g., `--constraint 'gpu80'`).

This command will check that the requested model is available and print a confirmation message on success. That message will display a service ID that uniquely identifies the service.

Services generally take 1-10 minutes to spin up, depending on the size of the model requested. The `blackfish ls` command displays the status of all active services. Once your new service indicates a `HEALTHY` status, it's ready to use.

## Step 3 - Submit a request

The `text-generation` service uses `vllm`—a fast, OpenAI-compatible inference
server. You can send it requests the same way you would work with ChatGPT.

=== "Python"

    ```python
    from openai import OpenAI

    client = OpenAI(
        base_url="http://localhost:8080/v1",
        api_key="sealsaretasty",
    )

    response = client.chat.completions.create(
        model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        messages=[
            {"role": "system", "content": "You are an expert marine biologist."},
            {"role": "user", "content": "Why are orcas so awesome?"},
        ],
        max_completion_tokens=100,
        temperature=0.1,
    )
    print(response.choices[0].message.content)
    ```

=== "R"

    ```r
    library(ellmer)

    chat <- chat_vllm(
      base_url = "http://localhost:8080",
      model = "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
      credentials = "sealsaretasty",
      system_prompt = "You are an expert marine biologist."
    )

    chat$chat("Why are orcas so awesome?")
    ```

=== "Shell"

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

!!! note "Hosts and ports"

    `8080` is the default port for services, so this is usually the correct port to include in the `base_url`, but Blackfish will automatically look for an available port if the default is taken. Replace `8080` with the port listed by `blackfish ls`. Services are __always__ exposed at `localhost` regardless of where they are actually running.

## Step 4 - Stop the service

Services run until they reach their specified `--time` limit. To avoid running an idle Slurm job, run

```shell
blackfish stop <ID>
```

to cancel your job and return its resources to the cluster.

## Next steps

That concludes running a single service from the command line. From here:

- The [Command Line](../usage/cli.md) guide covers the rest of the CLI,
  including batch jobs.
- The [Web Interface](../usage/ui.md) guide demonstrates common tasks in the browser-based UI.
- The [Python API](../usage/client.md)
  guide shows how to programmatically start and monitor services.
