---
name: blackfish-pr
description: Validate and open a Blackfish PR, update project status, and triage bot feedback when the user asks to open a PR.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Create a pull request for the current branch when requested by the user. A request to review changes or draft PR text alone does not request a push or PR creation.

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

Do not add agent attribution footers.

If there's a linked issue, include "Closes #N" in the PR body.

## Step 5: Update project status (if linked issue exists)

If the branch name starts with an issue number (e.g., `123-feature-name`) or the PR body contains "Closes #N":

1. Check if `.claude/projects.json` exists. If not, skip this step.
2. Read the projects array. If multiple projects, ask user which one (or try to find the issue in each).
3. Find the issue's item ID in the project:
   ```bash
   gh project item-list <project_number> --owner <owner> --format json | jq -r '.items[] | select(.content.number == <issue-number>) | .id'
   ```
4. Resolve the review status from the configured option names, matching case-insensitively (`In review`, `Review`, or `Pending review`). Use its stored option ID; do not index the config with an assumed spelling. Move the issue using that ID:
   ```bash
   gh project item-edit --id "<item-id>" --project-id "<project_id>" --field-id "<fields.status.id>" --single-select-option-id "<review-status-option-id>"
   ```

If the issue is not in any project, no linked issue exists, or no projects config exists, skip this step.

## Step 6: Wait for and triage the automated review

The repository’s automated reviewer posts a PR comment from the `claude` GitHub account. This reviewer is independent of which agent opens the PR. It takes a few minutes, so poll
for that comment rather than checking once (poll every ~60s, up to ~10
minutes). If no bot review appears, say so and stop.

The bot produces many false positives — do NOT blindly apply its suggestions.
Triage each item:
- **Address now**: genuine bug, security, or correctness problem in this PR's
  changes. Fix it in this branch, then commit and push.
- **Ignore**: false positive, nitpick, out-of-scope, or conflicts with project
  conventions. Note briefly why.
- **Follow-up issue**: real but larger concern not appropriate for this PR.
  Create a tracking issue and add it to the Blackfish project in "Backlog".

Report a short triage summary: what was addressed, what was ignored (with
reasons), and links to any follow-up issues.

Report the PR URL when complete.
