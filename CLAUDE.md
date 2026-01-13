# Blackfish Monorepo

Open-source AI-as-a-Service (MLaaS) platform for running ML models on HPC clusters.

## Repository Structure

```
blackfish/
├── lib/          # Python backend (blackfish-ai package)
├── web/          # Next.js frontend (blackfish-ui)
└── .github/      # CI/CD workflows (path-dependent)
```

## Quick Reference

### Python Backend (lib/)
```bash
cd lib
uv sync                           # Install dependencies
uv run pytest                     # Run tests
uv run pre-commit run --all-files # Lint & format
uv run blackfish --help           # CLI commands
```

### Next.js Frontend (web/)
```bash
cd web
npm install        # Install dependencies
npm run dev        # Dev server (localhost:3000)
npm test           # Run Jest tests
npm run build:lib  # Build and copy to Python package
```

## Architecture Overview

- **Backend**: Litestar async web framework, SQLAlchemy ORM, Alembic migrations
- **Frontend**: Next.js 14 App Router, React 18, Tailwind CSS, SWR
- **Services**: Text Generation, Speech Recognition (extensible base classes)
- **CLI**: Rich-click powered, profile/service/job management

## Key Conventions

- Python 3.12+, strict MyPy type checking enabled
- All Python code formatted with Ruff
- Frontend uses ESLint, components in `app/components/`
- Service-specific pages in `app/{service-name}/`
- Database migrations in `lib/src/blackfish/server/db/migrations/`

## Testing

- Python: `uv run pytest` (pytest + coverage)
- Frontend: `npm test` (Jest + React Testing Library)
- CI runs path-dependent workflows (lib.yml, web.yml)

## Pull Requests

Always use `/pr` to create pull requests. This command:
- Validates branch state
- Runs lint and tests for affected packages
- Updates coverage badge (Python changes)
- Creates PR with proper format

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full PR checklist.

## See Also

- [lib/CLAUDE.md](lib/CLAUDE.md) - Python backend details
- [web/CLAUDE.md](web/CLAUDE.md) - Frontend details
