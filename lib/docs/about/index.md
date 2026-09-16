---
hide:
  - toc
---

# What is Blackfish AI?

Blackfish helps researchers use state-of-the-art, open source artificial intelligence and machine learning models on high-performance computing (HPC) clusters. With Blackfish, researchers can spin up their own *private*, OpenAI-compatible inference APIs, and run large-scale batch inference jobs using HPC resources already available on their campus. Blackfish aims to provide an alternative to private public cloud services, such as ChatGPT, Amazon Transcribe, etc. that is safe to use with restricted data, prioritizes customization and replicability, and saves research funds. 

<div class="grid cards" markdown>

-   🚀 &nbsp; __OpenAI-compatible APIs__

    ---

    Launch `vllm` on high-powered GPUs and pointing your existing `openai` scripts at them works out of the box — no new SDK, no rewrite required.

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

    Ships with a CLI, web UI, and Python API. Open OnDemand provides researchers access via a web browser —  zero install required.

-   ⚙️ &nbsp; __Built for Slurm__

    ---

    Apptainer containers, shared model and image caches, and admin-defined resource tiers that constrain what users resource requests.

</div>

## What problem does this solve?

Researchers increasingly rely on AI to unlock new sources of data and fill the role of non-specialist assistants, e.g., coding data sources. Public cloud providers have for years offered AI services that perform essential data preprocessing tasks, such as transcribing recordings, performing object detection tasks, and labeling content. While relatively easy to use, these services:

- can be prohibitively expensive,
- not customizable,
- are opaque, and suffer from model creep / non-reproducible,
- are no longer clearly superior to open source models,
- may not satisfy data handling requiremenets,

The tools to perform such tasks locally are now widely available, but their adoption is limited to researchers that have the time, funding, and inclination to learn how to use them. Moreover, most state-of-the-art AI models rely on high-powered GPUs, which are typically only available to researchers through their institution's cluster, presenting a further hurdle to adoption.

### Adoption
Blackfish aims to make it easy for researchers to realize the benefits of open source models by automating the tricky bits of deployment and providing standardized workflows to save researchers time and energy.

Researchers should focus on research, not tooling. We try to meet researchers where they're at by providing multiple ways to work with Blackfish, including a Python API, a command-line tool (CLI), and a browser-based user interface (UI).

Don't want to install anything? Ask your HPC admins to install [Blackfish OnDemand](https://github.com/princeton-ddss/blackfish-ondemand).

### Transparency

You decide what model to run (down to the Git commit) and how you want it configured. There are no unexpected (or undetected) changes in performance because the model is always the same. All services are *private*, so you know exactly how your data is being handled.

### Privacy

Researchers often work under data restrictions that preclude the use of public cloud offerings. Blackfish runs entirely on your cluster and (optionally) laptop. Data never leaves your servers. APIs and batch jobs run on compute allocataions owned and authenticated by the user, and the codebase is open source so you can see exactly how all data is handled.

## Next Steps

Ready to get started? The [setup guide](../getting-started/installation.md) walks through each step in detail.

## Acknowledgements

Blackfish is maintained by research software engineers at the [Data Driven Social Science Initiative](https://ddss.princeton.edu/), a part of [Data and Intelligent Systems](http://dais.princeton.edu/) at Princeton University.

<div class="bf-logos" markdown>

[![Data Driven Social Science Initiative](../assets/img/ddss-logo.png){ .bf-logo }](https://ddss.princeton.edu/)
[![Data and Intelligent Systems](../assets/img/dais-logo.png){ .bf-logo }](http://dais.princeton.edu/)

</div>
