"""Story angle detection signals.

Translates ELO rating trajectories into narrative triggers:
- Trend detection (short-term momentum, long-term trajectory)
- Outlier detection (surprise scores, probability uplift)
- Car/driver performance decoupling
- Teammate battle tracking

See docs/F1_ELO_Story_Detection_System_Design.md §7 for thresholds.
"""

from __future__ import annotations
