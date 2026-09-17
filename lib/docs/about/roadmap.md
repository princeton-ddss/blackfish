# Roadmap

## v1.0

The first stable release. Blackfish runs open source models on your own
hardware and exposes them through OpenAI-compatible APIs.

**Services**

- [x] **Text generation** backed by [vLLM](https://github.com/vllm-project/vllm),
  serving an OpenAI-compatible chat completions API.
- [x] **Speech recognition** backed by
  [speech-recognition-inference](https://github.com/princeton-ddss/speech-recognition-inference).
- [x] Container image version pinning, so a service can be reproduced later with
  the same runtime.

**Batch Jobs**

- [x] Task-based pipelines run in the
  [tigerflow-ml](https://github.com/princeton-ddss/tigerflow-ml) image:
  `chat`, `embed`, `transcribe`, `translate`, `detect` and `ocr`.
- [x] Resume or restart terminal jobs without resubmitting from scratch.

**Interfaces**

- [x] A command-line interface to the REST API.
- [x] A browser-based user interface to the REST API.
- [x] A Python API that directly manages services without the REST server running.

**Profiles**

- [x] Local and Slurm profiles, with renames, an explicit default, and
  `blackfish profile repair` to reconcile an existing installation.
- [x] Remote execution over SSH, including tunnels to services on compute nodes.

**Admin**

- [x] Shared image and model caches, so a cluster stages files once for all users.
- [x] Resource tiers that present named hardware bundles instead of raw Slurm
  flags.

## v1.1

**Services**

- [ ] **Object detection**.
- [ ] Scalable, multi-instance APIs.
- [ ] Auto job resubmission.
  

**Batch Jobs**

- [ ] Auto-resubmission

**Web UI**

- [ ] Display token usage with proactive context length monitoring.
- [ ] Report Slurm job logs and errors.
- [ ] Display service metrics.
- [ ] Support reasoning/thinking output.
- [ ] Classification and extraction chat interfaces.

**Python API**

- [ ] Improved ergonomics.
  
**Admin**

- [ ] Built-in container image management.

## v1.2

- [ ] Auto-convert interactive sessions to batch jobs.
- [ ] Register external API endpoints as services.
