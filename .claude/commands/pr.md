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

If there's a linked issue, include "Closes #N" in the PR body.

## Step 5: Update project status (if linked issue exists)

If the branch name starts with an issue number (e.g., `123-feature-name`) or the PR body contains "Closes #N":

1. Check if `.claude/projects.json` exists. If not, skip this step.
2. Read the projects array. If multiple projects, ask user which one (or try to find the issue in each).
3. Find the issue's item ID in the project:
   ```bash
   gh project item-list <project_number> --owner <owner> --format json | jq -r '.items[] | select(.content.number == <issue-number>) | .id'
   ```
4. Move the issue to "In review" status using IDs from the config:
   ```bash
   gh project item-edit --id "<item-id>" --project-id "<project_id>" --field-id "<fields.status.id>" --single-select-option-id "<fields.status.options['In review']>"
   ```

If the issue is not in any project, no linked issue exists, or no projects config exists, skip this step.

Report the PR URL when complete.
