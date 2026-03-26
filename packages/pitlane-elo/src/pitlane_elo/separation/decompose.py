"""Driver/constructor rating separation.

Isolates driver skill from constructor advantage using:
- Teammate normalisation (within-team delta)
- Car-adjusted driver score (R_driver - alpha * R_constructor)
- Driver transfer calibration events

Based on van Kesteren & Bergkamp's finding that ~88% of F1 race result
variance is explained by the constructor, ~12% by driver skill.
"""

from __future__ import annotations
