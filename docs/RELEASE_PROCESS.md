# Release Process

This document describes how to create releases for PitLane-AI and what happens automatically during the release process.

## Overview

PitLane-AI uses an automated release workflow that:
- Bumps version numbers across all packages
- Generates CHANGELOG from conventional commits
- Builds distribution packages
- Optionally publishes to PyPI
- Attaches build artifacts to GitHub Releases

## Prerequisites

Before creating a release, ensure:
- All changes are merged to the `main` branch
- All tests are passing
- Pre-commit hooks have been run
- You have appropriate repository permissions

## Creating a Release

### Method 1: GitHub UI (Recommended)

1. Go to [Releases](https://github.com/jshudzina/PitLane-AI/releases) page
2. Click "Draft a new release"
3. Click "Choose a tag" and create a new tag:
   - Format: `vX.Y.Z` (e.g., `v0.2.0`, `v1.0.0`)
   - Must start with `v` and follow semantic versioning
   - Target: `main` branch
4. Enter release title (e.g., "Release v0.2.0")
5. Add release notes or let GitHub generate them
6. Click "Publish release"

### Method 2: Manual Workflow Trigger

For testing or special cases:

1. Go to [Actions](https://github.com/jshudzina/PitLane-AI/actions/workflows/release.yml) page
2. Click "Run workflow"
3. Enter:
   - **Version**: The version number (e.g., `0.2.0` or `v0.2.0`)
   - **Publish to PyPI**: Check if you want to publish (requires setup)
4. Click "Run workflow"

## What Happens Automatically

When you create a release, the workflow automatically:

### 1. Version Bump (Job: `version-bump`)
- Parses version from the release tag
- Runs `scripts/bump_version.py` to update versions in:
  - `/pyproject.toml`
  - `/packages/pitlane-agent/pyproject.toml`
  - `/packages/pitlane-web/pyproject.toml`
  - `/packages/pitlane-agent/src/pitlane_agent/__init__.py`
  - `/packages/pitlane-web/src/pitlane_web/__init__.py`
- Generates `CHANGELOG.md` from conventional commits using git-cliff
- Commits changes with message: `chore: bump version to X.Y.Z`
- Pushes commit to `main` branch

### 2. Build (Job: `build`)
- Checks out the version-bumped code
- Installs `uv` package manager
- Runs `uv build --all-packages` to create:
  - Wheel files (`.whl`) for all 3 packages
  - Source distributions (`.tar.gz`) for all 3 packages
- Uploads artifacts for 90 days

### 3. Publish to PyPI (Job: `publish`, conditional)
Only runs if:
- Repository variable `AUTO_PUBLISH_PYPI` is set to `true`, OR
- Manual workflow trigger with "Publish to PyPI" checked

Steps:
- Downloads build artifacts
- Publishes all packages to PyPI using stored token
- Packages become available at:
  - https://pypi.org/project/pitlane-ai/
  - https://pypi.org/project/pitlane-agent/
  - https://pypi.org/project/pitlane-web/

### 4. Upload Artifacts (Job: `upload-to-release`)
- Downloads build artifacts
- Attaches all `.whl` and `.tar.gz` files to the GitHub Release

## Version Numbering

PitLane-AI follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (X.0.0): Breaking changes
- **MINOR** (0.X.0): New features (backward compatible)
- **PATCH** (0.0.X): Bug fixes (backward compatible)

Examples:
- `v0.1.0` → `v0.2.0`: Added new features
- `v0.2.0` → `v0.2.1`: Fixed bugs
- `v0.9.0` → `v1.0.0`: First stable release with breaking changes

### Pre-release Versions

For testing releases:
- `v0.2.0-beta.1`: Beta release
- `v0.2.0-rc.1`: Release candidate

## Unified Versioning

All three packages (pitlane-ai, pitlane-agent, pitlane-web) share the same version number. This ensures:
- Compatibility between packages
- Simpler dependency management
- Clear version alignment for users

## CHANGELOG Generation

The CHANGELOG is automatically generated from conventional commit messages:

### Commit Types
- `feat:` → Features section
- `fix:` → Bug Fixes section
- `refactor:` → Refactoring section
- `perf:` → Performance section
- `test:` → Testing section
- `docs:` → Documentation section
- `chore:` → Skipped (except version bumps)

### Commit Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Examples:
```bash
feat(agent): add lap time distribution visualization
fix(web): resolve security vulnerabilities in dependencies
refactor(cli): reorganize command structure
```

Pull request references like `(#14)` are automatically converted to links.

## PyPI Publishing

### Setup (One-time)

To enable PyPI publishing:

1. **Create PyPI Account & Token**
   - Sign up at https://pypi.org
   - Generate API token at https://pypi.org/manage/account/token/
   - Scope: Entire account or specific to pitlane-ai projects

2. **Configure GitHub Environment**
   - Go to repository Settings → Environments
   - Create environment named: `pypi`
   - Add secret: `PYPI_TOKEN` (paste your PyPI API token)
   - Optional: Add protection rules (require approval, restrict to main branch)

3. **Enable Auto-Publishing (Optional)**
   - Go to repository Settings → Variables → New repository variable
   - Name: `AUTO_PUBLISH_PYPI`
   - Value: `true`
   - This enables automatic publishing on every release

### Manual Publishing

If auto-publishing is disabled:
- Use workflow_dispatch trigger
- Check "Publish to PyPI" option

## Monitoring Release Progress

1. Go to [Actions](https://github.com/jshudzina/PitLane-AI/actions) tab
2. Click on the "Release" workflow run
3. Monitor each job:
   - ✓ version-bump
   - ✓ build
   - ✓ publish (if enabled)
   - ✓ upload-to-release

Each job shows detailed logs of what happened.

## Verifying a Release

After a release completes:

### 1. Check Version Bump Commit
```bash
git pull origin main
git log -1  # Should show "chore: bump version to X.Y.Z"
```

### 2. Verify Versions
```bash
# Check all version files
grep -r "X.Y.Z" pyproject.toml packages/*/pyproject.toml packages/*/src/*/__init__.py
```

### 3. Check CHANGELOG
```bash
cat CHANGELOG.md
# Should show new version with categorized commits
```

### 4. Download and Test Artifacts
From the GitHub Release page:
- Download `.whl` files
- Install locally:
  ```bash
  pip install pitlane_ai-X.Y.Z-py3-none-any.whl
  pip install pitlane_agent-X.Y.Z-py3-none-any.whl
  pip install pitlane_web-X.Y.Z-py3-none-any.whl
  ```
- Verify versions:
  ```bash
  python -c "import pitlane_agent; print(pitlane_agent.__version__)"
  python -c "import pitlane_web; print(pitlane_web.__version__)"
  ```

### 5. Verify PyPI (if published)
- Check packages appear at:
  - https://pypi.org/project/pitlane-ai/X.Y.Z/
  - https://pypi.org/project/pitlane-agent/X.Y.Z/
  - https://pypi.org/project/pitlane-web/X.Y.Z/
- Test installation:
  ```bash
  pip install pitlane-ai==X.Y.Z
  ```

## Troubleshooting

### Release Workflow Failed

**Symptom**: Workflow shows red X in Actions tab

**Solutions**:
1. Check the failed job logs for specific errors
2. Common issues:
   - Version format invalid (must be X.Y.Z)
   - Merge conflicts on main branch
   - PyPI token expired or incorrect
   - Network issues during publishing

### Version Bump Commit Not Created

**Symptom**: No "chore: bump version to X.Y.Z" commit on main

**Solutions**:
1. Check version-bump job logs
2. Ensure GitHub token has write permissions
3. Check for branch protection rules blocking pushes

### Build Artifacts Missing

**Symptom**: No `.whl` or `.tar.gz` files attached to release

**Solutions**:
1. Check build job logs for errors
2. Verify uv installation succeeded
3. Check if packages have proper pyproject.toml configuration

### PyPI Publishing Failed

**Symptom**: publish job failed or packages not on PyPI

**Solutions**:
1. Verify `PYPI_TOKEN` secret is correctly set in pypi environment
2. Check token hasn't expired
3. Verify package names aren't already taken (for first release)
4. Check PyPI status page for outages

## Rolling Back a Release

If a release has issues:

### 1. Revert Version Bump Commit
```bash
# Find the version bump commit
git log --oneline | grep "chore: bump version"

# Revert it
git revert <commit-sha>
git push origin main
```

### 2. Delete GitHub Release
1. Go to [Releases](https://github.com/jshudzina/PitLane-AI/releases)
2. Click on the problematic release
3. Click "Delete" (⋮ menu)

### 3. Delete Git Tag
```bash
# Delete local tag
git tag -d vX.Y.Z

# Delete remote tag
git push --delete origin vX.Y.Z
```

### 4. Handle PyPI (if published)

**Important**: PyPI doesn't allow deleting or re-uploading versions!

Options:
- **Yank the release**: Marks version as broken but keeps it
  ```bash
  pip install twine
  twine upload --repository pypi dist/* --yank "Reason for yanking"
  ```
- **Publish a new patch version**: Create vX.Y.Z+1 with fixes

## Testing Releases

Before creating an official release, test with a pre-release version:

1. Create release with tag like `v0.2.0-test` or `v0.2.0-rc.1`
2. Monitor workflow execution
3. Download and test artifacts
4. Delete test release and tag when satisfied
5. Create official release

## Best Practices

1. **Write good commit messages**: Use conventional commits format consistently
2. **Review CHANGELOG**: After release, verify CHANGELOG accurately reflects changes
3. **Test before releasing**: Run full test suite before creating release
4. **Version appropriately**: Follow semantic versioning guidelines
5. **Pre-release testing**: Use pre-release tags for testing (e.g., `v0.2.0-beta.1`)
6. **Monitor workflow**: Watch the release workflow to catch issues early
7. **Verify artifacts**: Always download and test artifacts before announcing release

## Support

For issues with the release process:
- Check [Actions](https://github.com/jshudzina/PitLane-AI/actions) for workflow logs
- Review this document for common issues
- Open an issue at https://github.com/jshudzina/PitLane-AI/issues
