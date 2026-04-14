# Web Interface

Blackfish ships with a browser-based UI served alongside the API. Once
`blackfish start` is running, open `http://localhost:8000` (or your
configured host/port) to access it.

The UI and the CLI are alternative front-ends to the same API. Most
users will prefer the UI for interactive work (chat, model browsing,
settings) and the CLI for scripting and automation.

## What's in the UI

- **Services**
    - **Text Generation** — chat or completion against a running vLLM
      service, with text/code file attachments as conversation context.
    - **Speech Recognition** — transcribe audio against a running
      Whisper service.
    - More services on the way.
- **Models** — inventory, download, and delete models per profile.
- **Files** — browse, upload, download, and delete files on a remote
  Slurm profile over SFTP.
- **Batch Jobs** — launch and monitor TigerFlow-backed batch jobs
  (transcribe, translate, detect, OCR) against a directory of inputs.
- **Settings** — profile management, theme preference, and Hugging
  Face token management.

## Task walkthroughs

### Start and use a text-generation service

- From the **Text Generation** page, click the rocket icon in the
  service container header to open the launcher.
- Fill in the Service modal:
    - **Name** — a suggestion is pre-populated; leave it or rename.
    - **Model** and **Revision** — pick from the available list.
    - On a Slurm profile, pick a **Partition** and a **Resource tier**.
      Tier selection abstracts the CPU / memory / GPU / time-limit
      flags, so there's no need to fill them in by hand.
- Click **Launch**. The service status badge moves from `PENDING` →
  `STARTING` → `HEALTHY`.
- Once the service is `HEALTHY`, the chat text area at the bottom of
  the page becomes active:
    - Type a message and press **Enter** to send (**Shift+Enter** for
      a newline).
    - Click the **adjustments icon** in the toolbar to open the
      parameters panel — tune temperature, max tokens, presence and
      frequency penalties, stop sequences, and seed.
    - Click the **code-bracket icon** in the toolbar to open the code
      snippet modal, which shows the equivalent request body in
      Python, R, and Bash.
- When you're done, click the **stop button** in the service container
  header. The service transitions to `STOPPED`; a **trash button**
  appears next to it so you can remove the record entirely.

### Create a batch job

- **Prerequisite:** a Slurm profile with TigerFlow installed. TigerFlow
  is installed automatically the first time you create a Slurm profile,
  so in practice any Slurm profile will work.
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
    4. **Resources** — pick a partition, a resource tier, and the
       maximum number of concurrent workers. Advanced options (account,
       worker and client timeouts) live under an expandable section.
- Click **Submit**. The modal closes and the new job appears at the top
  of the Jobs table.
- The progress column shows finished/total counts as workers complete
  files.
- Click a job row to drill into file-level results; failed files expose
  their error messages inline.

### Manage models

- Open the **Models** page from the sidebar.
- The table lists every model available under the selected profile,
  with columns for name, size, parameter count, task, and location.
- **To download a new model**:
    - Click the **+** button in the header.
    - A dialog asks for a **repo ID** (e.g. `meta-llama/Llama-2-7b`)
      and an optional **revision** (defaults to `main`).
    - Click **Download**. The model appears in the table with a status
      indicator while the download runs.
- **To delete a model**:
    - Hover the row and click the **action menu**.
    - Choose **Delete** and confirm.

> [!NOTE]
> Model downloads and deletions are only supported for **local
> profiles** or **Slurm profiles with `host=localhost`** (e.g. Open
> OnDemand sessions running on the cluster head node). Remote Slurm
> profiles display a banner explaining that model management must
> happen on the cluster directly.

### Change settings

- Click the **gear icon** in the navbar to open the Settings slide-over.
- The panel has four sections: **Profiles**, **Hugging Face**,
  **App Configuration**, and **Theme**.

#### Profiles

- The top section lists every profile you've configured, with a badge
  showing the type (Local / Slurm).
- **To add a new profile**:
    - Click **Add Profile** — a form expands inline.
    - Fill in:
        - **Name** (immutable once created).
        - **Type** — Local or Slurm.
        - **Home directory** — where Blackfish stores profile state on
          the target machine. Must be an absolute path.
        - **Cache directory** — where cached models and SIF images
          live.
        - For Slurm profiles: **Host**, **User**, and an optional
          **Python path** if the cluster doesn't have Python on `$PATH`.
    - Click **Create**.
- **To edit a profile**: click the pencil icon on the row; the same
  form appears pre-filled with every field editable except Name.
- **To delete a profile**: click the trash icon. The `default` profile
  is protected and cannot be deleted.

#### Hugging Face

- Click **Sign In** to paste a Hugging Face access token. Blackfish
  uses this token to download gated models.
- Once configured, the section shows your HF username, token role, and
  a **Sign Out** button to clear the token.

#### Theme

- Toggle between **Light**, **Dark**, and **System**.
- **System** follows your OS preference and updates live when you
  change it.

#### App Configuration

- Read-only display of the running app's version, home directory,
  container provider, and debug flag.

## Video walkthroughs

Video demonstrations of the main flows are coming. In the meantime,
the [CLI guide](cli.md) covers concrete workflows that map one-to-one
onto their UI equivalents.
