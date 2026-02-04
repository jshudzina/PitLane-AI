# Skills

Skills provide specialized capabilities to the F1 agent, enabling domain-specific analysis through structured prompts and Python scripts. Each skill is a self-contained module with its own prompt, tools, and data access patterns.

## Overview

PitLane-AI uses the [Claude Agent SDK skills system](https://github.com/anthropics/anthropic-sdk-python) to organize functionality into focused, composable modules. When the agent receives a question about F1 data, it:

1. Identifies the relevant skill based on the query
2. Invokes the skill using the `Skill` tool
3. The skill executes with its own prompt and tool restrictions
4. Results are returned to the main agent conversation

## Skill Structure

Skills live in the `.claude/skills/` directory:

```
packages/pitlane-agent/src/pitlane_agent/.claude/skills/
├── f1-analyst/
│   ├── SKILL.md           # Skill definition and prompt
│   └── references/        # Sub-skill documentation
│       ├── lap_times.md   # Lap time analysis guide
│       ├── strategy.md    # Strategy analysis guide
│       └── telemetry.md   # Telemetry analysis guide
├── f1-drivers/
│   └── SKILL.md           # Driver information skill
└── f1-schedule/
    └── SKILL.md           # Schedule queries skill
```

## Skill Definition Format

Skills are defined using frontmatter in `SKILL.md`:

```markdown
---
name: f1-analyst
description: Answer questions about F1 races, drivers, qualifying, and practice sessions.
allowed-tools: Bash(pitlane *), Read, Write
---

# F1 Data Analyst

You are an F1 data analyst with access to historical race data via FastF1...

[Skill prompt continues...]
```

**Frontmatter Fields:**

- `name`: Skill identifier (used for invocation)
- `description`: When to use this skill (shown to main agent)
- `allowed-tools`: Tools available within the skill context

## Available Skills

### f1-analyst

**Purpose**: Data analysis and visualization using FastF1

**When to Use**: Questions about lap times, race results, strategy, telemetry

**Capabilities**:
- Lap time analysis and distributions
- Tyre strategy visualization
- Telemetry comparison (speed, throttle, brake)
- Session data queries

**Tool Access**:
- `Bash`: Restricted to `pitlane` CLI commands only
- `Read`: Restricted to workspace directory
- `Write`: Restricted to workspace directory

**Example Invocation**:
```
User: "Compare Verstappen and Hamilton lap times in Monaco 2024"
Agent: [Invokes f1-analyst skill]
Skill: [Executes pitlane CLI commands, generates visualization]
```

### f1-drivers

**Purpose**: Driver information queries via Ergast API

**When to Use**: Questions about driver details, codes, nationalities

**Capabilities**:
- Driver roster by season
- Driver codes and Wikipedia links
- Nationality and career data

**Tool Access**:
- `Bash`: Restricted to `pitlane` CLI commands
- `Read`: Restricted to workspace directory

**Example Invocation**:
```
User: "Who drove for Ferrari in 2019?"
Agent: [Invokes f1-drivers skill]
Skill: [Queries Ergast API, returns driver list]
```

### f1-schedule

**Purpose**: Event calendar and session timing queries

**When to Use**: Questions about race dates, locations, session schedules

**Capabilities**:
- Season calendar with dates and locations
- Session timing (FP1, FP2, FP3, Q, R)
- Round numbers and event names

**Tool Access**:
- `Bash`: Restricted to `pitlane` CLI commands
- `Read`: Restricted to workspace directory

**Example Invocation**:
```
User: "When is the next race?"
Agent: [Invokes f1-schedule skill]
Skill: [Queries schedule, returns next event details]
```

## Skill Invocation

Skills are invoked using the `Skill` tool:

```python
# Agent SDK handles skill discovery and execution
client.invoke_tool("Skill", {"skill": "f1-analyst"})
```

The agent automatically:
1. Loads the skill prompt from `SKILL.md`
2. Applies tool restrictions from `allowed-tools`
3. Passes the user query to the skill context
4. Returns skill results to main conversation

## Workspace Integration

Skills use the session workspace for data isolation:

**Session ID**: Passed via `PITLANE_SESSION_ID` environment variable

**Workspace Structure**:
```
~/.pitlane/workspaces/<session-id>/
├── data/              # Session data (JSON)
│   ├── session_info.json
│   ├── drivers.json
│   └── schedule.json
└── charts/            # Generated visualizations (PNG)
    ├── lap_times.png
    └── strategy.png
```

Skills read/write data using the workspace path:

```bash
# Skills fetch data to workspace
pitlane fetch session-info --session-id $PITLANE_SESSION_ID --year 2024 --gp Monaco --session R

# Skills generate charts to workspace
pitlane analyze lap-times --session-id $PITLANE_SESSION_ID --drivers VER HAM
```

## Tool Permissions in Skills

Skills have **more restricted tool access** than the main agent:

| Tool | Main Agent | Skills |
|------|-----------|--------|
| Skill | ✓ Allowed | ✗ Not allowed (no nested skills) |
| Bash | Restricted to `pitlane` CLI | Restricted to `pitlane` CLI |
| Read | Workspace only | Workspace only |
| Write | Workspace only | Workspace only |
| WebFetch | F1 domains only | ✗ Not allowed (unless specified) |

This ensures skills operate within safe boundaries and can't escalate permissions.

## Sub-Skills Pattern

Complex skills like `f1-analyst` use **sub-skills** for organization:

```
f1-analyst/
├── SKILL.md                  # Main skill prompt
└── references/
    ├── lap_times.md          # Lap time analysis sub-skill
    ├── strategy.md           # Strategy analysis sub-skill
    ├── telemetry.md          # Telemetry analysis sub-skill
    └── standings.md          # Standings analysis sub-skill
```

The main skill prompt routes to sub-skills based on query type:

```markdown
## Analysis Types

Based on the user's question, read the appropriate reference file:

### Lap Time Analysis
**When to use:** Questions about lap times, pace comparison...
**Read:** [references/lap_times.md](references/lap_times.md)

### Strategy Analysis
**When to use:** Questions about tyre strategy, pit stops...
**Read:** [references/strategy.md](references/strategy.md)
```

This enables:
- Modular skill development
- Focused prompts per analysis type
- Easier testing and maintenance

## Security Model

Skills are **sandboxed** through tool restrictions:

1. **Bash Access**: Limited to `pitlane` CLI only (no arbitrary commands)
2. **File Access**: Limited to workspace directory (no system files)
3. **Network Access**: Limited to F1 domains (Ergast, Wikipedia, F1.com)
4. **No Escalation**: Skills cannot invoke other skills

This ensures:
- Data isolation between sessions
- No access to sensitive system resources
- Predictable, auditable behavior

## Adding New Skills

See [Developer Guide: Adding Skills](../developer-guide/adding-skills.md) for creating custom skills.

## Related Documentation

- [Agent System](agent-system.md) - How skills integrate with F1Agent
- [Tool Permissions](tool-permissions.md) - Tool restriction details
- [Workspace Management](workspace-management.md) - Session isolation
- [Agent CLI: Using Skills](../agent-cli/skills-usage.md) - How agent skills work
