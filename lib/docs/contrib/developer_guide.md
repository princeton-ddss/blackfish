# Developer Guide

## Setup

### Clone and install

`uv` is optional but highly recommended. To install Blackfish for development:

```shell
git clone https://github.com/princeton-ddss/blackfish.git
cd blackfish/lib
uv sync
```

### pre-commit

Install the `pre-commit` hooks from the `lib/` directory:

```shell
uv run pre-commit install
```

### just

Development tasks run through a `justfile` in `lib/`. From that directory:

- `just lint` — run pre-commit hooks
- `just test` — run pytest with coverage
- `just coverage` — refresh the coverage badge
- `just docs` — build the MkDocs site

### SSH

Running Blackfish from your laptop to start remote services requires password-less SSH access to remote clusters. A simple way to set up password-less login is with the `ssh-keygen` and `ssh-copy-id` utilities.

First, make sure that you are connected to your institution's network or VPN, if required. Then, type the following at the command-line:

```shell
ssh-keygen -t rsa # generates ~/.ssh/id_rsa.pub and ~/.ssh/id_rsa
ssh-copy-id <user>@<host> # answer yes to transfer the public key
```

These commands create a secure public-private key pair and send the public key to the HPC server. You now have password-less access to your HPC server!

### Apptainer

Services deployed on HPC systems need to be run by Apptainer instead of Docker. Apptainer will not run Docker images directly. Instead, you need to convert Docker images to SIF files. For images hosted on Docker Hub, running `apptainer pull` will do this automatically. For example,

```shell
apptainer pull docker://vllm/vllm-openai:v0.10.2
```

This command generates a file `vllm-openai_v0.10.2.sif`. In order for users to access the image, it should be moved to a shared cache directory, e.g., `/shared/.blackfish/images`.

## API Development

Blackfish is a Litestar application. You can start the development server with:

```shell
blackfish start
```

### Configuration

The application and CLI pull settings from environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `BLACKFISH_HOST` | `localhost` | Host for the Blackfish app |
| `BLACKFISH_PORT` | `8000` | Port for the Blackfish app |
| `BLACKFISH_HOME_DIR` | `~/.blackfish` | Application data directory |
| `BLACKFISH_DEBUG` | `true` | Run in debug mode (no auth) |
| `BLACKFISH_CONTAINER_PROVIDER` | `docker` | Container runtime (`docker` or `apptainer`) |
| `BLACKFISH_AUTH_TOKEN` | — | Authentication token (ignored in debug mode) |

### Database Migrations

Blackfish uses Alembic for database migrations. From `lib/`:

```shell
# Check current revision
uv run alembic current

# Create a new migration after updating models
uv run alembic revision --autogenerate -m "description"

# Apply migrations
uv run alembic upgrade head
```

## UI Development

The frontend is a Vite + React application in `web/`.

### Setup

```shell
cd web
npm install
npm run dev    # Dev server at localhost:3000
```

The dev server proxies API requests to the Blackfish backend, so you'll need `blackfish start` running in another terminal.

### Testing and Linting

```shell
npm test              # Run Vitest tests
npm run test:watch    # Watch mode
npm run test:coverage # With coverage
npm run lint          # ESLint check
npm run lint:fix      # Auto-fix
```

### Building for Production

The backend ships with a pre-built copy of the UI so users don't need `npm` installed to run Blackfish. To update it:

```shell
npm run build:lib
```

This builds the UI with Vite and copies the output to `lib/src/blackfish/build/`. Commit the resulting build tree alongside your source changes.
