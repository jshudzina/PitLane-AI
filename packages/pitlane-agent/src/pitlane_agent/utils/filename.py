"""Filename utilities for chart and data file generation."""

import re
import unicodedata


def sanitize_filename(text: str) -> str:
    """Sanitize text for use in filenames.

    Converts text to lowercase, strips Unicode diacritics, and replaces
    spaces and special characters with underscores to create
    ASCII-safe filenames.

    Args:
        text: Input text (e.g., GP name like "Abu Dhabi" or "São Paulo")

    Returns:
        Sanitized string safe for filenames (e.g., "abu_dhabi", "sao_paulo")

    Examples:
        >>> sanitize_filename("Monaco")
        'monaco'
        >>> sanitize_filename("Abu Dhabi")
        'abu_dhabi'
        >>> sanitize_filename("Emilia-Romagna")
        'emilia_romagna'
        >>> sanitize_filename("São Paulo")
        'sao_paulo'
    """
    # Normalize to NFD (decomposed form) and strip diacritics
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Convert to lowercase
    text = text.lower()
    # Replace any non-word characters (not letters, digits, underscore) with underscore
    text = re.sub(r"[^\w]+", "_", text)
    # Collapse multiple consecutive underscores into one
    text = re.sub(r"_+", "_", text)
    # Remove leading/trailing underscores
    return text.strip("_")
