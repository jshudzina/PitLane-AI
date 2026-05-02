# Technology Stack

F1 data analysis AI agent platform built as a Python uv monorepo with three packages.

**Analysis Date:** 2026-05-02

## Languages

**Primary:**
- Python 3.12–3.14 — all packages; `requires-python = ">=3.12,<3.15"`

**Secondary:**
- Jinja2 templates — web UI (`packages/pitlane-web/src/pitlane_web/templates/`)
- HTML/CSS — web frontend (`packages/pitlane-web/src/pitlane_web/static/`)

## Runtime

**Environment:**
- Python 3.12 (CI baseline), tested against 3.12, 3.13, 3.14
- Local dev venv managed by uv at `.venv/`

**Package Manager:**
- uv 0.9.26 (pinned in CI via `astral-sh/setup-uv@v7`)
- Lockfile: `uv.lock` present and committed
- NEVER use pip — uv only (enforced by skill)

## Workspace Structure

uv workspace with root `pyproject.toml` and three member packages:

| Package | Path | Entry Points |
|---------|------|-------------|
| `pitlane-agent` | `packages/pitlane-agent/` | `pitlane` CLI (`pitlane_agent.cli:pitlane`) |
| `pitlane-elo` | `packages/pitlane-elo/` | `pitlane-elo` CLI (`pitlane_elo.cli:main`) |
| `pitlane-web` | `packages/pitlane-web/` | `pitlane-web` CLI (`pitlane_web.cli:main`) |

## Frameworks

**Core Agent:**
- `claude-agent-sdk` 0.1.47 (requires `>=0.1.40`) — Anthropic Claude Agent SDK; drives the AI agent loop, tool permissions, sandboxing, hooks

**Web:**
- `fastapi` 0.128.0 (requires `>=0.115`) — async HTTP API and server-rendered UI
- `uvicorn[standard]` 0.40.0 (requires `>=0.30`) — ASGI server
- `jinja2` >=3.1 — HTML templating
- `slowapi` 0.1.9 — rate limiting middleware for FastAPI
- `python-multipart` >=0.0.9 — form body parsing
- `markdown` >=3.5 — agent response rendering

**Testing:**
- `pytest` >=9.0.3 — test runner
- `pytest-asyncio` >=0.24 — async test support (`asyncio_mode = "auto"`)
- `pytest-cov` >=4.1 — coverage reporting
- `pytest-mock` >=3.12 — mocking helpers
- `pytest-timeout` >=2.2.0 — test timeouts
- `click.testing.CliRunner` — CLI integration tests (via click)

**Build:**
- `hatchling` — build backend for all three packages
- `uv build --all-packages` — produces wheels/sdists to `dist/`

## Key Dependencies

**F1 Data:**
- `fastf1` 3.8.1 (requires `>=3.8`) — primary F1 telemetry, session, and schedule data library; wraps F1 live timing and Ergast APIs. Cache at `~/.pitlane/cache/fastf1/`

**ELO / Statistical Modeling:**
- `numpy` 2.4.1 (requires `>=1.24`) — numerical arrays
- `scipy` 1.17.0 (requires `>=1.10`) — statistical functions
- `numba` 0.64.0 (requires `>=0.60`) — JIT compilation for ELO rating inner loops; cache redirected to `$TMPDIR/numba_cache` at import time. Threading layer forced to `workqueue` for compatibility.

**Database:**
- `duckdb` 1.5.0 (requires `>=1.5.0`) — embedded analytical database; reads/writes Parquet files; used in both `pitlane-agent` and `pitlane-elo`

**Visualization:**
- `matplotlib` 3.10.8 (requires `>=3.8`) — race charts, telemetry plots; MPLCONFIGDIR redirected to workspace tmp
- `plotly` 6.5.2 (requires `>=5.20`) — interactive charts
- `seaborn` 0.13.2 (requires `>=0.13.0`) — statistical visualization

**CLI:**
- `click` >=8.1.0 — CLI framework for all scripts and commands (required; argparse is not used)

**Networking:**
- `backoff` 2.2.1 (requires `>=2.2.1`) — retry logic for API calls

