---
name: blackfish-migrate
description: Create or apply a Blackfish database migration when the user requests that migration operation.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Use the migration description from the request; ask for it if none is available. Pass it as one argument to `-m`, using proper shell quoting (for example, `shlex.quote`) rather than interpolating raw text inside double quotes. Never execute unresolved placeholders.

For example, creating a migration described as "add model metadata" uses:

```bash
cd lib && uv run alembic revision --autogenerate -m 'add model metadata'
```

Review the generated migration before applying it and report any issues. If the user requested only generation or review, stop there. Apply it only when applying the migration is within the user’s request:

```bash
cd lib && uv run alembic upgrade head
```
