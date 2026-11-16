---
name: blackfish-test-web
description: Run and diagnose Blackfish React frontend tests when frontend test execution is requested.
---

Paths and commands below are relative to the repository root unless a working directory is specified. Use arguments from the user’s request wherever `<task arguments>` appears.

Run the React frontend tests.

```bash
cd web && npm test -- <task arguments>
```

If tests fail, analyze the failures and suggest fixes. If all tests pass, report the summary.
