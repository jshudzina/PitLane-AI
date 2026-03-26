"""Qualifying-based Car Rating (Rc) computation.

Implements Xun's per-Grand-Prix car performance metric:
    Rc = (T_team_avg_qual - T_fastest_qual) / T_fastest_qual

Lower Rc = faster car. Computed per qualifying session, providing a
track-specific signal of raw car pace independent of race outcomes.
"""

from __future__ import annotations
