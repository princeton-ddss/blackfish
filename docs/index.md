# Welcome to Blackfish!
Blackfish is an open source "AI-as-a-Service" (AIaaS) platform that helps researchers
use state-of-the-art, open source artificial intelligence and machine learning models.
With Blackfish, researchers can spin up their own equivalent of popular public cloud AI
services (e.g., Amazon Transcribe) using the high-performance computing (HPC) resources
already available on their campus.[^1]

## Quickstart
```shell
pip install blackfish
blackfish init
blackfish start
blackfish run <job_config> text-generate <container_config>
curl ...
```

## How does Blackfish work?
Blackfish consists of three primary components: the core API ("Blackfish API"), a command-line
interface ("Blackfish CLI") and a (graphical) user interface ("Blackfish UI"). The Blackfish
API performs all essential operations while the Blackfish CLI and UI provide convenient methods
for interacting with the Blackfish API. Essentially, the Blackfish API automates the process of
hosting AI models as APIs. That is, a user tells the Blackfish API—directly or via an interface—the
model she wants to use and the Blackfish API creates a "service API" running that model. The researcher
that starts the service owns the API: they have exclusive access to its use and "own" the resources
(e.g., CPU and GPU memory) required to deploy it.

In addition to starting the service, Blackfish keeps track of the service's status and allows the
researcher to stop the service when she is done using it.

In general, the service API will not be running on the same machine as the Blackfish application.
Instead, when the user requests a model, she will also specify a host for that model. The service API
runs on the specifieid host and Blackfish takes care of ensuring that the interface is able to communicate
with the remote service API.

![image](assets/img/architecture-slurm.jpg)

**Figure** The Blackfish architecture for running remote service APIs on a Slurm cluster.

## Requirements
Blackfish requires either Python *or* Docker installed to run on a desktop/laptop. Blackfish
can also be installed as a "no code" solution: ask your HPC system administrators about
[enabling Blackfish through OnDemand]().

## Acknowledgements
Blackfish is developed by research software engineers at Princeton University's
Data Driven Social Science Initiative.

[^1]: Support is currently limited to clusters running the Slurm job manager.
