---
hide:
  - toc
---

# What is Blackfish AI?

Blackfish helps researchers use state-of-the-art, open source artificial intelligence and machine learning models on high-performance computing (HPC) clusters. With Blackfish, researchers can spin up their own *private*, OpenAI-compatible inference APIs, and run large-scale batch inference jobs using HPC resources already available on their campus. Blackfish aims to provide an alternative to public cloud services, such as ChatGPT, Amazon Transcribe, etc. that is safe to use with restricted data, prioritizes customization and replicability, and saves research funds.

<div class="grid cards" markdown>

-   🚀 &nbsp; __OpenAI-compatible APIs__

    ---

    Launch `vllm` on high-powered GPUs and point your existing `openai` scripts at them — it works out of the box — no new SDK, no rewrite required.

-   🔒 &nbsp; __Private by design__

    ---

    Designed for IRB-restricted, DUA-bound, or otherwise unshippable data. Models run on your institution's cluster and your allocation — nothing leaves the cluster.

-   📌 &nbsp; __Reproducible to the commit__

    ---

    Pin a model and API version and your run today is repeatable in a year — no silent version creep, and you have full control over API settings.

-   🍪 &nbsp; __Point-and-click batching__

    ---

    Transcribe, translate, detect, OCR, or prompt across an entire folder. Resumable across allocations, and it picks up files added in mid-run.

-   🎛️ &nbsp; __No installation necessary__

    ---

    Ships with a CLI, web UI, and Python API. Open OnDemand provides researchers access via a web browser — zero install required.

-   ⚙️ &nbsp; __Built for Slurm__

    ---

    Apptainer containers, shared model and image caches, and admin-defined resource tiers that offer users named hardware bundles.

</div>

## What problem does this solve?

Researchers increasingly rely on AI to unlock new sources of data and augment or replace non-specialist assistants, e.g., coding data sources. Public cloud providers have for years offered AI services that perform essential data preprocessing tasks, such as transcribing recordings, performing object detection tasks, and labeling content. While relatively easy to use, these services:

- can be prohibitively expensive,
- are opaque and not customizable,
- suffer from model creep, making results hard to reproduce,
- may not satisfy data handling requirements,
- and, for many research tasks, are no longer clearly better than open source alternatives.

For many preprocessing tasks research depends on — transcription, classification, annotation, extraction — open source models now perform comparably to commercial services, and sometimes better.[^1][^2][^3] In addition, they cost nothing to run on an institutional cluster, can be inspected and pinned to an exact version, and provide complete control over sensitive data. For researchers working under an IRB protocol or a data use agreement, open source may be the only game in town.

However, the benefits of open source come with their own costs. Researchers need to learn how to work with the HPC clusters that provide access to high-powered GPUs: writing Slurm batch scripts, running Apptainer containers, navigating Hugging Face cache layouts, setting up port forwarding off a compute node, and working out which GPU will fit a 70-billion parameter model. These barriers limit adoption to researchers with the time, funding, and inclination to keep up with a fast-moving ecosystem.

Blackfish automates the tricky parts of deployment and provides standardized workflows so that launching a private inference API or running batch inference against a collection of documents is a single command — or a few clicks. Researchers should focus on their research, not on an evolving toolset. We meet researchers where they are by providing multiple ways to work, including a Python API, a command-line tool (CLI), and a browser-based user interface (UI). And because everything runs on your cluster, under your allocation, and using the model version you chose, you keep the transparency, privacy, and reproducibility benefits of open source.

!!! tip
    Blackfish offers a zero-installation option for users that are uncomfortable managing Python environments. Ask your HPC cluster admins about adding Blackfish to Open OnDemand. For admins, we offer a [template app](https://github.com/princeton-ddss/blackfish-ondemand) to get you started.

[^1]: Ferraro, A., Galli, A., La Gatta, V., & Postiglione, M. (2023). [Benchmarking open source and paid services for speech to text: an analysis of quality and input variety](https://doi.org/10.3389/fdata.2023.1210559). *Frontiers in Big Data*, 6.

[^2]: Alizadeh et al. (2023), [Open-Source LLMs for Text Annotation](https://arxiv.org/abs/2307.02179).

[^3]: Epoch AI, [Open models lag state-of-the-art closed models by 4 months](https://epoch.ai/data-insights/open-closed-eci-gap) (January 2026).

## Next Steps

Ready to get started? Our [getting started](../getting-started/installation.md) page walks through each step in detail.

## Acknowledgements

Blackfish is maintained by research software engineers at the [Data Driven Social Science Initiative](https://ddss.princeton.edu/), a part of [Data and Intelligent Systems](http://dais.princeton.edu/) at Princeton University.

<div class="bf-logos" markdown>

[![Data Driven Social Science Initiative](../assets/img/ddss-logo.png){ .bf-logo }](https://ddss.princeton.edu/)
[![Data and Intelligent Systems](../assets/img/dais-logo.png){ .bf-logo }](http://dais.princeton.edu/)

</div>
