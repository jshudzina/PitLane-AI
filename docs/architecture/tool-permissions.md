# Tool Permissions

PitLane-AI implements a comprehensive tool permission system to ensure the agent operates within safe, predictable boundaries. The system restricts tool access based on domain, file paths, and command patterns.

## Overview

Tool permissions provide **defense-in-depth security** through:

1. **Tool Allowlist**: Only specific tools are available
2. **Domain Restrictions**: Web access limited to F1-related domains
3. **Path Restrictions**: File access limited to workspace directories
4. **Command Restrictions**: Shell access limited to PitLane CLI

This ensures the agent can't access sensitive data, execute arbitrary code, or make unauthorized network requests.

## Permission Architecture

```
┌──────────────────────────────────────┐
│      F1Agent.chat()                  │
└──────────────┬───────────────────────┘
               │
               ├──> ClaudeSDKClient
               │    (allowed_tools, can_use_tool)
               │
               └──> can_use_tool_with_context()
                    │
                    ├──> Workspace Context Injection
                    └──> tool_permissions.can_use_tool()
                         │
                         ├──> Bash: pitlane CLI only
                         ├──> Read: workspace paths only
                         ├──> Write: workspace paths only
                         └──> WebFetch: F1 domains only
```

## Allowed Tools

The agent has access to **five tools** only:

```python
allowed_tools=["Skill", "Bash", "Read", "Write", "WebFetch"]
```

Any attempt to use other tools (Edit, Grep, Task, etc.) is blocked at the SDK level.

## Tool Restrictions

### Bash: PitLane CLI Only

**Rule**: Only `pitlane` CLI commands are permitted.

**Validation**:
1. Extract command (skip environment variables)
2. Check command starts with `pitlane `
3. Validate only allowed environment variables are used

**Allowed Environment Variables**:
- `PITLANE_SESSION_ID`
- `PITLANE_CACHE_DIR`
- `PITLANE_TRACING_ENABLED`
- `PITLANE_SPAN_PROCESSOR`

**Permitted Commands**:
```bash
✓ pitlane fetch session-info --year 2024 --gp Monaco
✓ PITLANE_SESSION_ID=abc123 pitlane analyze lap-times
✓ pitlane workspace list
```

**Blocked Commands**:
```bash
✗ ls -la
✗ cat /etc/passwd
✗ python script.py
✗ curl https://example.com
✗ CUSTOM_VAR=foo pitlane fetch ...
```

**Error Message**:
```
Bash is restricted to 'pitlane' CLI commands only.
Use 'pitlane <subcommand>' to execute F1 data operations.
```

### Read: Workspace Only

**Rule**: File reads are restricted to the workspace directory.

**Validation**:
1. Resolve file path to absolute path
2. Resolve workspace directory to absolute path
3. Check if file path starts with workspace path

**Permitted Reads**:
```python
✓ Read(file_path="~/.pitlane/workspaces/<session-id>/data/session_info.json")
✓ Read(file_path="~/.pitlane/workspaces/<session-id>/charts/lap_times.png")
```

**Blocked Reads**:
```python
✗ Read(file_path="/etc/passwd")
✗ Read(file_path="~/.ssh/id_rsa")
✗ Read(file_path="/Users/alice/Documents/secrets.txt")
```

**Error Message**:
```
Read access denied. File must be within workspace directory:
~/.pitlane/workspaces/<session-id>
```

### Write: Workspace Only

**Rule**: File writes are restricted to the workspace directory.

**Validation**: Same as Read (path must be within workspace).

**Permitted Writes**:
```python
✓ Write(file_path="~/.pitlane/workspaces/<session-id>/data/results.json")
✓ Write(file_path="~/.pitlane/workspaces/<session-id>/charts/strategy.png")
```

**Blocked Writes**:
```python
✗ Write(file_path="/tmp/malicious.sh")
✗ Write(file_path="~/Documents/data.txt")
✗ Write(file_path="/var/log/app.log")
```

**Error Message**:
```
Write access denied. File must be within workspace directory:
~/.pitlane/workspaces/<session-id>
```

### WebFetch: F1 Domains Only

**Rule**: Web requests are restricted to F1-related domains.

**Allowed Domains**:
- `wikipedia.org` (and `en.wikipedia.org`)
- `ergast.com` (and `api.ergast.com`)
- `formula1.com` (and `www.formula1.com`)

**Validation**:
1. Parse URL to extract domain
2. Remove `www.` prefix for comparison
3. Check exact match or subdomain match
4. Allow subdomains (e.g., `fr.wikipedia.org`)

