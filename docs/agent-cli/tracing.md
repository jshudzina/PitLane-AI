# Tracing

!!! warning "Agent-Only Tool"
    Tracing is designed for agent debugging and development, not direct user interaction.
    End users should use the [Web Interface](../user-guide/web-interface.md).

PitLane-AI includes OpenTelemetry-based tracing to observe agent behavior, tool calls, and permission checks. Tracing makes the agent's decision-making transparent and debuggable.

## Quick Start

### Enable Tracing

**CLI:**
```bash
PITLANE_TRACING_ENABLED=1 pitlane-agent
```

**Web Interface:**
```bash
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development
```

**Python API:**
```python
from pitlane_agent import F1Agent

agent = F1Agent(enable_tracing=True)
```

## What Gets Traced

### 1. Tool Invocations

Every tool call is logged with:
- Tool name (Bash, Read, Write, WebFetch, Skill)
- Input parameters
- Execution timing
- Result summary

**Example:**
```
[TOOL] Bash
  Command: pitlane fetch session-info --year 2024 --gp Monaco --session R
  Duration: 1.234s
  Status: Success

[TOOL] Write
  File: ~/.pitlane/workspaces/abc123/data/session_info.json
  Size: 2.1 KB
  Status: Success
```

### 2. Permission Checks

Permission decisions are logged with rationale:

**Example:**
```
[PERMISSION] Bash: ALLOWED
  Command: pitlane fetch session-info
  Reason: Matches pitlane CLI pattern

[PERMISSION] WebFetch: DENIED
  URL: https://example.com/data
  Domain: example.com
  Reason: Domain not in allowed list (ergast.com, formula1.com, wikipedia.org)

[PERMISSION] Read: ALLOWED
  File: ~/.pitlane/workspaces/abc123/data/session_info.json
  Reason: File within workspace directory
```

### 3. Skill Execution

Skill invocations are traced:

**Example:**
```
[SKILL] f1-analyst
  Prompt: Compare Verstappen and Hamilton lap times
  Sub-skill: references/lap_times.md
  Duration: 3.456s
  Status: Success
```

### 4. Agent Decisions

High-level agent reasoning is logged:

**Example:**
```
[AGENT] Analyzing query: "Compare VER and HAM lap times in Monaco"
[AGENT] Determined intent: Lap time comparison
[AGENT] Selecting skill: f1-analyst
[AGENT] Invoking skill with parameters: year=2024, gp=Monaco, drivers=[VER, HAM]
```

## Configuration

### Environment Variables

```bash
# Enable/disable tracing
PITLANE_TRACING_ENABLED=1  # or "true", "yes", "on"

# Span processor type
PITLANE_SPAN_PROCESSOR=simple   # Default: immediate output
PITLANE_SPAN_PROCESSOR=batch    # Batched output (production)
```

### Processor Types

| Processor | Behavior | Use Case |
|-----------|----------|----------|
| `simple` | Immediate output to stderr | Development, debugging |
| `batch` | Batched output (periodic flush) | Production, performance |

**Simple Processor:**
```bash
PITLANE_SPAN_PROCESSOR=simple PITLANE_TRACING_ENABLED=1 pitlane-agent
```

**Batch Processor:**
```bash
PITLANE_SPAN_PROCESSOR=batch PITLANE_TRACING_ENABLED=1 pitlane-agent
```

## Output Format

Traces are written to **stderr** in structured format:

```
[TIMESTAMP] [LEVEL] [COMPONENT] Message
  Key: Value
  Key: Value
```

**Example:**
```
2024-05-23 14:30:15 INFO TOOL Bash invoked
  command: pitlane fetch session-info --year 2024 --gp Monaco --session R
  duration: 1.234s
  status: success

2024-05-23 14:30:16 INFO PERMISSION Read check
  tool: Read
  file_path: ~/.pitlane/workspaces/abc123/data/session_info.json
  allowed: true
  reason: File within workspace

2024-05-23 14:30:17 WARN PERMISSION WebFetch denied
  tool: WebFetch
  url: https://example.com/data
  domain: example.com
  allowed: false
  reason: Domain not in allowed list
```

## Use Cases

### Debugging Agent Behavior

**Scenario:** Agent not generating expected chart

**With Tracing:**
```
[TOOL] Bash
  Command: pitlane analyze lap-times ...
  Status: Error
  Error: No lap data found for session

[AGENT] Analysis failed: Session data not available
```

**Solution:** Fetch session info first

### Auditing Tool Usage

**Scenario:** Verify agent only uses approved tools

**With Tracing:**
```
[PERMISSION] Bash: ALLOWED (pitlane CLI)
[PERMISSION] Read: ALLOWED (workspace file)
[PERMISSION] Write: ALLOWED (workspace file)
[PERMISSION] WebFetch: DENIED (non-F1 domain)
```

**Confirmation:** Agent respects tool restrictions

### Performance Analysis

**Scenario:** Identify slow operations

**With Tracing:**
```
[TOOL] Bash (pitlane fetch session-info)
  Duration: 5.234s  ← Slow (first fetch populates cache)

[TOOL] Bash (pitlane analyze lap-times)
  Duration: 0.456s  ← Fast (uses cached data)
```

**Insight:** First fetch is slow (FastF1 download), subsequent fast

### Understanding Skill Selection

**Scenario:** Verify correct skill invoked

**With Tracing:**
```
[AGENT] Query: "Compare VER and HAM lap times"
[AGENT] Intent: Lap time analysis
[AGENT] Selected skill: f1-analyst
[SKILL] f1-analyst invoked
  Sub-skill: references/lap_times.md
```

**Confirmation:** Correct skill and sub-skill selected

## Integration with Logging

Tracing uses standard Python logging:

```python
import logging

# Set log level
logging.basicConfig(level=logging.INFO)

# Custom logger
logger = logging.getLogger("pitlane_agent")
logger.setLevel(logging.DEBUG)
```

**Log Levels:**
- `DEBUG` - Verbose internal details
- `INFO` - Tool calls, permissions, decisions
- `WARN` - Permission denials, recoverable errors
- `ERROR` - Failures, exceptions

## Production Usage

### Structured Logging

Send traces to logging infrastructure:

```python
import logging.config

logging.config.dictConfig({
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        },
    },
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
})
```

### Telemetry Export

Export to OpenTelemetry collectors:

```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure exporter
exporter = OTLPSpanExporter(endpoint="https://otlp.example.com:4317")

# Set up tracer provider
trace.set_tracer_provider(TracerProvider())
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(exporter))
```

**Backends:**
- Jaeger
- Zipkin
- Datadog
- Honeycomb
- AWS X-Ray

## CLI Integration

### Redirecting Traces

**Capture to file:**
```bash
PITLANE_TRACING_ENABLED=1 pitlane-agent 2>traces.log
```

**Filter traces:**
```bash
PITLANE_TRACING_ENABLED=1 pitlane-agent 2>&1 | grep PERMISSION
```

**Parse JSON:**
```bash
PITLANE_TRACING_ENABLED=1 pitlane-agent 2>&1 | jq -R 'fromjson?'
```

## Related Documentation

- [Architecture: Agent System](../architecture/agent-system.md) - Tracing integration points
- [Architecture: Tool Permissions](../architecture/tool-permissions.md) - Permission logging
- [Developer Guide: Testing](../developer-guide/testing.md) - Using traces in tests
