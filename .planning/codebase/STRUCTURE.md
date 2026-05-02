<!-- refreshed: 2026-05-02 -->
# Codebase Structure

**Analysis Date:** 2026-05-02

Directory layout for PitLane AI — a uv workspace with three packages (`pitlane-agent`, `pitlane-elo`, `pitlane-web`) sharing a single lockfile.

## Directory Layout

```
PitLane-AI/
├── pyproject.toml              # Workspace root: uv workspace config, ruff, pytest settings
├── uv.lock                     # Shared lockfile for all packages
├── .pre-commit-config.yaml     # Pre-commit hooks (ruff format + lint)
├── .ruffignore                 # Ruff exclusions
├── .venv/                      # Shared virtual environment (managed by uv)
├── .github/
│   └── workflows/
│       ├── pr-checks.yml       # Lint + test on PRs
│       ├── update-data.yml     # Scheduled ELO snapshot rebuild
│       ├── tag-and-release.yml # Release automation
│       ├── version-bump-pr.yml # Automated version bump PR
│       └── deploy-docs.yml     # MkDocs to GitHub Pages
├── docs/                       # MkDocs source (architecture, API reference, guides)
│   └── architecture/
├── scripts/
│   └── bump_version.py         # Multi-package version bumper
├── .planning/
│   └── codebase/               # GSD codebase map documents (this file lives here)
├── .claude/
│   └── skills/                 # Project-level Claude skills (uv-pytest, skill-scaffolder)
│
├── packages/
│   ├── pitlane-agent/          # Core package: agent, CLI, commands, utils
│   ├── pitlane-elo/            # ELO rating models and story detection
│   └── pitlane-web/            # FastAPI web interface
```

## Package: pitlane-agent

