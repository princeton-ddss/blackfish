![GitHub Release](https://img.shields.io/github/v/release/princeton-ddss/blackfish)
![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/princeton-ddss/blackfish/lib.yml)
![coverage](lib/docs/assets/img/coverage.svg)
[![PyPI](https://img.shields.io/pypi/v/blackfish-ai.svg)](https://pypi.python.org/pypi/blackfish-ai)
[![License](https://img.shields.io/github/license/princeton-ddss/blackfish)](https://github.com/princeton-ddss/blackfish)

# Blackfish AI

![album-cover](lib/docs/assets/img/album-cover.png)

Blackfish helps researchers use state-of-the-art, open source artificial intelligence and machine learning models on high-performance computing (HPC) clusters. With Blackfish, researchers can spin up their own private, OpenAI-compatible inference APIs and run large-scale batch inference jobs using HPC resources already available on their campus. Blackfish aims to provide an alternative to public cloud services such as ChatGPT and Amazon Transcribe that is safe to use with restricted data, prioritizes customization and replicability, and saves research funds.

- 🚀 **OpenAI-compatible APIs**: launch `vllm` on high-powered GPUs and point your existing `openai` scripts at them.
- 🔒 **Private by design**: models run on your institution's cluster and your allocation, so data never leaves the cluster.
- 📌 **Reproducible to the commit**: pin a model and API version, and your run today is repeatable in a year.
- 🍪 **Point-and-click batching**: transcribe, translate, detect, OCR, or prompt across an entire folder, resumable across allocations.
- 🎛️ **No installation necessary**: use the CLI, web UI, or Python API, or reach the UI from a browser through Open OnDemand.
- ⚙️ **Built for Slurm**: Apptainer containers, shared model and image caches, and admin-defined resource tiers.

## Why Blackfish?

Public cloud AI services are easy to use, but they can be prohibitively expensive, change models without notice, and may not satisfy data handling requirements. For many research tasks (transcription, classification, annotation, extraction), open source models now perform comparably and cost nothing to run on an institutional cluster.

Blackfish automates the annoying bits (Slurm scripts, Apptainer containers, Hugging Face cache layouts, port forwarding off compute nodes, and sizing GPUs to models), so launching a private inference API or running batch inference over a collection of files is a single command or a few clicks.

See our [About page](https://princeton-ddss.github.io/blackfish/latest/about/) to learn more.

## Getting Started

Blackfish is a `pip`-installable Python package:

```shell
pip install blackfish-ai
blackfish init   # create a profile
blackfish start  # launch the app
```

See [Installation](https://princeton-ddss.github.io/blackfish/latest/getting-started/installation/) and [Basic Usage](https://princeton-ddss.github.io/blackfish/latest/getting-started/basic-usage/) for a full walkthrough.

> [!TIP]
> Don't want to manage a Python environment? Ask your HPC admins to add [Blackfish OnDemand](https://github.com/princeton-ddss/blackfish-ondemand) to your cluster's Open OnDemand portal.

## Documentation

Our [documentation](https://princeton-ddss.github.io/blackfish/) covers:

- **User Guide**: the [command line](https://princeton-ddss.github.io/blackfish/latest/usage/cli/), [web interface](https://princeton-ddss.github.io/blackfish/latest/usage/ui/), and [Python API](https://princeton-ddss.github.io/blackfish/latest/usage/client/)
- **Admin Guide**: [architecture](https://princeton-ddss.github.io/blackfish/latest/admin/architecture/), [adopting Blackfish](https://princeton-ddss.github.io/blackfish/latest/admin/adopting/), [cache management](https://princeton-ddss.github.io/blackfish/latest/admin/cache/), and [resource tiers](https://princeton-ddss.github.io/blackfish/latest/admin/resource-tiers/)
- **Developer Guide**: the [overview](https://princeton-ddss.github.io/blackfish/latest/developer/) and API reference
- **[Roadmap](https://princeton-ddss.github.io/blackfish/latest/about/roadmap/)**: what's planned next

For worked examples, see [blackfish-examples](https://github.com/princeton-ddss/blackfish-examples).

## Development

This is a monorepo containing:

| Package | Description |
|---------|-------------|
| [lib/](lib/) | Python backend (`blackfish-ai`): CLI, server, services |
| [web/](web/) | Vite + React frontend (`blackfish-ui`): browser interface |

See the package READMEs for development setup, and [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Acknowledgements

Blackfish is maintained by research software engineers at the [Data Driven Social Science Initiative](https://ddss.princeton.edu/), a part of [Data and Intelligent Systems](http://dais.princeton.edu/) at Princeton University.
