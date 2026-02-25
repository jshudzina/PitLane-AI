"""Generate qualifying results bar chart from FastF1 data.

Usage:
    pitlane analyze qualifying-results --year 2024 --gp Monaco --session Q
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.transforms import blended_transform_factory

from pitlane_agent.utils.constants import FIGURE_HEIGHT, FIGURE_WIDTH
from pitlane_agent.utils.fastf1_helpers import build_chart_path, format_lap_time, load_session_or_testing
from pitlane_agent.utils.plotting import ensure_color_contrast, get_driver_color_safe, save_figure, setup_plot_style

_Q1_GRAY = "#888888"


def _assign_qualifying_phases(results: pd.DataFrame) -> pd.DataFrame:
    """Assign each driver to their qualifying phase using classification position.

    Uses final position rather than NaT inspection, which is more robust for
    drivers who participated in a session but didn't set a time (e.g. a driver
    who advanced to Q2 but stalled before setting a time, or one who crashed
    in Q1 but was still classified in the Q2 zone by the stewards).

    Phase boundaries are derived from grid size:
      - Top 10 positions → Q3  (always 10, per sporting regulations)
      - Next (n−10)//2 positions → Q2  (5 for 20-car, 6 for 22-car)
      - Remaining → Q1

    Args:
        results: session.results DataFrame sorted by Position, with a
                 'Position' column

    Returns:
        results with a new 'Phase' column: "Q3", "Q2", or "Q1"
    """
    results = results.copy()
    n = len(results)
    if n < 10:
        raise ValueError(f"Expected at least 10 classified drivers, got {n}")
    n_q3 = 10
    n_q2 = (n - n_q3) // 2  # 5 for 20-car grid, 6 for 22-car grid

    def _phase(row: pd.Series) -> str:
        pos = int(row["Position"])
        if pos <= n_q3:
            return "Q3"
        if pos <= n_q3 + n_q2:
            return "Q2"
        return "Q1"

    results["Phase"] = results.apply(_phase, axis=1)
    return results


def _get_best_time(row: pd.Series) -> pd.Timedelta | None:
    """Return best time for a driver: Q3 > Q2 > Q1 (first non-NaT column)."""
    for col in ("Q3", "Q2", "Q1"):
        val = row[col]
        if not pd.isna(val):
            return val
    return None


def generate_qualifying_results_chart(
    year: int,
    gp: str | None,
    session_type: str | None,
    workspace_dir: Path,
    test_number: int | None = None,
    session_number: int | None = None,
) -> dict:
    """Generate qualifying results horizontal bar chart showing gap to pole.

    Each driver is shown as a horizontal bar where the bar length equals their
    gap to the pole position lap time. Drivers are colored by qualifying phase:
    Q3 finishers use their team color, Q2 eliminees use a dimmed team color,
    and Q1 eliminees are shown in gray. Dashed section dividers separate the
    qualifying phases.

    Supports standard qualifying (Q), sprint qualifying (SQ), and sprint
    shootout (SS) sessions. Handles both 20-car (≤2025) and 22-car (2026+)
    qualifying formats via position-based phase assignment — robust to drivers
    who advanced to a phase but didn't set a time (crash, mechanical failure).

    Args:
        year: Season year
        gp: Grand Prix name (ignored for testing sessions)
        session_type: Session identifier (Q, SQ, or SS)
        workspace_dir: Workspace directory for chart output
        test_number: Testing event number (for testing sessions)
        session_number: Session within testing event

    Returns:
        Dictionary with chart metadata and per-driver qualifying statistics

    Raises:
        ValueError: If session.results has no valid qualifying times
    """
    output_path = build_chart_path(
        workspace_dir,
        "qualifying_results",
        year,
        gp,
        session_type,
        None,
        test_number=test_number,
        session_number=session_number,
    )

    session = load_session_or_testing(year, gp, session_type, test_number=test_number, session_number=session_number)

    results = session.results.copy()

    # Validate required columns
    required_cols = {"Position", "Abbreviation", "TeamName", "Q1", "Q2", "Q3"}
    missing = required_cols - set(results.columns)
    if missing:
        raise ValueError(f"session.results missing columns: {missing}")

    # Sort by final classification position (P1 first)
    results = results.sort_values("Position").reset_index(drop=True)

    # Assign qualifying phases by classification position (not NaT inspection,
    # which fails for drivers who advanced but didn't set a time)
    results = _assign_qualifying_phases(results)

    # Compute best time per driver (highest phase reached)
    results["BestTime"] = results.apply(_get_best_time, axis=1)

    pole_time = results.iloc[0]["BestTime"]
    if pole_time is None or pd.isna(pole_time):
        raise ValueError("Pole sitter has no recorded lap time; cannot compute gaps.")
    pole_time_s = pole_time.total_seconds()

    results["GapToPole"] = results["BestTime"].apply(
        lambda t: t.total_seconds() - pole_time_s if t is not None and not pd.isna(t) else float("nan")
    )

    # Build per-driver color and alpha
    driver_colors: dict[str, str] = {}
    driver_alphas: dict[str, float] = {}
    for _, row in results.iterrows():
        abbr = row["Abbreviation"]
        phase = row["Phase"]
        if phase == "Q1":
            driver_colors[abbr] = _Q1_GRAY
            driver_alphas[abbr] = 0.9
        else:
            raw = get_driver_color_safe(abbr, session, fallback=_Q1_GRAY)
            driver_colors[abbr] = ensure_color_contrast(raw)
            driver_alphas[abbr] = 0.9 if phase == "Q3" else 0.45

    # Create figure with dynamic height for 20–22 drivers
    setup_plot_style()
    fig_height = max(FIGURE_HEIGHT, len(results) * 0.45)
    fig, ax = plt.subplots(figsize=(FIGURE_WIDTH, fig_height))

    max_gap = float(results["GapToPole"].max())
    ax.set_xlim(0, max_gap * 1.35)

    # Draw bars
    for i, (_, row) in enumerate(results.iterrows()):
        abbr = row["Abbreviation"]
        gap = float(row["GapToPole"])
        ax.barh(
            i,
            gap if gap > 0 else 0.001,  # pole bar gets a thin sliver for visibility
            height=0.65,
            color=driver_colors[abbr],
            alpha=driver_alphas[abbr],
            align="center",
        )

        # Bar end label
        label_x = gap + max_gap * 0.01
        time_str = format_lap_time(row["BestTime"])
        label_text = f"POLE  ({time_str})" if i == 0 else f"+{gap:.3f}s  ({time_str})"
        ax.text(
            label_x,
            i,
            label_text,
            va="center",
            ha="left",
            fontsize=8.5,
            color="white",
        )

    # Y-axis labels: "P{pos} {abbr}"
    y_labels = [f"P{int(row['Position'])} {row['Abbreviation']}" for _, row in results.iterrows()]
    ax.set_yticks(list(range(len(results))))
    ax.set_yticklabels(y_labels, fontsize=9)
    ax.invert_yaxis()

    # Section dividers between Q3/Q2 and Q2/Q1 phases.
    # Use a blended transform (x in axes coords, y in data coords) so the label
    # aligns exactly with the axhline regardless of axis padding.
    phase_list = results["Phase"].tolist()
    section_boundaries = [
        ("Q2", "Eliminated in Q2"),
        ("Q1", "Eliminated in Q1"),
    ]
    label_transform = blended_transform_factory(ax.transAxes, ax.transData)
    for phase_key, divider_label in section_boundaries:
        if phase_key in phase_list:
            boundary_idx = phase_list.index(phase_key)
            ax.axhline(y=boundary_idx - 0.5, color="#aaaaaa", linestyle="--", linewidth=1.0, alpha=0.6)
            ax.text(
                0.002,
                boundary_idx - 0.5,
                divider_label,
                transform=label_transform,
                va="bottom",
                ha="left",
                fontsize=8,
                color="#aaaaaa",
                fontstyle="italic",
            )

    ax.set_xlabel("Gap to Pole (seconds)")
    ax.set_title(f"{session.event['EventName']} {year} — {session.name}\nQualifying Results")
    ax.grid(True, alpha=0.25, axis="x")

    save_figure(fig, output_path)

    # Build statistics list
    pole_row = results.iloc[0]
    statistics = []
    for _, row in results.iterrows():
        best_time = row["BestTime"]
        best_s = best_time.total_seconds() if best_time is not None and not pd.isna(best_time) else None
        gap = float(row["GapToPole"])
        statistics.append(
            {
                "position": int(row["Position"]),
                "abbreviation": row["Abbreviation"],
                "team": row["TeamName"],
                "phase": row["Phase"],
                "best_time_s": round(best_s, 3) if best_s is not None else None,
                "best_time_str": format_lap_time(best_time),
                "gap_to_pole_s": round(gap, 3) if not pd.isna(gap) else None,
            }
        )

    return {
        "chart_path": str(output_path),
        "workspace": str(workspace_dir),
        "event_name": session.event["EventName"],
        "session_name": session.name,
        "year": year,
        "pole_driver": pole_row["Abbreviation"],
        "pole_time_s": round(pole_time_s, 3),
        "pole_time_str": format_lap_time(pole_time),
        "statistics": statistics,
    }