```
packages/pitlane-agent/
├── pyproject.toml              # Package manifest; entry point: pitlane = "pitlane_agent.cli:pitlane"
├── src/
│   └── pitlane_agent/
│       ├── __init__.py         # Exports F1Agent, __version__
│       ├── agent.py            # F1Agent class — primary SDK integration point
│       ├── cli.py              # Click root group; assembles fetch/analyze/stories/workspace
│       ├── cli_fetch.py        # `pitlane fetch` sub-commands (thin Click wrappers)
│       ├── cli_analyze.py      # `pitlane analyze` sub-commands (thin Click wrappers)
│       ├── cli_stories.py      # `pitlane stories` sub-commands (detect, season)
│       ├── tool_permissions.py # can_use_tool + PreToolUse hook; sandbox + domain rules
│       ├── tracing.py          # OpenTelemetry PostToolUse hook; ANSI console tracing
│       ├── py.typed            # PEP 561 marker
│       │
│       ├── commands/           # Pure business logic (no Click dependency)
│       │   ├── __init__.py     # Re-exports all public command functions
│       │   ├── fetch/          # Data fetching commands
│       │   │   ├── __init__.py
│       │   │   ├── session_info.py
│       │   │   ├── driver_info.py
│       │   │   ├── event_schedule.py
│       │   │   ├── driver_standings.py
│       │   │   ├── constructor_standings.py
│       │   │   ├── season_summary.py
│       │   │   └── race_control.py
│       │   ├── analyze/        # Chart generation commands
│       │   │   ├── __init__.py
│       │   │   ├── lap_times.py
│       │   │   ├── lap_times_distribution.py
│       │   │   ├── tyre_strategy.py
│       │   │   ├── position_changes.py
│       │   │   ├── speed_trace.py
│       │   │   ├── telemetry.py
│       │   │   ├── track_map.py
│       │   │   ├── gear_shifts_map.py
│       │   │   ├── qualifying_results.py
│       │   │   ├── team_pace.py
│       │   │   ├── driver_lap_compare.py
│       │   │   ├── driver_lap_list.py
│       │   │   ├── season_summary.py
│       │   │   └── championship_possibilities.py
│       │   └── workspace/
│       │       ├── __init__.py
│       │       └── operations.py   # All workspace CRUD: create, list, clean, conversations
│       │
│       ├── temporal/           # F1 calendar awareness
│       │   ├── __init__.py     # Public API: get_temporal_context, format_for_system_prompt
│       │   ├── context.py      # Dataclasses + TemporalContextManager + global get_temporal_context()
│       │   ├── analyzer.py     # TemporalAnalyzer: FastF1 schedule → TemporalContext
│       │   ├── cache.py        # File-based JSON cache with TTL
│       │   └── formatter.py    # format_as_text, format_for_system_prompt
│       │
│       ├── utils/              # Shared helpers
│       │   ├── __init__.py
│       │   ├── fastf1_helpers.py   # load_session(), setup_fastf1_cache(), validate_session_or_test()
│       │   ├── fastf1_cache.py     # get_fastf1_cache_dir() → ~/.pitlane/cache/fastf1/
│       │   ├── elo_db.py           # DuckDB queries over bundled Parquet ELO data
│       │   ├── stats_db.py         # DuckDB queries over session_stats.parquet
│       │   ├── race_stats.py       # Race-level stat computations (overtakes, SC counts)
│       │   ├── telemetry_analysis.py # Telemetry processing helpers
│       │   ├── plotting.py         # Shared Matplotlib/Seaborn/Plotly helpers
│       │   ├── circuits.py         # Circuit metadata (lengths, locations)
│       │   ├── constants.py        # MIN_F1_YEAR, team color maps, etc.
│       │   ├── filename.py         # sanitize_filename()
│       │   └── cli_helpers.py      # get_workspace_id() (reads PITLANE_WORKSPACE_ID env)
│       │
│       ├── data/               # Bundled static data (committed Parquet files)
│       │   ├── elo_model_state.parquet     # Current ELO ratings for all drivers
│       │   ├── session_stats.parquet       # Pre-computed race statistics
│       │   ├── elo_snapshots/<year>/<round>.parquet  # Per-race ELO snapshots
│       │   ├── race_entries/<year>/<round>.parquet   # Raw race entry data
│       │   └── qualifying_entries/<year>/<round>.parquet
│       │
│       └── .claude/
│           └── skills/         # Claude agent skills (loaded by F1Agent at runtime)
│               ├── f1-analyst/     # Core analyst persona and reasoning rules
│               ├── f1-2026-season/ # 2026 season context
│               ├── f1-drivers/     # Driver reference data
│               ├── f1-schedule/    # Schedule lookup guidance
│               ├── race-control/   # Race control message interpretation
│               ├── story-lines/    # Story signal narration guidance
│               └── web-search/     # Web search usage rules
│
├── scripts/                    # Dev/data maintenance scripts (not installed)
│   ├── update_elo_data.py      # Re-runs ELO pipeline and updates bundled data
│   ├── update_stats.py         # Re-computes session_stats.parquet
│   ├── export_db_to_parquet.py # DuckDB → Parquet export utility
│   ├── load_elo_history.py     # Historical data loader
│   └── review_mechanical_dnfs.py
│
└── tests/
    ├── conftest.py
    ├── test_agent.py
    ├── test_cli.py
    ├── test_cli_stories.py
    ├── test_permission_hooks.py
    ├── test_tracing.py
    ├── test_webfetch_permissions.py
    ├── test_workspace.py
    ├── commands/               # Per-command test files
    ├── integration/            # Real FastF1 API tests (marked `integration`)
    ├── temporal/               # Temporal context tests
    ├── scripts/                # Script tests
    └── utils/                  # Utility tests
```

## Package: pitlane-elo

```
packages/pitlane-elo/
├── pyproject.toml              # Entry point: pitlane-elo = "pitlane_elo.cli:main"
├── src/
│   └── pitlane_elo/
│       ├── __init__.py
│       ├── cli.py              # Click root: run, snapshot, calibrate, compare, stories
│       ├── cli_stories.py      # `pitlane-elo stories` sub-commands
│       ├── config.py           # EloConfig dataclass; ENDURE_ELO_CALIBRATED, ENDURE_ELO_DEFAULT
│       ├── data.py             # DuckDB/Parquet data access: get_race_entries, group_entries_by_race
│       ├── snapshots.py        # build_snapshots, catchup_snapshots, get_race_snapshot
│       ├── ratings_store.py    # RatingsStore: DuckDB persistence for elo_snapshots + model state
│       ├── calibration.py      # Hyperparameter search via SciPy
│       │
│       ├── ratings/
│       │   ├── base.py         # RatingModel ABC: process_race(), predict_win_probabilities()
│       │   ├── endure_elo.py   # EndureElo (Powell model, Numba JIT — preferred model)
│       │   ├── speed_elo.py    # SpeedElo (pairwise)
│       │   └── constructor_elo.py
│       │
│       ├── stories/
│       │   └── signals.py      # detect_stories() → list[StorySignal]; thresholds from design doc §7
│       │
│       ├── separation/
│       │   ├── decompose.py    # TeammateNormaliser, within-team delta tracking
│       │   ├── car_rating.py   # Car rating (Rc = team_avg_qual / fastest_qual)
│       │   └── alpha_estimation.py # van Kesteren alpha (88% constructor / 12% driver)
│       │
│       ├── prediction/
│       │   ├── forecast.py     # evaluate_model(), compare_models(), run_historical()
│       │   ├── scoring.py      # Log-likelihood and Brier score metrics
│       │   └── bayesian_forecast.py # PyMC/Bayesian alternative (optional dependency)
│       │
│       └── bayesian/
│           ├── base.py         # BayesianModel base
│           ├── data_prep.py    # Data preparation for PyMC models
│           └── van_kesteren.py # van Kesteren hierarchical Bayesian model
│
├── notebooks/                  # Jupyter exploration notebooks (not installed)
├── artifacts/                  # Research artifacts / reference outputs
└── tests/
    ├── conftest.py
    ├── test_data.py
    ├── test_snapshots.py
    ├── test_config.py
    ├── test_calibration.py
    ├── test_integration.py     # Full pipeline integration (marked `integration`)
    ├── ratings/
    │   ├── test_endure_elo.py
    │   ├── test_speed_elo.py
    │   └── test_constructor_elo.py
    ├── stories/test_signals.py
    ├── separation/
    │   ├── test_decompose.py
    │   ├── test_car_rating.py
    │   └── test_alpha_estimation.py
    ├── prediction/
    │   ├── test_forecast.py
    │   └── test_scoring.py
    └── bayesian/
        ├── test_data_prep.py
        └── test_van_kesteren.py
```

