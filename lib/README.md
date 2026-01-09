# Blackfish AI

Python package `blackfish-ai` - the core backend for the [Blackfish](../) MLaaS platform.

For project overview, installation, and usage instructions, see the [main README](../README.md).

## Development Setup

```bash
cd lib
uv sync                    # Install dependencies
uv run blackfish --help    # Verify CLI works
```

## Common Commands

```bash
# Development (using justfile)
uv run just test           # Run tests with coverage
uv run just lint           # Lint and format
uv run just coverage       # Generate coverage badge
uv run just docs           # Build documentation

# Database Migrations
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
```

## Project Structure

```
lib/
├── src/blackfish/
│   ├── cli/              # CLI commands (rich-click)
│   ├── server/           # Litestar app, routes, models
│   └── build/            # Built frontend (generated)
├── tests/                # pytest tests
└── docs/                 # MkDocs documentation
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BLACKFISH_HOST` | Server host | `localhost` |
| `BLACKFISH_PORT` | Server port | `8000` |
| `BLACKFISH_DEBUG` | Enable debug mode (0/1) | `1` |
| `BLACKFISH_HOME_DIR` | Blackfish home directory | `~/.blackfish` |
| `BLACKFISH_BASE_PATH` | API base path | `/` |
| `BLACKFISH_STATIC_DIR` | Static files directory | (bundled) |
| `BLACKFISH_CONTAINER_PROVIDER` | Container provider | (auto-detect) |
| `BLACKFISH_MAX_FILE_SIZE` | Max upload file size | `1000000000` |

## Documentation

- [Full Documentation](https://princeton-ddss.github.io/blackfish/)
- [Main README](../README.md)
