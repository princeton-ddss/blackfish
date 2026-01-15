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