## Package: pitlane-web

```
packages/pitlane-web/
├── pyproject.toml              # Entry point: pitlane-web = "pitlane_web.cli:main"
├── src/
│   └── pitlane_web/
│       ├── __init__.py
│       ├── app.py              # FastAPI app, all routes, SSE chat, rate limiter setup
│       ├── agent_manager.py    # AgentCache (LRU OrderedDict of F1Agent instances)
│       ├── cli.py              # Click CLI: `pitlane-web` → uvicorn start
│       ├── config.py           # Constants: cookie settings, rate limit strings, cache max size
│       ├── filters.py          # Jinja2 custom filters (registered at startup)
│       ├── security.py         # is_safe_filename(), is_valid_session_id()
│       └── session.py          # generate_workspace_id(), validate_session_safely()
└── tests/
```

## Key File Locations

**Primary Entry Points:**
- CLI entry: `packages/pitlane-agent/src/pitlane_agent/cli.py` — `@click.group() def pitlane()`
- ELO CLI entry: `packages/pitlane-elo/src/pitlane_elo/cli.py` — `@click.group() def main()`
- Web entry: `packages/pitlane-web/src/pitlane_web/app.py` — `app = FastAPI(...)`
- Agent SDK entry: `packages/pitlane-agent/src/pitlane_agent/agent.py` — `class F1Agent`

**Configuration:**
- Workspace root: `pyproject.toml` — ruff, pytest, uv workspace members
- Package deps: `packages/pitlane-agent/pyproject.toml`, `packages/pitlane-elo/pyproject.toml`, `packages/pitlane-web/pyproject.toml`
- Web config: `packages/pitlane-web/src/pitlane_web/config.py` — all env-driven constants
- ELO config: `packages/pitlane-elo/src/pitlane_elo/config.py` — `EloConfig` dataclass, calibrated defaults

**Core Logic:**
- Tool permission enforcement: `packages/pitlane-agent/src/pitlane_agent/tool_permissions.py`
- Temporal context: `packages/pitlane-agent/src/pitlane_agent/temporal/context.py`
- ELO model (preferred): `packages/pitlane-elo/src/pitlane_elo/ratings/endure_elo.py`
- Story detection: `packages/pitlane-elo/src/pitlane_elo/stories/signals.py`
- Workspace operations: `packages/pitlane-agent/src/pitlane_agent/commands/workspace/operations.py`

**Testing:**
- Agent tests: `packages/pitlane-agent/tests/test_agent.py`
- CLI tests: `packages/pitlane-agent/tests/test_cli.py`
- Permission tests: `packages/pitlane-agent/tests/test_permission_hooks.py`
- ELO model tests: `packages/pitlane-elo/tests/ratings/`
- Integration (real API): `packages/pitlane-agent/tests/integration/`, `packages/pitlane-elo/tests/test_integration.py`

