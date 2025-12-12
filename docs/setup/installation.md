# Installation Guide

If your HPC administrator has added Blackfish Ondemand to your Open Ondemand portal, then you can already use Blackfish on your cluster—congratulations! 🎉 Otherwise, if Blackfish Ondemand has not been setup, or if you would like to use Blackfish from your laptop, follow the instructions below.

Note that Blackfish does **not** need to be installed on your HPC cluster in order to run services on the cluster. However, if you want to run Blackfish on a login node, it will need to be installed for your cluster account as well.

!!! note

    Blackfish installations on different machines do not synchronize application data. In particular, Blackfish running on your laptop does not know about services started by Blackfish running on your HPC cluster.

## Prerequisites

### Supported Platforms

Blackfish is tested on **Linux** and **macOS**. Mileage may vary on Windows machines.

### Container Provider

In order facilitate reproducibility and minimize dependencies, Blackfish uses [Docker](https://docs.docker.com/desktop/) and [Apptainer](https://apptainer.org/docs/admin/main/installation.html) to run service containers. HPC-based services require Apptainer; local services support both Docker and Apptainer, but Apptainer only runs on Linux systems.

### SSH Configuration

Using Blackfish from your laptop requires a seamless (i.e., password-less) method of communicating with remote clusters. On many systems, this is simple to setup with the `ssh-keygen` and `ssh-copy-id` utilitites. First, make sure that you are connected to your institution's network (or VPN), then type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC server you need access to. You now have password-less access to your HPC server!

!!! warning

    Blackfish depends on seamless interaction with your university's HPC cluster. Before proceeding, make sure that you have enabled password-less login and are connected to your institutions network or VPN, if required.

## Installation

### pip

```shell
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install blackfish-ai
```

### uv

```shell
uv venv
uv add blackfish-ai
```

### Initialization

Before you use Blackfish for the first time, you need to initialize it:

```shell
blackfish init
```

Answer the prompts to create a new default profile. If you are setting up Blackfish on a cluster, your default profile should be a "local" profile:

```shell
# > name: default
# > type: local
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /shared/.blackfish
```

If you are installing Blackfish on your laptop, then you probably want your default profile to be a "Slurm" profile:

```shell
# > name: default
# > type: slurm
# > host: cluster.organization.edu
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /shared/.blackfish
```

The home directory supplied must be a directory for which your user has read-write permissions; the cache directory only requires read permissions.

!!! note

    If your default profile connects to an HPC cluster, Blackfish will attempt to set up the remote host at this point. Profile creation will fail if you're unable to connect to the HPC server and you'll need to re-run the `blackfish init` command or create a profile with `blackfish profile create`.
