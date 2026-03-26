"""Prediction assessment metrics.

Pure functions operating on (predicted, actual) arrays:
- Log-likelihood of race winner
- Brier score (win probability calibration)
- RMSE on finishing position
- Calibration curve data
"""

from __future__ import annotations
