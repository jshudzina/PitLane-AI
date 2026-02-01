#!/usr/bin/env python3
"""
Atomically bump version across all PitLane-AI packages.

This script updates the version number in all 5 locations:
1. /pyproject.toml (root package)
2. /packages/pitlane-agent/pyproject.toml
3. /packages/pitlane-web/pyproject.toml
4. /packages/pitlane-agent/src/pitlane_agent/__init__.py
5. /packages/pitlane-web/src/pitlane_web/__init__.py

Supports PEP 440 versioning including pre-release and local versions.

Usage:
    python scripts/bump_version.py 0.2.0         # Release version
    python scripts/bump_version.py v0.2.0        # 'v' prefix is automatically stripped
    python scripts/bump_version.py 0.2.0a0       # Alpha version
    python scripts/bump_version.py 0.2.0b1       # Beta version
    python scripts/bump_version.py 0.2.0rc1      # Release candidate
    python scripts/bump_version.py 0.2.0.dev0    # Development version
    python scripts/bump_version.py 0.2.0+test    # Local version
"""

import re
import sys
from pathlib import Path


def validate_version(version: str) -> str:
    """
    Validate and normalize PEP 440 version format.

    Supports Python's PEP 440 versioning including pre-release and local versions:
    - 0.2.0
    - 0.2.0a0 or 0.2.0alpha0 (alpha)
    - 0.2.0b1 or 0.2.0beta1 (beta)
    - 0.2.0rc1 (release candidate)
    - 0.2.0.post1 (post-release)
    - 0.2.0.dev0 (development)
    - 0.2.0+test (local version)

    Args:
        version: Version string (e.g., "0.2.0", "v0.2.0a0", "0.2.0rc1")

    Returns:
        Normalized version string without 'v' prefix

    Raises:
        ValueError: If version format is invalid per PEP 440
    """
    # Strip 'v' prefix if present
    normalized = version.lstrip("v")

    # Validate PEP 440 version format
    # Based on https://peps.python.org/pep-0440/
    # [N!]N(.N)*[{a|alpha|b|beta|rc}N][.postN][.devN][+local]
    pattern = r"^(\d+!)?\d+(\.\d+)*((a|alpha|b|beta|rc)\d+)?(\.post\d+)?(\.dev\d+)?(\+[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
    if not re.match(pattern, normalized):
        raise ValueError(
            f"Invalid version format: {version}. "
            f"Expected PEP 440 format: X.Y.Z[{{a|b|rc}}N][.postN][.devN][+local] "
            f"(e.g., 0.2.0, 0.2.0a0, 0.2.0b1, 0.2.0rc1, 0.2.0.dev0, 0.2.0+test)"
        )

    return normalized


def update_pyproject_toml(file_path: Path, version: str) -> None:
    """
    Update version in pyproject.toml file.

    Args:
        file_path: Path to pyproject.toml file
        version: New version string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If version line not found
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text()

    # Match 'version = "X.Y.Z"' pattern
    pattern = r'^version = "[^"]*"'
    replacement = f'version = "{version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)

    if count == 0:
        raise ValueError(f"Version line not found in {file_path}")

    file_path.write_text(new_content)
    print(f"✓ Updated {file_path.relative_to(Path.cwd())} to version {version}")


def update_init_py(file_path: Path, version: str) -> None:
    """
    Update __version__ in __init__.py file.

    Args:
        file_path: Path to __init__.py file
        version: New version string

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If __version__ line not found
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = file_path.read_text()

    # Match '__version__ = "X.Y.Z"' pattern
    pattern = r'^__version__ = "[^"]*"'
    replacement = f'__version__ = "{version}"'

    new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)

    if count == 0:
        raise ValueError(f"__version__ line not found in {file_path}")

    file_path.write_text(new_content)
    print(f"✓ Updated {file_path.relative_to(Path.cwd())} to version {version}")


def bump_version(version: str) -> None:
    """
    Update version in all PitLane-AI package files.

    Args:
        version: New version string

    Raises:
        Exception: If any file update fails (all updates are rolled back)
    """
    # Get repository root
    repo_root = Path(__file__).parent.parent

    # Define files to update with their update functions
    files_to_update: list[tuple[Path, callable]] = [
        (repo_root / "pyproject.toml", update_pyproject_toml),
        (repo_root / "packages/pitlane-agent/pyproject.toml", update_pyproject_toml),
        (repo_root / "packages/pitlane-web/pyproject.toml", update_pyproject_toml),
        (repo_root / "packages/pitlane-agent/src/pitlane_agent/__init__.py", update_init_py),
        (repo_root / "packages/pitlane-web/src/pitlane_web/__init__.py", update_init_py),
    ]

    # Validate all files exist before making any changes
    print("Validating files...")
    for file_path, _ in files_to_update:
        if not file_path.exists():
            raise FileNotFoundError(f"Required file not found: {file_path}")

    # Update all files
    print(f"\nBumping version to {version}...\n")
    updated_files = []

    try:
        for file_path, update_func in files_to_update:
            update_func(file_path, version)
            updated_files.append(file_path)

        print(f"\n✓ Successfully bumped version to {version} in all {len(updated_files)} files")

    except Exception as e:
        print(f"\n✗ Error updating files: {e}", file=sys.stderr)
        print(f"Updated {len(updated_files)} of {len(files_to_update)} files", file=sys.stderr)
        raise


def main() -> int:
    """
    Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) != 2:
        print("Usage: python scripts/bump_version.py <version>", file=sys.stderr)
        print("Example: python scripts/bump_version.py 0.2.0", file=sys.stderr)
        return 1

    try:
        version_arg = sys.argv[1]
        version = validate_version(version_arg)
        bump_version(version)
        return 0

    except ValueError as e:
        print(f"✗ Validation error: {e}", file=sys.stderr)
        return 1

    except FileNotFoundError as e:
        print(f"✗ File error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
