lint:
  uv run pre-commit autoupdate
  uv run pre-commit run --all-files

test:
  uv run pytest --cache-clear --verbose --cov=app

coverage:
  uv run coverage-badge -o docs/assets/img/coverage.svg -f

docs:
  uv run mkdocs build
