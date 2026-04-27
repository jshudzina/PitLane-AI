"""ELO rating models and story detection for F1."""

__version__ = "0.4.7"

import os
import tempfile

# workqueue is Numba's most portable threading backend and avoids TBB/OpenMP
# deadlocks on machines where the default backend conflicts with the environment.
# Must be set before numba is imported anywhere in the package.
os.environ.setdefault("NUMBA_THREADING_LAYER", "workqueue")

# Redirect Numba's cache to a temp directory so sandboxed environments that
# block writes to the source tree (e.g. the pitlane skill sandbox) can still
# use JIT caching.
os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "numba_cache"))
