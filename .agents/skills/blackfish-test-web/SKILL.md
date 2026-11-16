---
name: blackfish-test-web
description: Run and diagnose Blackfish React frontend tests when frontend test execution is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Run the React frontend tests. If the user provides test selectors or Vitest options, append `--` followed by those separate, correctly shell-quoted arguments. With no arguments, run the full suite.

```bash
cd web && npm test
```

If tests fail, analyze the failures and suggest fixes. If all tests pass, report the summary.
