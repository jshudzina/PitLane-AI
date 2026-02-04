# Architecture Overview

PitLane-AI is built on the [Claude Agent SDK](https://github.com/anthropics/anthropic-sdk-python), demonstrating practical applications of AI agents in domain-specific analysis. The architecture emphasizes **security**, **observability**, and **modularity**.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Interface Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  - CLI (pitlane-agent)                                          │
│  - Web Interface (pitlane-web) - FastAPI + Server-Sent Events  │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                       F1Agent (Core)                            │
├─────────────────────────────────────────────────────────────────┤
│  - Session Management                                           │
│  - Workspace Isolation                                          │
│  - Temporal Context Injection                                   │
│  - Tool Permission Enforcement                                  │
│  - OpenTelemetry Tracing                                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌──────▼─────┐  ┌───────▼──────┐
│   Skills     │  │   Tools    │  │  Data Layer  │
├──────────────┤  ├────────────┤  ├──────────────┤
│ f1-analyst   │  │ Bash       │  │ FastF1       │
│ f1-drivers   │  │ Read       │  │ Ergast API   │
│ f1-schedule  │  │ Write      │  │ Workspaces   │
│              │  │ WebFetch   │  │ Cache        │
└──────────────┘  └────────────┘  └──────────────┘
```

## Core Components

### 1. F1Agent

The main agent class that orchestrates all functionality:

- **Session Management**: Unique session IDs with workspace isolation
- **Temporal Context**: Real-time F1 calendar awareness
- **Tool Permissions**: Restricted tool access for security
- **Tracing**: OpenTelemetry observability hooks

[Learn more →](agent-system.md)

### 2. Skills System

Modular, composable skills for domain-specific analysis:

- **f1-analyst**: Lap times, strategy, telemetry analysis
- **f1-drivers**: Driver information via Ergast API
- **f1-schedule**: Event calendar and session schedules

Each skill has its own prompt, tool restrictions, and data access patterns.

[Learn more →](skills.md)

### 3. Temporal Context

Real-time awareness of the F1 calendar at multiple granularities:

- **Season Level**: Current year, phase (pre/in/post/off-season)
- **Race Weekend Level**: Current/last/next race events
- **Session Level**: Live/recent/upcoming sessions

Injected into the agent's system prompt for contextual understanding.

[Learn more →](temporal-context.md)

### 4. Tool Permissions

Defense-in-depth security through tool restrictions:

- **Bash**: Restricted to `pitlane` CLI only
- **Read/Write**: Restricted to workspace directory
- **WebFetch**: Restricted to F1-related domains
- **Skill**: No restrictions (delegated to skill permissions)

[Learn more →](tool-permissions.md)

### 5. Workspace Management

Session-based workspaces for data isolation:

```
~/.pitlane/workspaces/<session-id>/
├── .metadata.json
├── data/              # Session data
└── charts/            # Generated visualizations
```

Enables concurrent sessions and multi-user deployments.

[Learn more →](workspace-management.md)

## Data Flow

### Query Execution Flow

```
1. User Query
   ↓
2. F1Agent.chat()
   │
   ├─> Inject temporal context into system prompt
   ├─> Initialize ClaudeSDKClient with tools
   └─> Set can_use_tool permission handler
   ↓
3. Agent Reasoning
   │
   ├─> Determine relevant skill
   └─> Invoke Skill tool
   ↓
4. Skill Execution
   │
   ├─> Parse query intent
   ├─> Execute pitlane CLI command
   └─> Read workspace data / Generate chart
   ↓
5. Response Streaming
   │
   └─> Yield text chunks to user interface
```

### Data Persistence Flow

```
1. CLI Command (via Skill)
   ↓
2. FastF1 Data Fetch
   │
   ├─> Check shared cache (~/.pitlane/cache/fastf1/)
   ├─> Download if missing
   └─> Cache for future use
   ↓
3. Analysis / Visualization
   │
   ├─> Process data (lap times, strategy, etc.)
   └─> Generate matplotlib chart
   ↓
4. Workspace Storage
   │
   ├─> Save JSON to workspace/data/
   └─> Save PNG to workspace/charts/
   ↓
5. Agent Response
   │
   └─> Reference workspace files in response
```

## Key Design Principles

### 1. Security First

- **Principle of Least Privilege**: Tools have minimal necessary permissions
- **Sandboxing**: Skills operate within workspace boundaries
- **Domain Restrictions**: Web access limited to known F1 domains
- **Auditable**: All permission checks logged and traced

### 2. Observability

- **OpenTelemetry Integration**: Trace tool calls, permissions, and decisions
- **Structured Logging**: Contextual logging with session IDs
- **Inspectable Workspaces**: Persistent data for debugging

### 3. Modularity

- **Skills as Modules**: Easy to add new analysis capabilities
- **Tool-Based Architecture**: Standard Claude SDK tool patterns
- **Workspace Isolation**: Clean separation of concerns

### 4. User Experience

- **Streaming Responses**: Real-time feedback via Server-Sent Events
- **Temporal Awareness**: Agent understands "last race", "this weekend"
- **Visualizations**: Automatic chart generation for insights

## Package Structure

PitLane-AI is organized as a monorepo with two main packages:

```
packages/
├── pitlane-agent/          # Core agent library
│   ├── src/pitlane_agent/
│   │   ├── agent.py        # F1Agent class
│   │   ├── temporal/       # Temporal context system
│   │   ├── tool_permissions.py
│   │   ├── tracing.py      # OpenTelemetry hooks
│   │   ├── scripts/        # CLI commands
│   │   └── .claude/skills/ # F1 analysis skills
│   └── tests/
│
└── pitlane-web/            # Web interface
    ├── src/pitlane_web/
    │   ├── app.py          # FastAPI application
    │   ├── agent_manager.py # Multi-session management
    │   └── templates/      # Jinja2 templates
    └── tests/
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Agent Framework** | Claude Agent SDK |
| **LLM** | Claude 3.7 Sonnet |
| **F1 Data** | FastF1, Ergast API |
| **Visualization** | Matplotlib |
| **Web Framework** | FastAPI |
| **Streaming** | Server-Sent Events |
| **Tracing** | OpenTelemetry |
| **Package Manager** | uv (monorepo workspace) |
| **Testing** | pytest, pytest-asyncio |

## Deployment Models

### 1. CLI Usage

Single-user, local analysis:

```bash
pitlane-agent
# Interactive CLI session
```

### 2. Web Interface (Development)

Local web server with hot-reload:

```bash
uvx pitlane-web --env development
# Visit http://localhost:8000
```

### 3. Web Interface (Production)

!!! info "Coming Soon"
    Production deployment instructions are currently being finalized and will be available in a future release.

Supports concurrent sessions via workspace isolation.

## Next Steps

Explore specific architectural components:

- [Agent System](agent-system.md) - Core F1Agent implementation
- [Temporal Context](temporal-context.md) - F1 calendar awareness
- [Skills](skills.md) - Skill system and available skills
- [Tool Permissions](tool-permissions.md) - Security model
- [Workspace Management](workspace-management.md) - Session isolation

Or jump to usage documentation:

- [User Guide: Web Interface](../user-guide/web-interface.md) - Using PitLane-AI
- [Agent CLI](../agent-cli/cli-reference.md) - CLI reference (for agents/developers)
- [Developer Guide](../developer-guide/setup.md) - Contributing and extending