**Permitted Requests**:
```python
✓ WebFetch(url="https://en.wikipedia.org/wiki/Lewis_Hamilton")
✓ WebFetch(url="https://api.ergast.com/api/f1/2024/drivers.json")
✓ WebFetch(url="https://www.formula1.com/en/results.html")
✓ WebFetch(url="https://fr.wikipedia.org/wiki/Monaco")
```

**Blocked Requests**:
```python
✗ WebFetch(url="https://example.com/data")
✗ WebFetch(url="https://github.com/user/repo")
✗ WebFetch(url="https://api.openweathermap.org/data")
```

**Error Message**:
```
Domain 'example.com' is not in the allowed list.
Allowed domains: ergast.com, formula1.com, wikipedia.org
```

## Permission Context

Permissions are evaluated with **workspace context**:

```python
async def can_use_tool_with_context(tool_name, input_params, context):
    # Inject workspace context
    context_with_workspace = {
        **context,
        "workspace_dir": workspace_dir,
        "session_id": session_id,
    }
    return await can_use_tool(tool_name, input_params, context_with_workspace)
```

This enables:
- Read/Write restrictions based on session workspace
- Audit logs with session context
- Tracing permission checks

## Permission Flow

When a tool is invoked:

```
1. Agent calls tool (e.g., Read)
   │
   ├──> SDK invokes can_use_tool_with_context()
   │    │
   │    ├──> Inject workspace_dir and session_id
   │    └──> Call tool_permissions.can_use_tool()
   │         │
   │         ├──> Validate tool parameters
   │         │
   │         ├──> If allowed:
   │         │    └──> Return PermissionResultAllow()
   │         │
   │         └──> If denied:
   │              ├──> Log denial (with context)
   │              ├──> Log tracing span (if enabled)
   │              └──> Return PermissionResultDeny(message)
   │
   ├──> If allowed: Tool executes
   └──> If denied: Error returned to agent
```

## Tracing Permission Checks

Permission checks are logged via OpenTelemetry spans (when tracing enabled):

```python
tracing.log_permission_check(tool_name, allowed=False, reason=denial_msg)
```

Trace output example:

```
[PERMISSION] Bash: DENIED
  Reason: Bash is restricted to 'pitlane' CLI commands only
  Command: cat /etc/passwd

[PERMISSION] Read: ALLOWED
  File: ~/.pitlane/workspaces/abc123/data/session_info.json

[PERMISSION] WebFetch: DENIED
  Domain: github.com
  Reason: Domain not in allowed list
```

## Implementation

See [`tool_permissions.py`](../../packages/pitlane-agent/src/pitlane_agent/tool_permissions.py) for the full implementation:

```python
async def can_use_tool(
    tool_name: str,
    input_params: dict[str, Any],
    context: ToolPermissionContext | dict[str, Any],
) -> PermissionResultAllow | PermissionResultDeny:
    """Validate tool usage with restrictions."""

    # Bash: pitlane CLI only
    if tool_name == "Bash":
        command = input_params.get("command", "")
        if not _is_allowed_bash_command(command):
            return PermissionResultDeny(message="...")
        return PermissionResultAllow()

    # Read: workspace only
    if tool_name == "Read":
        file_path = input_params.get("file_path", "")
        workspace_dir = context.get("workspace_dir")
        if not _is_within_workspace(file_path, workspace_dir):
            return PermissionResultDeny(message="...")
        return PermissionResultAllow()

    # Write: workspace only
    if tool_name == "Write":
        # Same as Read

    # WebFetch: F1 domains only
    if tool_name == "WebFetch":
        url = input_params.get("url", "")
        domain = urlparse(url).netloc
        if domain not in ALLOWED_WEBFETCH_DOMAINS:
            return PermissionResultDeny(message="...")
        return PermissionResultAllow()

    # Allow all other tools (Skill)
    return PermissionResultAllow()
```

## Benefits

### 1. Defense in Depth

Multiple layers of security:
- Tool allowlist (5 tools only)
- Per-tool restrictions (domain, path, command)
- Workspace isolation (session-scoped)

### 2. Auditable

All permission checks are:
- Logged with structured data
- Traced via OpenTelemetry
- Reviewable in logs

### 3. Predictable

Agent behavior is constrained to:
- F1 data operations only
- Session-scoped file access
- Known, safe domains

### 4. User-Friendly

Error messages are clear and actionable:
- Explain why permission was denied
- Suggest correct usage
- Don't expose internal details

## Related Documentation

- [Agent System](agent-system.md) - How permissions integrate with F1Agent
- [Skills](skills.md) - Skill-specific tool restrictions
- [Workspace Management](workspace-management.md) - Session isolation
- [Agent CLI: Tracing](../agent-cli/tracing.md) - Observing permission checks
