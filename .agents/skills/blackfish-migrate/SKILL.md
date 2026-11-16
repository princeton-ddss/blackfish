---
name: blackfish-migrate
description: Create, inspect, and apply a Blackfish database migration when a schema migration is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified. Use arguments from the user’s request wherever `<task arguments>` appears.

Create and run a database migration.

Migration description: <task arguments>

```bash
cd lib && uv run alembic revision --autogenerate -m "<task arguments>"
```

Then apply the migration:
```bash
cd lib && uv run alembic upgrade head
```

Review the generated migration file and report any issues.