**Runtime Data:**
- User workspaces: `~/.pitlane/workspaces/<uuid>/` (created at runtime)
- FastF1 cache: `~/.pitlane/cache/fastf1/`
- Temporal cache: `~/.pitlane/cache/temporal/`
- Matplotlib config: `~/.pitlane/cache/matplotlib/` (set via `MPLCONFIGDIR`)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`
- CLI modules prefixed with `cli_`: `cli_fetch.py`, `cli_analyze.py`, `cli_stories.py`
- Test files: `test_<module>.py`

**Directories:**
- Python packages: `snake_case/` (e.g., `pitlane_agent`, `pitlane_elo`, `pitlane_web`)
- Distribution packages: `kebab-case/` (e.g., `pitlane-agent`, `pitlane-elo`, `pitlane-web`)

**Python:**
- Classes: `PascalCase` (`F1Agent`, `RatingModel`, `StorySignal`)
- Functions/methods: `snake_case`
- Constants: `SCREAMING_SNAKE_CASE` (`ALLOWED_WEBFETCH_DOMAINS`, `MIN_F1_YEAR`)
- Private helpers: `_snake_case` (`_is_allowed_bash_command`, `_inclusion_exclusion`)

## Where to Add New Code

**New fetch command (e.g., `pitlane fetch pit-stops`):**
1. Implementation: `packages/pitlane-agent/src/pitlane_agent/commands/fetch/pit_stops.py` — pure function `get_pit_stops(year, gp, session)`
2. Register: add import in `packages/pitlane-agent/src/pitlane_agent/commands/fetch/__init__.py`
3. CLI binding: add `@fetch.command()` in `packages/pitlane-agent/src/pitlane_agent/cli_fetch.py`
4. Tests: `packages/pitlane-agent/tests/commands/test_pit_stops.py`

**New analysis/chart command:**
1. Implementation: `packages/pitlane-agent/src/pitlane_agent/commands/analyze/<name>.py` — function `generate_<name>_chart(year, gp, session, workspace_dir)`
2. Register: add import in `packages/pitlane-agent/src/pitlane_agent/commands/analyze/__init__.py`
3. CLI binding: add `@analyze.command()` in `packages/pitlane-agent/src/pitlane_agent/cli_analyze.py`
4. Tests: `packages/pitlane-agent/tests/commands/test_<name>.py`

**New ELO rating model:**
1. Subclass `RatingModel` in `packages/pitlane-elo/src/pitlane_elo/ratings/<model_name>.py`
2. Implement `process_race()` and `predict_win_probabilities()`
3. Register in `packages/pitlane-elo/src/pitlane_elo/ratings/__init__.py`
4. Add to `_make_model()` in `packages/pitlane-elo/src/pitlane_elo/cli.py`
5. Tests: `packages/pitlane-elo/tests/ratings/test_<model_name>.py`

**New utility helper:**
- Shared F1 data helpers: `packages/pitlane-agent/src/pitlane_agent/utils/`
- ELO-specific math/data: `packages/pitlane-elo/src/pitlane_elo/`

**New Claude skill:**
- Location: `packages/pitlane-agent/src/pitlane_agent/.claude/skills/<skill-name>/`
- Must include a `SKILL.md` (index file) and any `rules/*.md` files
- Skills are loaded automatically by `F1Agent` via `settings_sources=["project"]` and `cwd=PACKAGE_DIR`

**New web route:**
- Add route handler in `packages/pitlane-web/src/pitlane_web/app.py`
- Config constants in `packages/pitlane-web/src/pitlane_web/config.py`
- Security helpers in `packages/pitlane-web/src/pitlane_web/security.py`

## Special Directories

**`packages/pitlane-agent/src/pitlane_agent/data/`:**
- Purpose: Bundled static Parquet files shipped inside the wheel
- Generated: Yes (by `scripts/update_elo_data.py`, `scripts/update_stats.py`)
- Committed: Yes — binary Parquet files are committed directly to git by design (no Git LFS)

**`packages/pitlane-agent/src/pitlane_agent/.claude/skills/`:**
- Purpose: Claude Agent SDK skill definitions loaded at runtime by `F1Agent`
- Generated: No (hand-authored Markdown)
- Committed: Yes

**`.planning/codebase/`:**
- Purpose: GSD codebase map documents consumed by `/gsd-plan-phase` and `/gsd-execute-phase`
- Generated: Yes (by GSD mapper)
- Committed: Yes

**`~/.pitlane/` (runtime, not in repo):**
- Purpose: All user-facing runtime state: workspaces, FastF1 cache, temporal cache, matplotlib config
- Generated: Yes (at runtime by the agent and CLI)
- Committed: No

---

*Structure analysis: 2026-05-02*
