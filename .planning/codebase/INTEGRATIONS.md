# External Integrations

PitLane AI integrates with Anthropic's Claude API, F1 live timing data sources, and an Ergast REST API for historical F1 data.

**Analysis Date:** 2026-05-02

## APIs & External Services

**Anthropic Claude API:**
- Service: Claude language model (Anthropic)
- SDK: `claude-agent-sdk` 0.1.47 — `ClaudeSDKClient`, `ClaudeAgentOptions`, `query()`
- Auth: `ANTHROPIC_API_KEY` environment variable (consumed by SDK, not referenced directly in this codebase)
- Used in: `packages/pitlane-agent/src/pitlane_agent/agent.py`, `packages/pitlane-agent/scripts/review_mechanical_dnfs.py`
- Tools granted to agent: `Skill`, `Bash`, `Read`, `Write`, `WebFetch`, `WebSearch` (with domain allow-lists)

**F1 Live Timing API (via FastF1):**
- Service: Formula 1 live timing service
- SDK: `fastf1` 3.8.1 — wraps HTTP calls internally; not accessed via Claude tools
- Domains accessed by FastF1 at runtime (not filterable by SDK sandbox currently):
  - `livetiming.formula1.com` — primary live timing
  - `livetiming-static.formula1.com` — static timing files
  - `api.formula1.com` — F1 official API (fastf1 >= 3.4)
  - `raw.githubusercontent.com` — fastf1 bundled datasets (driver numbers, etc.)
- Auth: None (public endpoints)
- Cache: local filesystem at `~/.pitlane/cache/fastf1/` (shared across all commands)
- Used in: `packages/pitlane-agent/src/pitlane_agent/utils/fastf1_helpers.py`, many `commands/` modules

**Ergast API (via FastF1 wrapper):**
- Service: Ergast Motor Racing Developer API — historical F1 standings and results
- SDK: `fastf1.ergast.Ergast()` client (`packages/pitlane-agent/src/pitlane_agent/utils/ergast.py`)
- Domains: `api.ergast.com`, `ergast.com`
- Auth: None (public API)
- Status: Legacy endpoint; still actively used for driver/constructor standings
- Also accessible via agent `WebFetch` tool (domain `api.ergast.com` is in allow-list)

**Formula 1 Official Website:**
- Domain: `www.formula1.com`, `formula1.com`
- Access: `WebFetch` and `WebSearch` tools (agent only, domain allow-listed)
- Auth: None

**FIA Website:**
- Domain: `www.fia.com`, `api.fia.com`
- Access: `WebFetch` and `WebSearch` tools (agent only, domain allow-listed)
- Auth: None

**Wikipedia:**
- Domain: `wikipedia.org`, `en.wikipedia.org`
- Access: `WebFetch` and `WebSearch` tools (agent only, domain allow-listed)
- Auth: None

## Data Storage

**Databases:**
- DuckDB 1.5.0 — embedded analytical database; no separate server process
  - Used in `pitlane-agent`: `packages/pitlane-agent/src/pitlane_agent/utils/elo_db.py`, `utils/stats_db.py`
  - Used in `pitlane-elo`: `packages/pitlane-elo/src/pitlane_elo/data.py`, `ratings_store.py`, `snapshots.py`
  - Override path: `PITLANE_DB_PATH` env var; defaults to path derived from `PITLANE_DATA_DIR`

**Parquet Files (bundled data):**
- Location: `packages/pitlane-agent/src/pitlane_agent/data/`
- Contents: `elo_model_state.parquet`, `session_stats.parquet`, plus `elo_snapshots/`, `qualifying_entries/`, `race_entries/` directories
- Committed directly to git (no Git LFS); declared as wheel `artifacts` in `hatchling` build
- Updated weekly by `update-data` GitHub Actions workflow → auto-PR

**File Storage:**
- Workspace files: local filesystem under `~/.pitlane/workspaces/{workspace_id}/` (generated per session)
- FastF1 cache: local filesystem at `~/.pitlane/cache/fastf1/`
- No cloud object storage

