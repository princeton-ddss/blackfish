# Adopting Blackfish

This page is for HPC administrators deciding whether to support Blackfish on a
cluster. It covers what users install, what the cluster has to provide, and how
the work lands in your scheduler.

For how the components fit together, see the
[Architecture Overview](architecture.md).

## What users install

Blackfish is not deployed centrally. Each researcher installs the
`blackfish-ai` Python package into their own environment and runs it from their
laptop or a login node. There is no service to register, no privileged
component, and nothing persistent on the cluster between jobs.

That means adopting Blackfish is mostly a question of what you allow and what
you provide, rather than what you operate.

## What the cluster has to provide

- **Slurm**, for running services on compute nodes.
- **Apptainer** on the compute nodes. Services and batch jobs run inside
  containers, invoked as `apptainer run` from the generated job script.
- **SSH**, when a user runs Blackfish off the cluster. From a laptop it
  submits jobs and polls their status over SSH; from a login node it calls
  Slurm directly. Either way it opens an SSH tunnel to reach a running
  service.
- **Python 3.12 or newer** wherever a user runs Blackfish.

## What you provide

Three things are worth setting up centrally, though none is required:

- **A shared cache.** Blackfish does not ship container images, and model
  weights are large. Staging both in a shared directory means users download
  them once rather than each. See [Cache Management](cache.md).
- **Resource tiers.** A `resource_specs.yaml` in the shared cache lets the UI
  offer named hardware bundles — "Small", "Medium", "Large" — instead of raw
  Slurm flags. See [Resource Tiers](resource-tiers.md).
- **An Open OnDemand app.** Publishing Blackfish through OnDemand gives
  researchers a browser-based route with nothing to install, which suits users
  who would rather not manage a Python environment. We provide a
  [template app](https://github.com/princeton-ddss/blackfish-ondemand) to
  start from. It also runs Blackfish on the cluster itself, so the profile
  uses `host=localhost` — the configuration under which model downloads are
  supported.

Without any of these, Blackfish still works: users install it themselves, fall
back to their own cache directories, and specify resources directly.

## Security model

### Process identity

Blackfish runs as the user who starts it, and submits jobs as that user. It
stores no passwords or private keys. When it reaches the cluster over SSH, it
runs with `PasswordAuthentication=no` and relies on the key or Kerberos
credentials the user already has. A user can therefore do nothing through
Blackfish that they could not do with `sbatch` and `ssh` directly.

### Network exposure

The REST API listens on port 8000 bound to `localhost` by default, so it is
reachable only from the machine running it and is not exposed to the network.
Services running on compute nodes are reached through an SSH tunnel that
Blackfish opens; no listening port has to be opened on the cluster for them.

### Authentication

Authentication is on by default. Every API request requires a bearer token,
which Blackfish generates at start-up and writes to
`$BLACKFISH_HOME_DIR/auth_token` at mode `0600` — readable only by the user
running it, which is what keeps it private on a shared machine. The CLI reads
the same file, so it needs no setup of its own.

Debug mode (`BLACKFISH_DEBUG=1`) turns authentication off entirely and is for
development only; on a login node it leaves the API open to every other user
on that host.

### Service authentication

The token above protects the Blackfish API. A running service exposes its own
API on a compute node, and that one takes a separate key: `--api-key` on
`blackfish run`, or the field in the web launcher. Blackfish stores the key
with the service and attaches it when proxying requests.

!!! note "Services are open unless a key is set"

    The key is optional. A service started without one accepts requests from
    anyone who can reach its port on the compute node — worth mentioning to
    users when you announce Blackfish.

### Data residency

Inference runs on your hardware, against models staged on your filesystem.
Prompts, audio and other inputs are read from the cluster filesystem and
processed on the compute node — they are not sent to a third-party service.
Downloading a model from Hugging Face is a separate, explicit step; see
[Cache Management](cache.md).

## Resource accounting

Services and batch jobs are ordinary Slurm jobs. The generated script carries
the standard directives:

```bash
#SBATCH --job-name=...
#SBATCH --nodes=...
#SBATCH --ntasks-per-node=...
#SBATCH --mem=...
#SBATCH --time=...
#SBATCH --gres=gpu:...
#SBATCH --constraint=...
#SBATCH --partition=...
#SBATCH --account=...
```

Because jobs are submitted as the requesting user with an explicit `--account`
and `--partition`, existing fairshare, QoS and partition limits apply
unchanged. Blackfish adds no scheduling path of its own and cannot exceed a
user's allocation. Jobs appear in `squeue` and `sacct` like any other.

[Resource Tiers](resource-tiers.md) shape what the interface offers, not what
the API accepts — a request can still specify its own resources, and Slurm
remains the thing that enforces limits.

## Storage

Each user keeps configuration, logs and a SQLite database in
`BLACKFISH_HOME_DIR` (`~/.blackfish` by default) on the machine running
Blackfish. There is no database server to provision.

Model weights, container images and job files live wherever a profile's
`home_dir` and `cache_dir` point — typically a shared filesystem you nominate.
Those are the directories that grow, and the ones worth putting on a quota you
are comfortable with.
