---
name: blackfish-pr-checklist
description: Review the Blackfish pre-PR checklist when asked for readiness checks without creating a pull request.
---

Paths and commands below are relative to the repository root unless a working directory is specified.

Output the PR checklist for the contributor to review before creating a pull request.

## PR Checklist

Before creating a pull request, ensure you have completed the following:

### Code Quality
- [ ] Code follows project conventions and patterns
- [ ] No debug statements or commented-out code

### Testing
- [ ] Tests pass locally
  - Python: `cd lib && uv run just test`
  - Frontend: `cd web && npm test`
- [ ] New functionality has test coverage
- [ ] Linting passes
  - Python: `cd lib && uv run just lint`
  - Frontend: `cd web && npm run lint`

### Documentation
- [ ] Code is self-documenting or has necessary comments
- [ ] README updated if adding new features or changing setup

### Coverage Badge (Python changes only)
- [ ] Coverage badge updated: `cd lib && uv run just coverage`
- [ ] Badge changes committed

### Final Steps
- [ ] Commits are clean and have clear messages
- [ ] Branch is up to date with main
- [ ] PR title and description are clear

When the user asks to open the PR, follow the [blackfish-pr skill](../blackfish-pr/SKILL.md) (Claude: `/pr`). Reviewing this checklist alone does not request PR creation.
