"""ELO rating models and story detection for F1."""

__version__ = "0.4.6"

import os

# workqueue is Numba's most portable threading backend and avoids TBB/OpenMP
# deadlocks on machines where the default backend conflicts with the environment.
# Must be set before numba is imported anywhere in the package.
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")
