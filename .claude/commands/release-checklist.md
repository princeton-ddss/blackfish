Output the release checklist for preparing a new version release.

## Release Checklist

Before releasing a new version, ensure you have completed the following:

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
  - Python: `cd lib && uv run just test`
  - Frontend: `cd web && npm test`
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
- [ ] Verify PyPI package published (if automated)

### Post-Release
- [ ] Announce release if significant changes
