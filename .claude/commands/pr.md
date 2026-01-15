Create a pull request for the current branch.

$ARGUMENTS

## Step 1: Validate branch state

```bash
git branch --show-current
git status
```

Ensure we're not on main/dev and there are commits to push.

## Step 2: Run pre-PR checks

For Python backend (if lib/ files changed):

```bash
cd lib && uv run just lint
cd lib && uv run just test
cd lib && uv run just coverage
```

For frontend (if web/ files changed):

```bash
cd web && npm run lint
cd web && npm test
```

If any checks fail, report the issues and stop. Do not create the PR.

## Step 3: Analyze changes for PR content

```bash
git log --oneline main..HEAD
git diff main...HEAD --stat
```

## Step 4: Create the PR

Push the branch and create the PR using gh:

```bash
git push -u origin $(git branch --show-current)
gh pr create --title "..." --body "..."
```

Use this PR body format:

- ## Summary (2-3 bullet points)
- ## Test plan (verification steps)
- Footer with Claude Code attribution

Report the PR URL when complete.
