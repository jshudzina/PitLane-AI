#!/bin/bash
# Pytest runner for uv monorepos
# Usage: ./run_pytest.sh <package-name> [pytest arguments]
# Example: ./run_pytest.sh pitlane-core -v
# Example: ./run_pytest.sh pitlane-core tests/test_specific.py -k test_function

set -e

if [ $# -eq 0 ]; then
    echo "Error: Package name required"
    echo "Usage: $0 <package-name> [pytest arguments]"
    echo "Example: $0 pitlane-core -v"
    exit 1
fi

PACKAGE_NAME=$1
shift  # Remove package name from arguments, leaving only pytest args

echo "🔄 Syncing uv environment..."
uv sync --all-packages --all-groups --reinstall

echo "🧪 Running pytest for package: $PACKAGE_NAME"
uv run --directory "packages/$PACKAGE_NAME" pytest "$@"