**Caching:**
- FastF1 disk cache: `~/.pitlane/cache/fastf1/` (persists between runs; cached in CI via `actions/cache@v5`)
- Numba JIT cache: `$TMPDIR/numba_cache` (in-process, ephemeral)
- Agent cache (`pitlane-web`): in-memory LRU up to 100 concurrent sessions (`AGENT_CACHE_MAX_SIZE = 100`), implemented in `packages/pitlane-web/src/pitlane_web/agent_manager.py`

## Authentication & Identity

**Auth Provider:**
- None — no user authentication system
- Web sessions use a cookie (`pitlane_session`) with a generated workspace ID; no passwords or OAuth
- Cookie settings: HttpOnly=True, SameSite=lax, Secure=True in production (configurable via `PITLANE_HTTPS_ENABLED`)
- Session max age: 7 days default (`PITLANE_SESSION_MAX_AGE`)
- Cookie name: `pitlane_session` (defined in `packages/pitlane-web/src/pitlane_web/config.py`)

**Agent Tool Sandboxing:**
- OS-level sandbox via `claude-agent-sdk` `SandboxSettings` (enabled by default)
- Additional permission layer in `packages/pitlane-agent/src/pitlane_agent/tool_permissions.py`:
  - `Bash`: restricted to `pitlane` CLI commands only when sandbox disabled
  - `Read`: restricted to workspace dir and skills dir
  - `Write`: restricted to workspace dir
  - `WebFetch`: domain allow-list (wikipedia, ergast, formula1.com, fia.com)
  - `WebSearch`: domain allow-list (wikipedia, formula1.com, fia.com) + `allowed_domains` param required

## Monitoring & Observability

**Tracing:**
- OpenTelemetry (`opentelemetry-api` 1.39.1, `opentelemetry-sdk`)
- Console-based span exporter (no external APM service)
- Disabled by default; enabled with `PITLANE_TRACING_ENABLED=1`
- Span processor: `simple` (default) or `batch` (via `PITLANE_SPAN_PROCESSOR`)
- Implementation: `packages/pitlane-agent/src/pitlane_agent/tracing.py`
- Traces agent tool calls (tool name, key param, permission decisions)

**Logs:**
- Python `logging` module throughout
- Web app log level: `PITLANE_LOG_LEVEL` env var (default `INFO`)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- No external log aggregation

**Error Tracking:**
- None — no Sentry or equivalent

## CI/CD & Deployment

**Hosting:**
- Production: ASGI process (`uvicorn`) — deployment platform not specified in repo

**CI Pipeline:**
- GitHub Actions
- Workflows:
  - `.github/workflows/pr-checks.yml` — lint (Ruff), format check, pytest (3.12/3.13/3.14 matrix), build, pre-commit; runs on PRs and pushes to `main`/`develop`
  - `.github/workflows/update-data.yml` — weekly Monday 08:00 UTC data refresh; fetches F1 data via FastF1, updates Parquet files, opens PR automatically via `peter-evans/create-pull-request@v8.1.1`
  - `.github/workflows/deploy-docs.yml` — MkDocs site deployment
  - `.github/workflows/tag-and-release.yml` — version tagging and release
  - `.github/workflows/version-bump-pr.yml` — automated version bump PRs
  - `.github/dependabot.yml` — dependency update automation

**Secrets (CI):**
- `ANTHROPIC_API_KEY` — required for agent functionality (not referenced in workflow files; expected in repo/environment secrets)

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected (FastF1 makes outbound HTTP calls, but these are library-internal, not webhook callbacks)

## Environment Configuration

**Required for agent operation:**
- `ANTHROPIC_API_KEY` — Anthropic API key (consumed by `claude-agent-sdk`)

**Optional overrides:**
- `PITLANE_DATA_DIR` — override bundled Parquet data directory
- `PITLANE_DB_PATH` — override DuckDB file path
- `PITLANE_TRACING_ENABLED=1` — enable OTel console tracing
- `PITLANE_ENV=development` — disables cookie Secure flag for local HTTP dev

**Secrets location:**
- No `.env` file in repo — configure via shell environment or CI secrets
- `detect-private-key` pre-commit hook prevents accidental secret commits

---

*Integration audit: 2026-05-02*
