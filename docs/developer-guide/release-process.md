# Release Process

Detailed release process documentation can be found at [docs/RELEASE_PROCESS.md](../../RELEASE_PROCESS.md).

## Quick Reference

### Creating a Release

1. Go to [Releases page](https://github.com/jshudzina/PitLane-AI/releases)
2. Click "Draft a new release"
3. Create tag: `vX.Y.Z` (e.g., `v0.2.0`)
4. Publish release

### Automated Steps

The workflow automatically:
- Bumps version numbers in all packages
- Generates CHANGELOG from conventional commits
- Builds wheel and source distributions
- Publishes to PyPI (if configured)
- Attaches artifacts to GitHub Release

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

See [full documentation](../../RELEASE_PROCESS.md) for details.
