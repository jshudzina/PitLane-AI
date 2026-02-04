# Web Interface

The PitLane-AI web interface provides an interactive chat experience for F1 data analysis, powered by FastAPI and Server-Sent Events (SSE) for real-time streaming responses.

## Quick Start

### Development Mode

```bash
# Using uvx (recommended)
uvx pitlane-web --env development

# With tracing enabled
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development

# Custom port
uvx pitlane-web --port 3000 --env development
```

Visit [http://localhost:8000](http://localhost:8000)

!!! info "Production Deployment"
    Production deployment instructions are currently being finalized and will be available in a future release.

## Features

### 1. Real-Time Streaming

Responses stream in real-time using **Server-Sent Events (SSE)**:

```
User: "Compare Verstappen and Hamilton lap times in Monaco 2024"
↓
Agent: [Streams response chunks as they're generated]
       "I'll analyze the lap times for Verstappen..."
       "Let me fetch the session data..."
       "Here's the comparison: ..."
```

**Benefits:**
- Immediate feedback (no waiting for full response)
- Transparent agent reasoning
- Better user experience for long-running analyses

### 2. Session Management

Each browser session gets a unique **session ID** stored in a secure cookie:

```
Session Cookie:
- Name: pitlane_session
- HttpOnly: true (XSS protection)
- SameSite: Lax (CSRF protection)
- Max-Age: 7 days
```

**Session Flow:**
1. User visits homepage
2. Server generates UUID session ID
3. Cookie set in response
4. All subsequent requests include session cookie
5. Agent uses session ID for workspace isolation

**Benefits:**
- Data isolation between users
- Persistent chat history per session
- Concurrent multi-user support

### 3. Chart Visualization

Generated charts are automatically displayed in the chat:

```
Agent: "I've generated a lap time distribution chart"
↓
[Chart image displayed inline]
```

**Chart Flow:**
1. Skill generates matplotlib chart → workspace/charts/lap_times.png
2. Agent references chart in response
3. Frontend detects chart path
4. Fetches chart via `/charts/<session_id>/<filename>`
5. Displays inline in chat

**Security:**
- Session ID validated before serving charts
- Filename sanitized (no directory traversal)
- Only PNG files served
- MIME type validation

### 4. Rate Limiting

The web interface includes rate limiting for API endpoints:

| Endpoint | Limit |
|----------|-------|
| `/` (homepage) | 30/minute |
| `/chat` (messages) | 60/minute |
| `/charts/*` (images) | 120/minute |

**Configuration:**
```python
# In pitlane_web/config.py
RATE_LIMIT_SESSION_CREATE = "30/minute"
RATE_LIMIT_CHAT = "60/minute"
RATE_LIMIT_CHART = "120/minute"
RATE_LIMIT_ENABLED = True  # Disable for development
```

## User Interface

### Chat Interface

**Layout:**
```
┌─────────────────────────────────────────┐
│ PitLane AI - F1 Data Analysis           │ <- Header
├─────────────────────────────────────────┤
│                                         │
│ User: Compare VER and HAM lap times    │
│                                         │
│ Assistant: I'll analyze the lap times   │
│ for Verstappen and Hamilton...          │
│                                         │
│ [Chart: lap_times.png]                  │
│                                         │
│ The analysis shows...                   │
│                                         │
├─────────────────────────────────────────┤
│ [Type your message here...]     [Send] │ <- Input
└─────────────────────────────────────────┘
```

**Features:**
- Auto-scroll to latest message
- Markdown rendering (code blocks, lists, emphasis)
- Inline chart display
- Loading indicators during agent execution

### Message Types

**User Messages:**
```html
<div class="message user-message">
  <strong>You:</strong> Compare Verstappen lap times
</div>
```

**Assistant Messages:**
```html
<div class="message assistant-message">
  <strong>Assistant:</strong> I'll analyze the lap times...
  <img src="/charts/abc123/lap_times.png" alt="Chart">
</div>
```

**System Messages:**
```html
<div class="message system-message">
  Error: Failed to fetch session data
</div>
```

## API Endpoints

### `GET /`

Render the chat homepage.

**Response:**
- HTML page with session ID
- Sets session cookie (if new session)

**Session Logic:**
1. Check for existing session cookie
2. Validate session ID (timing-safe comparison)
3. Create new session if invalid/missing
4. Update `last_accessed` timestamp
5. Render template with session ID

### `POST /chat`

Send a chat message (Server-Sent Events).

**Request:**
```
POST /chat
Content-Type: application/x-www-form-urlencoded
Cookie: pitlane_session=abc123

message=Compare+VER+and+HAM+lap+times
```

**Response:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"type": "start"}

data: {"type": "chunk", "content": "I'll analyze"}

data: {"type": "chunk", "content": " the lap times"}

