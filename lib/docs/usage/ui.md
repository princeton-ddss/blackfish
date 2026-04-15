# Web Interface

Blackfish ships with a browser-based UI served alongside the API at `http://localhost:8000` (or your configured host/port). The UI and the CLI are alternative front-ends to the same API — most users will prefer the UI for interactive work (chat, model browsing, settings) and the CLI for scripting and automation.

## Features

- **Services**
    - **Text Generation** — chat or completion against a running vLLM
      service, with text/code file attachments as conversation context.
    - **Speech Recognition** — transcribe audio against a running
      Whisper service.
    - More services on the way.
- **Models** — inventory, download, and delete models per profile.
- **Files** — browse, upload, download, and delete files on a remote
  Slurm profile over SFTP.
- **Batch Jobs**
    - **Transcription** — transcribe audio files using Whisper.
    - **Translation** — translate text files between languages.
    - **Object Detection** — zero-shot object detection on images.
    - **OCR** — extract text from images or scanned pages.
- **Settings** — profile management, theme preference, and Hugging
  Face token management.

## Walkthroughs

### Launch a service

From any service page, click :heroicons-rocket-launch: in the service container header to open the launcher.

- Fill in the Service modal:
    - **Name** — a suggestion is pre-populated; leave it or rename.
    - **Model** and **Revision** — pick from the available list.
    - On a Slurm profile, pick a **Partition**, a **Resource tier**, and
      set the **Time** limit. **Account** is available under the expandable **Advanced** section.
- Click **Launch**. The service status badge moves from `PENDING` →
  `STARTING` → `HEALTHY`. The time to reach `HEALTHY` depends on Slurm
  queue wait times and model size. Once the job starts, small models
  (~1B) typically load in about a minute, while large models (~70B) can
  take 5–10 minutes.
- When you're done, click :heroicons-stop: in the service container
  header. The service transitions to `STOPPED`; :heroicons-trash:
  appears next to it so you can remove the record entirely.

#### Text Generation

Once the service is `HEALTHY`, the chat text area at the bottom of
the page becomes active:

- Type a message and press **Enter** to send (**Shift+Enter** for
  a newline).
- Click :heroicons-adjustments-horizontal: in the toolbar to open the
  parameters panel — tune temperature, max tokens, presence and
  frequency penalties, stop sequences, and seed.
- Click :heroicons-code-bracket: in the toolbar to open the code
  snippet modal, which shows the equivalent request body in
  Python, R, and Bash.

#### Speech Recognition

Once the service is `HEALTHY`:

- Use the file browser to select an audio file from the service's
  mount directory. A preview player appears below the browser.
- Click :heroicons-adjustments-horizontal: to set the transcription
  language.
- Click the submit button to start transcription. The result appears
  in the output area once processing completes.

### Create a batch job

Batch jobs require a Slurm profile — the Jobs page is only accessible
when a Slurm profile is selected.

- From the **Jobs** page, click **New Job** — this is a dropdown menu.
- Pick the task you want to run: **Transcription**, **Translation**,
  **Object Detection**, or **OCR**.
- The New Job modal opens as a stepper:
    1. **Model** — pick a model and revision.
    2. **Task parameters** — fields vary by task:
        - *Transcription*: language, output format.
        - *Translation*: source language, target language.
        - *Object Detection*: labels, threshold, batch size, sample FPS.
        - *OCR*: output format.
    3. **Data** — use the directory browser to select an input directory
       on the cluster and an output directory to write results to. Set
       the input file extension to filter inputs.
    4. **Resources** — pick a **Partition**, a **Resource tier**, and the
       maximum number of concurrent **Workers**. **Account**, worker and
       client timeouts are available under the expandable **Advanced** section.
- Click **Submit**. The modal closes and the new job appears at the top
  of the Jobs table with a status of `RUNNING`.
- The progress column shows finished/total counts as workers complete
  files. The job transitions to `STOPPED` when all files have been
  processed or if the job is manually stopped.
- Click a job row to view file-level details. Each row shows the
  input and output file names, start time, elapsed time, and status (success
  or failure). Click a file row to open a side panel with a preview of
  the output and additional details.

### Manage models

- Open the **Models** page from the sidebar.
- The table lists every model available under the selected profile,
  with columns for name, size, parameter count, task, and location.
- **To download a new model**:
    - Click :heroicons-plus: in the header.
    - A dialog asks for a **repo ID** (e.g. `google/gemma-3-27b-it`)
      and an optional **revision** (defaults to `main`).
    - Click **Download**. The model appears in the table with a status
      indicator while the download runs. Large models can take a
      significant amount of time to download.
- **To delete a model**:
    - Hover the row and click the **action menu**.
    - Choose **Delete** and confirm.

!!! note

    Model downloads and deletions are only supported for Slurm profiles with `host=localhost` (e.g. Open OnDemand sessions running on the cluster head node). Remote Slurm profiles display a banner explaining that model management must happen on the cluster directly.

### Change settings

- Click :heroicons-cog-6-tooth: in the navbar to open the Settings slide-over.
- The panel has four sections: **Profiles**, **Hugging Face**,
  **App Configuration**, and **Theme**.

#### Profiles

- The top section lists every profile you've configured, with a badge
  showing the type (Slurm or Local).
- **To add a new profile**:
    - Click **Add Profile** — a form expands inline.
    - Fill in:
        - **Name** — must be unique and is immutable once created.
        - **Type** — Slurm or Local.
        - **Home directory** — where Blackfish stores profile state on
          the target machine, e.g., `/home/shamu/.blackfish`.
        - **Cache directory** — where cached models and SIF images
          live, e.g., `/shared/.blackfish`.
        - For Slurm profiles: **Host** (e.g., `cluster.university.edu`
          or `localhost`), **User** (your cluster username), and an
          optional **Python path** (e.g., `python3` or
          `/usr/local/bin/python3.12`) if the cluster doesn't have
          Python on `$PATH`.
    - Click **Create**.
- **To edit a profile**: click :heroicons-pencil: on the row; the same
  form appears pre-filled with every field editable except Name.
- **To delete a profile**: click :heroicons-trash:. The `default` profile
  is protected and cannot be deleted.

#### Hugging Face

- Click **Sign In** to paste a [Hugging Face access token](https://huggingface.co/docs/hub/en/security-tokens). Blackfish
  uses this token to download gated models.
- Once configured, the section shows your HF username, token role, and
  a **Sign Out** button to clear the token.

#### Theme

- Toggle between **Light**, **Dark**, and **System**. **System** follows your OS preference and updates live when you change it.

#### App Configuration

- Read-only display of the running app's version, home directory,
  container provider, and debug flag.
