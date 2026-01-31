"""FastF1 cache utilities."""

from pathlib import Path


def get_fastf1_cache_dir() -> Path:
    """Get the shared FastF1 cache directory path.

    Returns:
        Path to the FastF1 cache directory in the user's home directory.

    Examples:
        >>> cache_dir = get_fastf1_cache_dir()
        >>> print(cache_dir)
        /home/user/.pitlane/cache/fastf1
    """
    return Path.home() / ".pitlane" / "cache" / "fastf1"
