# Installation Guide

If your HPC administrator has added Blackfish OnDemand to your Open OnDemand portal, then you can already use Blackfish on your cluster—congratulations! 🎉 Otherwise, if Blackfish OnDemand has not been set up, or if you would like to use Blackfish from your laptop, follow the instructions below.

!!! note

    Blackfish does **not** need to be installed on your HPC cluster in order to run services on the cluster. However, if you want to run Blackfish on a login node, it will need to be installed for your cluster account as well. Blackfish installations on different machines do not synchronize application data.

## Prerequisites

### Supported Platforms

Blackfish is tested on **Linux** and **macOS**. Mileage may vary on Windows machines.

### Container Provider

In order to facilitate reproducibility and minimize dependencies, Blackfish uses [Docker](https://docs.docker.com/desktop/) and [Apptainer](https://apptainer.org/docs/admin/main/installation.html) to run service containers. HPC-based services require Apptainer to be installed on your university cluster.

### Container Images

Blackfish does not ship container images. Your HPC admin may provide these in a shared cache directory. Otherwise, you will need to obtain them yourself. See [Images](management.md#images) for details.

## Install Blackfish

### pip

```shell
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install blackfish-ai
```

### uv

```shell
uv venv
uv pip install blackfish-ai
```

Verify the installation:

```shell
blackfish version
```

## Setup

Before you use Blackfish for the first time, you need to initialize it:

```shell
blackfish init
```

This command walks you through creating a default profile. The steps differ depending on where you are installing Blackfish.

### On your laptop

If you are installing Blackfish on your laptop, you will first need to configure password-less SSH access to your cluster.

#### SSH Configuration

On many systems, this is simple to set up with the `ssh-keygen` and `ssh-copy-id` utilities. First, make sure that you are connected to your institution's network (or VPN), then type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC server you need access to. You now have password-less access to your HPC server!

#### Profile

Your default profile should point to your cluster's hostname:

```shell
# > name: default
# > type: slurm
# > host: cluster.organization.edu
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /shared/.blackfish
```

!!! note

    Blackfish will attempt to connect to the remote host during profile creation. Make sure you have enabled password-less SSH access and are connected to your institution's network or VPN before proceeding.

### On the cluster

Log into your cluster and install Blackfish as described above. Your default profile should use `localhost` as the host:

```shell
# > name: default
# > type: slurm
# > host: localhost
# > user: shamu
# > home: /home/shamu/.blackfish
# > cache: /shared/.blackfish
```

### Profile details

The `home` directory must be a directory for which your user has read-write permissions; the `cache` directory only requires read permissions. You can modify this profile or add additional profiles later. See [Profiles](../usage/cli.md#profiles) for details.

!!! tip

    Models and virtual environments can be large. On HPC systems where `~` has a strict quota, consider using a scratch or project directory for your virtual environment and setting `home` to a location with sufficient storage.
