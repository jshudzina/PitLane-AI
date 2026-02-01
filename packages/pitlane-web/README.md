# PitLane Web

Web interface for PitLane AI - F1 data analysis powered by AI agents.

## Quick Start

```bash
# Install and run with uvx (recommended)
uvx pitlane-web --env development

# Or install with pip/uv
pip install pitlane-web
pitlane-web --env development
```

## Features

- **Interactive Web UI** - Chat-based interface for F1 data analysis
- **AI-Powered Analysis** - Uses Claude Agent SDK for intelligent F1 insights
- **Session Management** - Isolated workspaces for each analysis session
- **Chart Generation** - Automatic visualization of lap times, tyre strategy, and more
- **Rate Limiting** - Built-in protection against abuse
- **OpenTelemetry Tracing** - Observable agent behavior for debugging

## Usage

### Basic Commands

```bash
# Development mode with auto-reload
uvx pitlane-web --env development

# Custom port
uvx pitlane-web --port 3000

# Production mode
uvx pitlane-web --env production --host 0.0.0.0

# See all options
uvx pitlane-web --help
```

### Environment Variables

- `PITLANE_ENV` - Environment mode (development/production/test)
- `PITLANE_TRACING_ENABLED` - Enable OpenTelemetry tracing (0/1)
- `PITLANE_HTTPS_ENABLED` - Enable secure cookies (true/false)
- `PITLANE_SESSION_MAX_AGE` - Session cookie max age in seconds
- `PITLANE_RATE_LIMIT_ENABLED` - Enable rate limiting (true/false)

### With Tracing

```bash
# Enable tracing to see agent behavior
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development
```

## Requirements

- Python 3.11 or higher (up to 3.13)
- `pitlane-agent` package (installed automatically as a dependency)

## Architecture

Built with:
- **FastAPI** - Modern web framework
- **Uvicorn** - ASGI server with auto-reload support
- **Jinja2** - Template engine for server-side rendering
- **Claude Agent SDK** - AI agent orchestration
- **FastF1** - F1 data access (via pitlane-agent)

## License

Apache-2.0

## Links

- [GitHub Repository](https://github.com/jshudzina/PitLane-AI)
- [Documentation](https://github.com/jshudzina/PitLane-AI#readme)
- [Issues](https://github.com/jshudzina/PitLane-AI/issues)
