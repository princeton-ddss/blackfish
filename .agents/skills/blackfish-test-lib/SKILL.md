---
name: blackfish-test-lib
description: Run and diagnose Blackfish Python backend tests when backend test execution is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified. Use arguments from the user’s request wherever `<task arguments>` appears.

Run the Python backend tests.

```bash
cd lib && uv run pytest --verbose <task arguments>
```

If tests fail, analyze the failures and suggest fixes. If all tests pass, report the summary.
