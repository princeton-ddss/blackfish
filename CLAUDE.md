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

## Commits

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification.

Scopes: `lib`, `web`, `ci`, `docs` (optional — omit for cross-cutting changes)

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

## GitHub Project Integration

Work is tracked in GitHub Projects (Kanban boards). Run `/project-setup` to add projects to `.claude/projects.json` (not tracked in git).

### When creating issues

1. Create the issue: `gh issue create --title "..." --body "..."`
2. Ask user: "Ready to implement or Backlog?"
3. Read `.claude/projects.json` and ask user which project to use (if multiple)
4. Add to project and set status:
   ```bash
   # Add issue to project (use owner and project_number from config)
   gh project item-add <project_number> --owner <owner> --url <issue-url>

   # Get item ID
   ITEM_ID=$(gh project item-list <project_number> --owner <owner> --format json | jq -r '.items[] | select(.content.url == "<issue-url>") | .id')

   # Set status (use IDs from .claude/project.json)
   gh project item-edit --id "$ITEM_ID" --project-id "<project_id>" --field-id "<status.id>" --single-select-option-id "<status.options[status]>"
   ```

### When starting work on an issue

1. Ensure a tracking issue exists (create one if needed)
2. Move issue to "In progress" status using the option ID from config

### When opening a PR

1. Link the issue in PR body with "Closes #N"
2. Move issue to "In review" status
3. The `/pr` command handles this automatically

## See Also

- [lib/CLAUDE.md](lib/CLAUDE.md) - Python backend details
- [web/CLAUDE.md](web/CLAUDE.md) - Frontend details
