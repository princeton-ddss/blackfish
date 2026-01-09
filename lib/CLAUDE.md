# Blackfish Python Backend

Python package `blackfish-ai` - ML-as-a-Service platform core.

## Development Setup

```bash
uv sync                    # Install all dependencies
uv run blackfish --help    # Verify CLI works
```

## Common Commands

```bash
# Testing
uv run pytest                              # Run all tests
uv run pytest tests/api/ -v                # API tests only
uv run pytest -k "test_name" -v            # Run specific test
uv run pytest --cov=blackfish              # With coverage

# Linting & Type Checking
uv run pre-commit run --all-files          # Full lint
uv run ruff check src/                     # Ruff only
uv run mypy src/                           # Type check (strict)

# Just commands
just test                                  # pytest with coverage
just lint                                  # pre-commit hooks
just docs                                  # Build MkDocs
```

## Project Structure

```
lib/
├── src/blackfish/
│   ├── cli/              # CLI commands (rich-click)
│   │   ├── __main__.py   # Entry point
│   │   ├── jobs/         # Job management commands
│   │   └── services/     # Service commands
│   ├── server/
│   │   ├── asgi.py       # Litestar app definition
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── jobs/         # Batch job implementations
│   │   ├── services/     # Service implementations
│   │   └── db/migrations/# Alembic migrations
│   ├── client.py         # Python API client
│   └── build/            # Built frontend (generated)
├── tests/
│   ├── conftest.py       # Pytest fixtures
│   ├── api/              # API endpoint tests
│   ├── cli/              # CLI tests
│   └── unit/             # Unit tests
└── docs/                 # MkDocs documentation
```

## Code Patterns

### Adding a New Service
1. Create service class in `src/blackfish/server/services/` extending `BaseService`
2. Add API routes to `src/blackfish/server/asgi.py`
3. Add CLI commands in `src/blackfish/cli/services/`
4. Add tests in `tests/api/` and `tests/unit/`

### Adding a New Batch Job
1. Create job class in `src/blackfish/server/jobs/` extending `BaseBatchJob`
2. Register in job manager
3. Add corresponding tests

### Database Migrations
```bash
cd lib
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Key Files

- `src/blackfish/server/asgi.py` - Main Litestar app, routes, middleware
- `src/blackfish/server/config.py` - App configuration
- `src/blackfish/cli/__main__.py` - CLI entry point
- `tests/conftest.py` - Shared test fixtures

## Type Checking

MyPy strict mode is enabled. All code must have type annotations:
- Function signatures (params and return types)
- Class attributes
- No implicit `Any` types
