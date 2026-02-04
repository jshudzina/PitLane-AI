# Project Structure

PitLane-AI is organized as a Python monorepo using uv workspaces.

## Directory Layout

```
PitLane-AI/
├── pyproject.toml          # Workspace root configuration
├── uv.lock                 # Unified dependency lockfile
├── README.md
├── LICENSE
│
├── packages/
│   ├── pitlane-agent/      # Core agent library
│   │   ├── pyproject.toml  # Package metadata
│   │   ├── src/
│   │   │   └── pitlane_agent/
│   │   │       ├── __init__.py
│   │   │       ├── agent.py            # F1Agent class
│   │   │       ├── cli.py              # CLI entry point
│   │   │       ├── cli_fetch.py        # Fetch commands
│   │   │       ├── cli_analyze.py      # Analyze commands
│   │   │       ├── tool_permissions.py # Permission system
│   │   │       ├── tracing.py          # OpenTelemetry hooks
│   │   │       ├── temporal/           # Temporal context system
│   │   │       │   ├── __init__.py
│   │   │       │   ├── context.py      # Context data structures
│   │   │       │   ├── analyzer.py     # Calendar analysis
│   │   │       │   ├── cache.py        # Cache management
│   │   │       │   └── formatter.py    # Prompt formatting
│   │   │       ├── scripts/            # CLI script implementations
│   │   │       │   ├── workspace.py    # Workspace management
│   │   │       │   ├── fetch.py        # Data fetching
│   │   │       │   └── analyze.py      # Analysis functions
│   │   │       └── .claude/
│   │   │           └── skills/         # Agent skills
│   │   │               ├── f1-analyst/
│   │   │               ├── f1-drivers/
│   │   │               └── f1-schedule/
│   │   └── tests/
│   │       ├── conftest.py             # Shared fixtures
│   │       ├── test_agent.py
│   │       ├── test_tracing.py
│   │       ├── temporal/               # Temporal context tests
│   │       └── integration/            # Integration tests
│   │
│   └── pitlane-web/        # Web interface
│       ├── pyproject.toml
│       ├── src/
│       │   └── pitlane_web/
│       │       ├── __init__.py
│       │       ├── app.py              # FastAPI application
│       │       ├── cli.py              # Web CLI entry point
│       │       ├── agent_manager.py    # Agent lifecycle
│       │       ├── config.py           # Configuration
│       │       ├── security.py         # Security utilities
│       │       ├── session.py          # Session management
│       │       ├── filters.py          # Jinja2 filters
│       │       ├── templates/          # HTML templates
│       │       │   └── index.html
│       │       └── static/             # CSS, JS, images
│       └── tests/
│           ├── test_agent_manager.py
│           └── test_agent_manager_concurrency.py
│
└── docs/                   # MkDocs documentation
    ├── index.md
    ├── architecture/
    ├── user-guide/
    ├── developer-guide/
    └── api-reference/
```

## Package Descriptions

### pitlane-agent

**Purpose:** Core agent library with skills and CLI

**Key Components:**
- `agent.py` - Main F1Agent class
- `temporal/` - F1 calendar awareness system
- `tool_permissions.py` - Tool restriction logic
- `scripts/` - CLI command implementations
- `.claude/skills/` - Analysis skills

**Entry Points:**
- `pitlane` - CLI interface
- `pitlane-agent` - Interactive agent (planned)

### pitlane-web

**Purpose:** Web interface for chat-based F1 analysis

**Key Components:**
- `app.py` - FastAPI routes and SSE
- `agent_manager.py` - Agent caching and lifecycle
- `session.py` - Session management
- `templates/` - HTML UI
- `static/` - Frontend assets

**Entry Point:**
- `pitlane-web` - Web server CLI

## Key Files

### Root Configuration

#### `pyproject.toml` (root)

```toml
[project]
name = "pitlane-ai"
version = "0.1.2.dev4"
description = "AI-powered F1 data analysis"

[tool.uv.workspace]
members = [
    "packages/pitlane-agent",
    "packages/pitlane-web"
]

[tool.ruff]
line-length = 120
target-version = "py312"
```

Defines workspace members and shared tool configuration.

### Package Configuration

#### `packages/pitlane-agent/pyproject.toml`

```toml
[project]
name = "pitlane-agent"
dependencies = [
    "claude-agent-sdk",
    "fastf1",
    "matplotlib",
    "click",
    # ...
]

[project.scripts]
pitlane = "pitlane_agent.cli:pitlane"
```

Defines `pitlane-agent` package with dependencies and CLI entry point.

#### `packages/pitlane-web/pyproject.toml`

```toml
[project]
name = "pitlane-web"
dependencies = [
    "pitlane-agent",  # Workspace dependency
    "fastapi",
    "uvicorn",
    "slowapi",
    # ...
]

[project.scripts]
pitlane-web = "pitlane_web.cli:cli"
```

Defines `pitlane-web` package depending on `pitlane-agent`.

## Dependency Management

### Workspace Dependencies

Packages can depend on other workspace packages:

```toml
# packages/pitlane-web/pyproject.toml
dependencies = [
    "pitlane-agent",  # Resolved from workspace
]
```

### Lockfile

`uv.lock` contains unified lockfile for all packages:
- Ensures consistent versions across workspace
- Fast resolution and installation
- Reproducible builds

### Adding Dependencies

```bash
# Add to pitlane-agent
uv add --package pitlane-agent <package>

# Add to pitlane-web
uv add --package pitlane-web <package>

# Add dev dependency
uv add --package pitlane-agent --dev <package>
```

## Testing Structure

### Unit Tests

Located in `packages/*/tests/`:

```python
# packages/pitlane-agent/tests/test_agent.py
def test_agent_initialization():
    agent = F1Agent(session_id="test-123")
    assert agent.session_id == "test-123"
```

### Integration Tests

Marked with `@pytest.mark.integration`:

```python
# packages/pitlane-agent/tests/integration/test_fastf1_temporal.py
@pytest.mark.integration
async def test_temporal_context_live():
    ctx = get_temporal_context(force_refresh=True)
    assert ctx.current_season == 2024
```

### Fixtures

Shared fixtures in `conftest.py`:

```python
# packages/pitlane-agent/tests/conftest.py
@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for testing."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    yield workspace
```

## Documentation Structure

MkDocs-based documentation in `docs/`:

```
docs/
├── index.md                # Homepage
├── architecture/           # System design
│   ├── overview.md
│   ├── agent-system.md
│   └── ...
├── user-guide/             # Usage documentation
│   ├── cli-reference.md
│   ├── web-interface.md
│   └── ...
├── developer-guide/        # This section
│   ├── setup.md
│   ├── project-structure.md
│   └── ...
└── api-reference/          # Auto-generated API docs
    ├── pitlane-agent/
    └── pitlane-web/
```

Built with `mkdocs build` and served via GitHub Pages.

## Skills Structure

Skills are organized under `.claude/skills/`:

```
.claude/skills/
├── f1-analyst/
│   ├── SKILL.md            # Skill definition
│   └── references/         # Sub-skills
│       ├── lap_times.md
│       ├── strategy.md
│       └── telemetry.md
├── f1-drivers/
│   └── SKILL.md
└── f1-schedule/
    └── SKILL.md
```

Each skill has:
- `SKILL.md` - Frontmatter + prompt
- `references/` - Optional sub-skill documentation

## Related Documentation

- [Setup](setup.md) - Development environment setup
- [Contributing](contributing.md) - Contribution workflow
- [Adding Skills](adding-skills.md) - Creating new skills
