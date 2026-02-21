# Installation

PitLane-AI is available as three Python packages on PyPI. You can install just the components you need, or install everything at once.

## Requirements

- Python 3.12, 3.13, or 3.14
- pip or [uv](https://docs.astral.sh/uv/) package manager
- **Anthropic API key** — Required to run the Claude-powered agent. Get one at [console.anthropic.com](https://console.anthropic.com).

## Install Options

### Option 1: Full Install (Recommended)

Install both the CLI agent and web interface:

```bash
pip install pitlane-ai
```

This meta-package includes both `pitlane-agent` and `pitlane-web`.

### Option 2: CLI Only

If you only need the command-line interface:

```bash
pip install pitlane-agent
```

### Option 3: Web Interface Only

If you only need the web interface:

```bash
pip install pitlane-web
```

!!! note
    The web interface depends on `pitlane-agent`, so installing `pitlane-web` will also install the agent.

## Using uvx (No Installation Required)

For one-off usage without installing, use `uvx`:

```bash
# Run CLI commands
uvx pitlane-agent workspace create --workspace-id my-analysis

# Run web server
uvx pitlane-web --env development
```

## Development Installation

For contributing to PitLane-AI, clone the repository and install in development mode:

```bash
# Clone the repository
git clone https://github.com/jshudzina/PitLane-AI.git
cd PitLane-AI

# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install with documentation dependencies
uv sync --group docs

# Install with development dependencies
uv sync --group dev
```

See the [Developer Guide](../developer-guide/setup.md) for more details.

## Verify Installation

After installation, verify that the packages are installed correctly:

```bash
# Check pitlane-agent version
python -c "import pitlane_agent; print(pitlane_agent.__version__)"

# Check pitlane-web version
python -c "import pitlane_web; print(pitlane_web.__version__)"

# Try the CLI
pitlane --help

# Try the web server
pitlane-web --help
```

## Dependencies

PitLane-AI is built on top of industry-standard F1 data APIs that handle all the analytical heavy lifting:

### Core Data APIs

- **[FastF1](https://docs.fastf1.dev/)** - F1 telemetry, timing, lap times, and session data access
- **[jolpica-f1 (Ergast API)](https://github.com/jolpica/jolpica-f1)** - Historical F1 driver rosters, race results, and championship data (accessed via FastF1's ergast module)

### Agent & Visualization

- **Claude Agent SDK** - AI agent orchestration and skill system
- **Matplotlib** - Chart generation and data visualization
- **FastAPI** - Web interface backend (pitlane-web only)
- **OpenTelemetry** - Optional tracing and observability

All dependencies are automatically installed when you install PitLane-AI.

## Upgrading

To upgrade to the latest version:

```bash
pip install --upgrade pitlane-ai
```

Or for individual packages:

```bash
pip install --upgrade pitlane-agent
pip install --upgrade pitlane-web
```

## Uninstalling

To remove PitLane-AI:

```bash
pip uninstall pitlane-ai pitlane-agent pitlane-web
```

## Next Steps

- [Quick Start Guide](quick-start.md) - Run your first analysis
- [Configuration](configuration.md) - Configure PitLane-AI settings
- [Web Interface](../user-guide/web-interface.md) - Learn how to use the web app
- [Agent CLI](../agent-cli/cli-reference.md) - CLI reference (for agents/developers)
