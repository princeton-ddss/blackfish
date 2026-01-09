# Contributing to Blackfish

Thanks for your interest in contributing to Blackfish!

## Development Setup

See the package READMEs for setup instructions:
- [Python backend](lib/README.md)
- [Next.js frontend](web/README.md)

## PR Checklist

Before creating a pull request:

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

## Release Checklist

For maintainers preparing a release:

### Pre-Release
- [ ] All PRs for this release are merged to main
- [ ] CI is green on main branch
- [ ] Coverage badge is up to date

### Version Bump
- [ ] Update version in `lib/pyproject.toml`
- [ ] Update version in `web/package.json` (keep in sync)
- [ ] Update CHANGELOG if maintained

### Testing
- [ ] Full test suite passes
- [ ] Manual smoke test of key features

### Documentation
- [ ] README reflects current functionality
- [ ] Images table updated if new service images added
- [ ] Models table updated if new models tested

### Release
- [ ] Create release commit: `git commit -m "Release vX.Y.Z"`
- [ ] Tag the release: `git tag vX.Y.Z`
- [ ] Push with tags: `git push && git push --tags`
- [ ] Create GitHub release with release notes
- [ ] Verify PyPI package published

### Post-Release
- [ ] Announce release if significant changes
