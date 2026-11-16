---
name: blackfish-build
description: Build the Blackfish frontend and verify its Python package integration when a full application build is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified. Use arguments from the user’s request wherever `<task arguments>` appears.

Build the full application (frontend + backend integration).

1. Build the frontend:
```bash
cd web && npm run build:lib
```

2. Verify the Python package:
```bash
cd lib && uv run blackfish --help
```

Report any build errors and suggest fixes.
