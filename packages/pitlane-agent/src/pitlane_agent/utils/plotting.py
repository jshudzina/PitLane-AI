"""Matplotlib plotting utilities for F1 visualizations.

This module provides shared plotting utilities used across all visualization commands,
including style setup, figure saving, and color handling.
"""

from pathlib import Path

import fastf1
import fastf1.plotting
import matplotlib.pyplot as plt

from pitlane_agent.utils.constants import DEFAULT_DPI, MATPLOTLIB_DARK_THEME


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
