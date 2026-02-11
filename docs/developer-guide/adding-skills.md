# Adding Skills

Create custom skills to extend the F1 agent's capabilities.

## Skill Structure

Skills are defined in `.claude/skills/<skill-name>/`:

```
packages/pitlane-agent/src/pitlane_agent/.claude/skills/
└── my-skill/
    ├── SKILL.md              # Skill definition (required)
    └── references/           # Sub-skills (optional)
        └── advanced.md
```

## Creating a Skill

### 1. Create Skill Directory

```bash
mkdir -p packages/pitlane-agent/src/pitlane_agent/.claude/skills/my-skill
cd packages/pitlane-agent/src/pitlane_agent/.claude/skills/my-skill
```

### 2. Write SKILL.md

```markdown
---
name: my-skill
description: Brief description of when to use this skill
allowed-tools: Bash(pitlane *), Read, Write
---

# My Custom Skill

You are a specialist in [domain]. Answer questions about [topic] using [tools].

## Instructions

1. [Step-by-step instructions for the skill]
2. [How to use tools]
3. [Expected output format]

## Examples

**User:** [Example question]
**Response:** [How to handle it]
```

### 3. Test the Skill

```python
from pitlane_agent import F1Agent

agent = F1Agent(session_id="test")

# Ask a question that should trigger your skill
response = await agent.chat_full("Question for my skill")
print(response)
```

## Skill Definition Format

### Frontmatter

```yaml
---
name: my-skill              # Skill identifier (kebab-case)
description: When to use this skill  # Shown to main agent
allowed-tools: Bash(pitlane *), Read, Write  # Tool restrictions
---
```

**Tool Syntax:**
- `Bash` - Full bash access (not recommended)
- `Bash(pitlane *)` - Restricted to pitlane CLI
- `Read` - Read files from workspace
- `Write` - Write files to workspace
- `WebFetch` - Fetch web content (use sparingly)

### Prompt Content

Write clear instructions:

```markdown
# Skill Title

You are a [role] with access to [capabilities].

## Task

[What the skill does]

## Available Commands

### Command 1
```bash
pitlane fetch data --workspace-id $PITLANE_WORKSPACE_ID
```
[Description of what it does]

### Command 2
```bash
pitlane analyze data --workspace-id $PITLANE_WORKSPACE_ID
```
[Description]

## Output Format

[How to format the response]

## Examples

[Example conversations]
```

## Sub-Skills Pattern

For complex skills, use sub-skills:

```
my-skill/
├── SKILL.md           # Routes to sub-skills
└── references/
    ├── basic.md       # Basic operations
    └── advanced.md    # Advanced operations
```

**Main skill (SKILL.md):**
```markdown
---
name: my-skill
description: Handle multiple types of queries
allowed-tools: Bash(pitlane *), Read, Write
---

# My Skill

Based on the user's question, read the appropriate reference:

## Basic Operations
**When:** Questions about [basic topics]
**Read:** [references/basic.md](references/basic.md)

## Advanced Operations
**When:** Questions about [advanced topics]
**Read:** [references/advanced.md](references/advanced.md)
```

## Example: Race Predictions Skill

```markdown
---
name: f1-predictions
description: Predict race outcomes based on historical data
allowed-tools: Bash(pitlane *), Read, Write
---

# F1 Race Predictions

You predict Formula 1 race outcomes using historical data analysis.

## Prediction Process

1. **Fetch Historical Data**
   ```bash
   pitlane fetch session-info --workspace-id $PITLANE_WORKSPACE_ID \
     --year 2023 --gp Monaco --session R
   ```

2. **Analyze Patterns**
   - Compare historical lap times
   - Evaluate tyre strategies
   - Consider track characteristics

3. **Generate Prediction**
   - Rank drivers by probability
   - Identify key factors
   - Provide confidence levels

## Example

**User:** "Who will win the Monaco Grand Prix?"

**Response:**
"Based on historical performance at street circuits:

1. Max Verstappen (45% probability)
   - Strong in slow-speed corners
   - Consistent pace in qualifying

2. Charles Leclerc (30% probability)
   - Monaco specialist
   - Excellent in sector 3

3. Lewis Hamilton (15% probability)
   - Experienced at Monaco
   - Strong racecraft

Key factors: Qualifying position critical (80% of winners start P1-P2)"
```

## Tool Permissions

Skills inherit tool restrictions:

| Tool | Main Agent | Skill |
|------|-----------|-------|
| Bash | pitlane CLI | pitlane CLI |
| Read | Workspace | Workspace |
| Write | Workspace | Workspace |
| WebFetch | F1 domains | Only if specified |
| Skill | ✓ Allowed | ✗ No nested skills |

Skills cannot invoke other skills.

## Best Practices

1. **Clear Descriptions**: Help the agent choose the right skill
2. **Specific Instructions**: Step-by-step guidance
3. **Tool Safety**: Use `Bash(pitlane *)` not `Bash`
4. **Workspace Integration**: Save data to `$PITLANE_WORKSPACE_ID` workspace
5. **Examples**: Include example queries and responses
6. **Error Handling**: Explain common errors and solutions

## Testing Skills

```bash
# Start agent with tracing
PITLANE_TRACING_ENABLED=1 pitlane-agent

# Ask questions that trigger your skill
> Compare lap times  # Should trigger f1-analyst

# Verify skill invocation in traces
[SKILL] f1-analyst invoked
  Sub-skill: references/lap_times.md
  Duration: 2.345s
```

## Debugging Skills

Enable tracing to see skill execution:

```python
agent = F1Agent(enable_tracing=True)
response = await agent.chat_full("Test my skill")
```

Check stderr for:
- `[SKILL]` - Skill invocations
- `[TOOL]` - Tool calls from skill
- `[PERMISSION]` - Permission checks

## Skill Discovery

The Claude Agent SDK automatically discovers skills in `.claude/skills/`:

1. Scans for `SKILL.md` files
2. Parses frontmatter (name, description, allowed-tools)
3. Loads skill prompts on demand
4. Enforces tool restrictions

## Related Documentation

- [Architecture: Skills](../architecture/skills.md) - Skill system internals
- [Agent CLI: Using Skills](../agent-cli/skills-usage.md) - How agent skills work
- [Agent CLI: CLI Reference](../agent-cli/cli-reference.md) - Available CLI commands