**Observability:**
- `opentelemetry-api` 1.39.1 (requires `>=1.24.0`) — tracing API
- `opentelemetry-sdk` >=1.24.0 — console span exporter; controlled by `PITLANE_TRACING_ENABLED=1`

**Optional (pitlane-elo extras):**
- `pymc` >=5.0 + `arviz` >=0.15 — Bayesian modeling (optional extra `[bayesian]`; skipped in CI on Python 3.14; tests in `tests/bayesian/` excluded by default)
- `jupyter` + `pandas` — notebook support (optional extra `[notebooks]`)

## Dev Tools

**Linting/Formatting:**
- `ruff` >=0.15.12 — linter + formatter; line-length 120, target Python 3.12
- Config: `[tool.ruff]` in root `pyproject.toml`
- Rules enabled: E, W, F, I (isort), N (pep8-naming), UP (pyupgrade), B (bugbear), C4, SIM

**Pre-commit:**
- `pre-commit` >=4.6.0
- Config: `.pre-commit-config.yaml`
- Hooks: `ruff` (lint + fix), `ruff-format`, standard file checks, `detect-private-key`, conventional-pre-commit (commit message enforcement)

**Documentation:**
- `mkdocs-material` >=9.7.1 — docs site
- Config: `mkdocs.yml`
- `mkdocstrings[python]` >=1.0.4 — API reference from docstrings

**Profiling (pitlane-elo dev):**
- `py-spy` >=0.4.1
- `pyinstrument` >=5.1.2

## Configuration

**Environment Variables:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `PITLANE_TRACING_ENABLED` | `0` | Enable OpenTelemetry console tracing (`1` to enable) |
| `PITLANE_SPAN_PROCESSOR` | `simple` | OTel span processor type (`simple` or `batch`) |
| `PITLANE_WORKSPACE_ID` | auto-generated | Active workspace identifier (set by agent at runtime) |
| `PITLANE_DATA_DIR` | package bundled | Override path for Parquet data files |
| `PITLANE_DB_PATH` | derived from data dir | Override DuckDB path |
| `PITLANE_ENV` | `production` | Environment mode (`production`, `development`, `test`) |
| `PITLANE_LOG_LEVEL` | `INFO` | Log level for web app |
| `PITLANE_HTTPS_ENABLED` | derived from env | Force cookie `Secure` flag |
| `PITLANE_SESSION_MAX_AGE` | `604800` (7 days) | Session cookie max age in seconds |
| `PITLANE_RATE_LIMIT_ENABLED` | `true` | Toggle rate limiting |
| `PITLANE_RATE_LIMIT_SESSION` | `10/minute` | Rate limit for session creation |
| `PITLANE_RATE_LIMIT_CHAT` | `30/minute` | Rate limit for chat messages |
| `PITLANE_RATE_LIMIT_CHART` | `100/minute` | Rate limit for chart requests |
| `NUMBA_THREADING_LAYER` | `workqueue` | Set at import time in `pitlane_elo/__init__.py` |
| `NUMBA_CACHE_DIR` | `$TMPDIR/numba_cache` | Set at import time in `pitlane_elo/__init__.py` |
| `MPLCONFIGDIR` | workspace tmp dir | Set at agent init in `agent.py` |
| `ANTHROPIC_API_KEY` | required | Consumed by `claude-agent-sdk` (not set by this codebase) |

**No `.env` file present** — environment is configured externally (shell or CI secrets).

## Build Configuration

- `hatchling` build backend per package
- Parquet data files (`*.parquet`) are declared as `artifacts` in `pitlane-agent` wheel — committed directly to git, not LFS
- Build command: `uv build --all-packages` → `dist/`

## Platform Requirements

**Development:**
- Python 3.12–3.14
- uv 0.9.26+
- Apple Silicon supported; prefer MLX or PyTorch (MPS) over jax-metal for ML; CPU JAX fallback for PyMC

**CI:**
- GitHub Actions on `ubuntu-latest`
- Matrix: Python 3.12, 3.13, 3.14
- uv 0.9.26 pinned

**Production:**
- ASGI process via `uvicorn` behind a reverse proxy
- No Docker configuration present

---

*Stack analysis: 2026-05-02*