data: {"type": "done"}
```

**SSE Event Types:**
- `start` - Agent execution started
- `chunk` - Text chunk from agent response
- `done` - Agent execution completed
- `error` - Error occurred

### `GET /charts/<session_id>/<filename>`

Serve generated chart images.

**Request:**
```
GET /charts/abc123/lap_times.png
Cookie: pitlane_session=abc123
```

**Security Checks:**
1. Extract session ID from cookie
2. Validate session ID format (UUID)
3. Compare cookie session with URL session (timing-safe)
4. Validate filename (alphanumeric + underscores/dashes only)
5. Check file exists in workspace charts directory
6. Validate PNG extension

**Response:**
```
Content-Type: image/png
Cache-Control: max-age=3600

[PNG binary data]
```

**Error Responses:**
- `401 Unauthorized` - Session mismatch
- `404 Not Found` - Chart doesn't exist
- `400 Bad Request` - Invalid filename

## Configuration

### Environment Variables

```bash
# Enable tracing (OpenTelemetry)
PITLANE_TRACING_ENABLED=1

# Tracing processor type
PITLANE_SPAN_PROCESSOR=simple  # or 'batch' for production

# Session cookie settings (production)
SESSION_COOKIE_SECURE=true     # HTTPS only
SESSION_COOKIE_HTTPONLY=true   # XSS protection
SESSION_COOKIE_SAMESITE=Lax    # CSRF protection

# Rate limiting
RATE_LIMIT_ENABLED=true        # Disable for local development
```

### CLI Options

```bash
uvx pitlane-web --help

Options:
  --port INTEGER           Port to run on (default: 8000)
  --env [development|production]   Environment mode (default: production)
  --help                   Show this message and exit
```

**Development vs. Production:**

| Feature | Development | Production |
|---------|-------------|------------|
| Auto-reload | ✓ Enabled | ✗ Disabled |
| Rate limiting | ✗ Disabled | ✓ Enabled |
| Debug logs | ✓ Verbose | ✗ Info only |
| Cookie secure | ✗ False | ✓ True (HTTPS) |

## Agent Manager

The web interface uses an **agent manager** for lifecycle management:

```python
from pitlane_web.agent_manager import get_or_create_agent

# Get cached agent or create new one
agent = await get_or_create_agent(session_id, enable_tracing=True)

# Stream response
async for chunk in agent.chat(message):
    yield chunk
```

**Agent Caching:**
- Agents cached in memory (TTL: 30 minutes)
- Shared across requests for same session
- Automatic eviction on idle
- Thread-safe (asyncio locks)

**Benefits:**
- Faster response times (no re-initialization)
- Maintains conversation context
- Efficient resource usage

## Security Features

### 1. Session Validation

**Timing-Safe Comparison:**
```python
# Prevents timing attacks
secrets.compare_digest(cookie_session, url_session)
```

**UUID Validation:**
```python
# Prevents path traversal
uuid.UUID(session_id)  # Raises ValueError if invalid
```

### 2. Filename Sanitization

**Allowed Pattern:**
```python
# Only alphanumeric, underscores, dashes
r'^[a-zA-Z0-9_-]+\.png$'
```

**Prevents:**
- Directory traversal (`../../../etc/passwd`)
- Command injection (`chart.png; rm -rf /`)
- Extension spoofing (`chart.png.exe`)

### 3. CORS and Headers

**Security Headers:**
```python
Cache-Control: no-cache  # Disable caching for SSE
X-Content-Type-Options: nosniff  # Prevent MIME sniffing
```

**No CORS:**
- No `Access-Control-Allow-Origin` (same-origin only)
- Prevents cross-site chat hijacking

### 4. Rate Limiting

**Per-IP limits** prevent abuse:
- 30 session creations per minute
- 60 chat messages per minute
- 120 chart requests per minute

## Deployment

!!! note "Coming Soon"
    Production deployment instructions (Docker, Kubernetes, cloud platforms) are currently being finalized and will be available in a future release.

    For now, use development mode for local testing:
    ```bash
    uvx pitlane-web --env development
    ```

## Troubleshooting

### Chart Not Displaying

**Check:**
1. Session ID matches between cookie and URL
2. Chart file exists in workspace
3. Browser console for 401/404 errors

**Debug:**
```bash
# Check workspace charts
ls ~/.pitlane/workspaces/<session-id>/charts/

# Check session cookie
# Browser DevTools → Application → Cookies
```

### Streaming Not Working

**Check:**
1. Browser supports SSE (EventSource API)
2. No proxy buffering (see Nginx config above)
3. Network tab shows `text/event-stream` content type

**Debug:**
```javascript
// Browser console
const eventSource = new EventSource('/chat');
eventSource.onmessage = (e) => console.log(e.data);
```

### Agent Timeouts

**Check:**
1. FastF1 cache populated (first request slow)
2. Network connectivity to Ergast API
3. Rate limit not exceeded

**Debug:**
```bash
# Enable tracing
PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development
# Check stderr for tool calls and permission checks
```

## Related Documentation

- [Analysis Types](analysis-types.md) - Available analysis workflows
- [Architecture: Agent System](../architecture/agent-system.md) - Agent internals
- [Architecture: Workspace Management](../architecture/workspace-management.md) - Session isolation
- [Agent CLI Reference](../agent-cli/cli-reference.md) - CLI reference (for agents/developers)
