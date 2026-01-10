Review the current branch changes and suggest PR content.

1. Get the current branch and base branch:
```bash
git branch --show-current
git log --oneline main..HEAD
git diff main...HEAD --stat
```

2. Analyze the changes:
- Summarize what changed (new features, bug fixes, refactoring, etc.)
- Identify which parts of the monorepo are affected (lib/, web/, or both)
- List the key files modified

3. Generate a PR description with:
- **Title**: Concise summary of the changes
- **Summary**: 2-3 bullet points explaining the changes
- **Test plan**: How to verify the changes work correctly

Present the suggested PR content for the user to review and modify.
