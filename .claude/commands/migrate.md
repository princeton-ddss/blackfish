Create and run a database migration.

Migration description: $ARGUMENTS

```bash
cd lib && uv run alembic revision --autogenerate -m "$ARGUMENTS"
```

Then apply the migration:
```bash
cd lib && uv run alembic upgrade head
```

Review the generated migration file and report any issues.
