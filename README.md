# PitLane-AI
Bringing AI agents to F1 data analysis - interactive telemetry exploration, race strategy insights, and results analysis

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python package management in a monorepo workspace.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

## Development

### Code Quality

We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
# Run linting
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Running the Web App

```bash
uv run --directory packages/pitlane-web uvicorn pitlane_web.app:app --reload
```

If pitlane_web is not found run  `uv sync --reinstall-package pitlane-web --reinstall-package pitlane-agent` and retry

## Configuration

### WebFetch Domain Restrictions

For security, the WebFetch tool is restricted to a limited set of approved domains. This prevents the agent from accessing arbitrary websites while allowing access to F1-related data sources.

**Allowed domains:**
- `wikipedia.org` (and all subdomains like `en.wikipedia.org`, `de.wikipedia.org`)
- `ergast.com` (and `api.ergast.com`)
- `formula1.com` (and `www.formula1.com`)

If the agent attempts to fetch from an unapproved domain, the request will be denied with a message listing the allowed domains.

To modify the allowed domains, edit the `ALLOWED_WEBFETCH_DOMAINS` set in `packages/pitlane-agent/src/pitlane_agent/tool_permissions.py`.

### Tracing Configuration

PitLane AI includes optional OpenTelemetry-based tracing for debugging agent behavior.

**Environment variables:**
- `PITLANE_TRACING_ENABLED`: Set to `1` to enable tracing (default: `0`)
- `PITLANE_SPAN_PROCESSOR`: Set to `batch` for production or `simple` for testing (default: `simple`)

**Example:**
```bash
PITLANE_TRACING_ENABLED=1 PITLANE_SPAN_PROCESSOR=batch uv run pitlane session-info --year 2024 --gp Monaco --session R
```

Trace output is written to stderr and shows tool calls, permission checks, and denial reasons.
