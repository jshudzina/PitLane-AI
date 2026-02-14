"""Matplotlib plotting utilities for F1 visualizations.

This module provides shared plotting utilities used across all visualization commands,
including style setup, figure saving, and color handling.
"""

import colorsys
from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt

from pitlane_agent.utils.constants import DEFAULT_DPI, MATPLOTLIB_DARK_THEME

# Minimum lightness for colors on dark background (#2d2d2d)
MIN_COLOR_LIGHTNESS = 0.35


def setup_plot_style():
    """Configure matplotlib for F1-style dark theme.

    Uses MATPLOTLIB_DARK_THEME configuration from utils.constants.
    This function should be called before creating any matplotlib figures
    to ensure consistent styling across all visualizations.
    """
    plt.style.use("dark_background")
    plt.rcParams.update(MATPLOTLIB_DARK_THEME)


def save_figure(
    fig: plt.Figure,
    output_path: Path,
    dpi: int = DEFAULT_DPI,
    bbox_inches: str = "tight",
) -> None:
    """Save matplotlib figure with consistent settings.

    Handles directory creation, proper DPI settings, and memory cleanup.

    Args:
        fig: Matplotlib figure to save
        output_path: Path where figure should be saved
        dpi: Dots per inch for output (default: DEFAULT_DPI from constants)
        bbox_inches: Bounding box setting (default: "tight")
    """
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Apply tight layout and save
    fig.tight_layout()
    fig.savefig(
        str(output_path),
        dpi=dpi,
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        bbox_inches=bbox_inches,
    )

    # Clean up to free memory
    plt.close(fig)


def get_driver_color_safe(
    driver_abbr: str,
    session: fastf1.core.Session,
    fallback: str | None = None,
) -> str | None:
    """Get driver color with exception handling.

    Attempts to retrieve the official FastF1 driver color, falling back
    to a specified color or None if not available.

    Args:
        driver_abbr: Driver abbreviation (e.g., "VER", "HAM")
        session: FastF1 session object
        fallback: Optional fallback color if driver color not found

    Returns:
        Driver color hex code or fallback value
    """
    try:
        return fastf1.plotting.get_driver_color(driver_abbr, session)
    except Exception:
        return fallback


def get_driver_team(driver_abbr: str, session: fastf1.core.Session) -> str | None:
    """Get team name for a driver from session results.

    Args:
        driver_abbr: Driver abbreviation (e.g., "VER")
        session: FastF1 session object

    Returns:
        Team name string or None if not found
    """
    try:
        driver_info = session.results[session.results["Abbreviation"] == driver_abbr]
        if not driver_info.empty:
            return str(driver_info.iloc[0]["TeamName"])
    except Exception:
        pass
    return None


def ensure_color_contrast(hex_color: str, min_lightness: float = MIN_COLOR_LIGHTNESS) -> str:
    """Ensure a hex color has sufficient lightness for dark backgrounds.

    If the color's HLS lightness is below min_lightness, it is raised to that threshold
    while preserving hue and saturation.

    Args:
        hex_color: Hex color string (e.g., "#1a1a2e")
        min_lightness: Minimum lightness value (0.0-1.0)

    Returns:
        Adjusted hex color string
    """
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    if lightness < min_lightness:
        lightness = min_lightness
        r, g, b = colorsys.hls_to_rgb(h, lightness, s)
    return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
