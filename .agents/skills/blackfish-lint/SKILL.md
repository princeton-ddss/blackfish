---
name: blackfish-lint
description: Run Blackfish backend and frontend lint checks when checking monorepo code quality.
---

Paths and commands below are relative to the repository root unless a working directory is specified. Use arguments from the user’s request wherever `<task arguments>` appears.

Run linting for the entire monorepo.

For the Python backend:
```bash
cd lib && uv run pre-commit run --all-files
```

For the frontend:
```bash
cd web && npm run lint
```

Report any issues found and suggest fixes.
