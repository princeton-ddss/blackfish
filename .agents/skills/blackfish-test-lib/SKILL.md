---
name: blackfish-test-lib
description: Run and diagnose Blackfish Python backend tests when backend test execution is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Run the Python backend tests. Append any requested test selectors or pytest options as separate, correctly shell-quoted arguments. With no arguments, run the full suite.

```bash
cd lib && uv run pytest --verbose
```

If tests fail, analyze the failures and suggest fixes. If all tests pass, report the summary.
