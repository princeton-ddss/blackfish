# Getting Started

## Installation

### pip
```shell
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install blackfish
```

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
```shell
blackfish init
```

This command will ask you to create or modify a profile. If you've already run
the `init` command, then you can safely skip this step.

### Creating a profile
```shell
blackfish profile create
```

Follow the prompts. Support options for `type` are "slurm" or "local".

## Usage
Once you have initialized Blackfish and created a profile, you're ready to go.

### Starting Blackfish
Start the core Blackfish API:
```shell
blackfish start
```

Also start the Blackfish UI:
```shell
blackfish start --ui
```

### Obtaining services

### Obtaining models
```shell
blackfish pull <service>
```

### Starting a service
```shell
blackfish run [job_options] <service> [container_options]
```

```shell
blackfish run \
  --profile hpc \
  --mem 16 \
  --ntasks 4 \
  --gres 1 \
  --time 00:05 \
  text-generation \
  --model bigscience/bloom-560m \
```

!!! note

    If no `--revision` is provided, Blackfish automatically suggests the most recently
    available *downloaded* version of the requested model. This reduces the
    time-to-first-inference, but may not be desirable for your use case. Download the
    model *before* starting your service if you need the [most recent version]() available
    on Hugging Face.

!!! tip

    Add the `--dry-run` flag to any service command in order to preview the job Blackfish
    will submit to Slurm.

### Listing available services
```shell
blackfish ls
```

```shell
blackfish ls --filters image=<image>,status=<status>
```

### Calling a service
The details of calling a service depend on the service you are trying to connect to.
For the `text-generation` service, the primary endpoint is called like so:
```shell
curl 127.0.0.1:8081/generate \
  -X POST \
  -d '{"inputs": "Hello", "parameters": {"max_new_tokens": 20}}' \
  -H 'Content-Type: application/json'
```
Alternatively, call the service through the UI or CLI, which will handle the connection
details for you, but only supports the core features of each service API.

### Stopping a service
```shell
blackfish stop <service_id>
```

Services remain in your list of services for future reference. You can delete
expired services with the `rm` command:
```shell
blackfish rm <service_id>
```

### Selecting a model
```shell
blackfish models ls
blackfish models ls --profile <profile>
blackfish models ls --refresh
```

### Downloading a model

### Getting help
Add the `--help` argument to any command in order to print a documentation on its
usage.
```shell
blackfish --help
```