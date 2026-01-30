"""Filename utilities for chart generation."""

import re


def sanitize_filename(text: str) -> str:
    """Sanitize text for use in filenames.

    Converts text to lowercase and replaces spaces and special characters
    with underscores to create filesystem-safe filenames.

    Args:
        text: Input text (e.g., GP name like "Abu Dhabi" or "São Paulo")

    Returns:
        Sanitized string safe for filenames (e.g., "abu_dhabi", "s_o_paulo")

    Examples:
        >>> sanitize_filename("Monaco")
        'monaco'
        >>> sanitize_filename("Abu Dhabi")
        'abu_dhabi'
        >>> sanitize_filename("Emilia-Romagna")
        'emilia_romagna'
    """
    # Convert to lowercase
    text = text.lower()
    # Replace any non-word characters (not letters, digits, underscore) with underscore
    text = re.sub(r"[^\w]+", "_", text)
    # Collapse multiple consecutive underscores into one
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    return text.strip("_")
