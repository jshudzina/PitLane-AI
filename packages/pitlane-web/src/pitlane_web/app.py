"""FastAPI application for PitLane AI with session management."""

import contextlib
import logging
import re
import uuid
from pathlib import Path

import markdown
from fastapi import Cookie, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pitlane_agent import F1Agent
from pitlane_agent.scripts.workspace import (
    generate_session_id,
    get_workspace_path,
    update_workspace_metadata,
    workspace_exists,
)

# ============================================================================
# Logging Configuration
# ============================================================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(title="PitLane AI", description="F1 data analysis powered by AI")

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)

# ============================================================================
# Session Configuration
# ============================================================================

SESSION_COOKIE_NAME = "pitlane_session"
SESSION_MAX_AGE = 86400 * 7  # 7 days
SESSION_COOKIE_SECURE = False  # Set True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "lax"

# Agent cache: maps session_id -> F1Agent instance
_agent_cache: dict[str, F1Agent] = {}
_CACHE_MAX_SIZE = 100  # Maximum concurrent sessions

# ============================================================================
# Helper Functions
# ============================================================================


def is_valid_session_id(session_id: str) -> bool:
    """Validate that session_id is a valid UUID."""
    try:
        uuid.UUID(session_id)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def get_or_create_agent(session_id: str) -> F1Agent:
    """Get cached agent or create new one for session.

    Implements LRU-style eviction when cache is full.
    """
    if session_id in _agent_cache:
        logger.debug(f"Using cached agent for session: {session_id}")
        return _agent_cache[session_id]

    # Evict oldest entry if cache is full
    if len(_agent_cache) >= _CACHE_MAX_SIZE:
        # Remove first item (oldest in insertion order)
        oldest_session = next(iter(_agent_cache))
        logger.info(f"Agent cache full ({_CACHE_MAX_SIZE}), evicting oldest session: {oldest_session}")
        del _agent_cache[oldest_session]

    # Create new agent
    logger.info(f"Creating new agent for session: {session_id}")
    agent = F1Agent(session_id=session_id)
    _agent_cache[session_id] = agent
    logger.debug(f"Agent cache size: {len(_agent_cache)}/{_CACHE_MAX_SIZE}")
    return agent


def rewrite_workspace_paths(text: str, session_id: str) -> str:
    """Rewrite absolute workspace paths to web-relative URLs.

    Transforms:
      /Users/.../.pitlane/workspaces/{session-id}/charts/lap_times.png
      → /charts/{session-id}/lap_times.png

    Args:
        text: Response text containing absolute paths
        session_id: Current session ID

    Returns:
        Text with rewritten paths
    """
    workspace_base = str(Path.home() / ".pitlane" / "workspaces")
    escaped_base = re.escape(workspace_base)

    # Pattern: /path/to/workspaces/{uuid}/{charts|data}/{filename}
    pattern = rf"{escaped_base}/([a-f0-9\-]+)/(charts|data)/([^\s\)]+)"

    def replacer(match):
        matched_session = match.group(1)
        subdir = match.group(2)
        filename = match.group(3)

        # Only rewrite current session's paths (security)
        if matched_session == session_id:
            return f"/{subdir}/{matched_session}/{filename}"
        return match.group(0)

    return re.sub(pattern, replacer, text)


def md_to_html(text: str) -> str:
    """Convert markdown to HTML."""
    return markdown.markdown(text, extensions=["fenced_code", "tables"])


# ============================================================================
# Jinja2 Filters
# ============================================================================

templates.env.filters["markdown"] = md_to_html
templates.env.filters["rewrite_paths"] = rewrite_workspace_paths

# ============================================================================
# Routes
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Render the home page with session management."""
    # Check if we need to create a new session
    needs_new_session = False
    if session and is_valid_session_id(session) and workspace_exists(session):
        session_id = session
        logger.info(f"Index page loaded with existing session: {session_id}")
        # Update last accessed time
        with contextlib.suppress(Exception):
            update_workspace_metadata(session_id)
    else:
        session_id = generate_session_id()
        needs_new_session = True
        logger.info(f"Index page loaded, creating new session: {session_id}")

    # Create the template response
    template_response = templates.TemplateResponse(request, "index.html", {"session_id": session_id})

    # Set cookie if needed
    if needs_new_session:
        logger.info(f"Setting session cookie for index page: {session_id}")
        template_response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=SESSION_MAX_AGE,
            secure=SESSION_COOKIE_SECURE,
            httponly=SESSION_COOKIE_HTTPONLY,
            samesite=SESSION_COOKIE_SAMESITE,
        )

    return template_response


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/chat", response_class=HTMLResponse)
async def chat(
    request: Request,
    question: str = Form(...),
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Process a user question and return an HTML response.

    Uses F1Agent with Claude Agent SDK to analyze F1 data.
    """
    # Check if we need to create a new session
    needs_new_session = False
    if session and is_valid_session_id(session) and workspace_exists(session):
        session_id = session
        logger.info(f"Using existing session: {session_id}")
        # Update last accessed time
        with contextlib.suppress(Exception):
            update_workspace_metadata(session_id)
    else:
        session_id = generate_session_id()
        needs_new_session = True
        logger.info(f"Creating new session: {session_id}")

    try:
        # Get or create agent for this session
        agent = get_or_create_agent(session_id)

        # Process question
        response_text = await agent.chat_full(question)

        if not response_text.strip():
            response_text = "I wasn't able to process your question. Please try again."

    except Exception as e:
        logger.error(f"Error processing chat: {e}", exc_info=True)
        response_text = f"An error occurred: {e}"

    # Create the template response
    template_response = templates.TemplateResponse(
        request,
        "partials/message.html",
        {"content": response_text, "question": question, "session_id": session_id},
    )

    # Set cookie if needed
    if needs_new_session:
        logger.info(f"Setting session cookie: {session_id}")
        template_response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            max_age=SESSION_MAX_AGE,
            secure=SESSION_COOKIE_SECURE,
            httponly=SESSION_COOKIE_HTTPONLY,
            samesite=SESSION_COOKIE_SAMESITE,
        )

    return template_response


@app.get("/charts/{session_id}/{filename}")
async def serve_chart(
    session_id: str,
    filename: str,
    current_session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Serve chart files from session workspace with security validation.

    Security checks:
    1. Validate session ID format (UUID)
    2. Verify session ownership (matches cookie)
    3. Ensure workspace exists
    4. Validate filename (no path traversal)
    5. Check file exists within workspace
    6. Validate file extension
    """
    logger.info(f"Chart request: {filename} for session {session_id}")

    # 1. Validate session ID format
    if not is_valid_session_id(session_id):
        logger.warning(f"Invalid session ID format: {session_id}")
        raise HTTPException(status_code=400, detail="Invalid session ID")

    # 2. Verify session ownership
    if session_id != current_session:
        logger.warning(f"Session ownership mismatch - URL: {session_id}, Cookie: {current_session}")
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only access your own session's charts",
        )

    # 3. Verify workspace exists
    if not workspace_exists(session_id):
        logger.warning(f"Workspace not found for session: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    # 4. Validate filename (prevent path traversal)
    if ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(f"Path traversal attempt detected: {filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")

    # 5. Construct and validate file path
    workspace_path = get_workspace_path(session_id)
    chart_path = workspace_path / "charts" / filename

    # Resolve symlinks and verify within workspace
    try:
        resolved_chart = chart_path.resolve()
        resolved_workspace = workspace_path.resolve()

        if not str(resolved_chart).startswith(str(resolved_workspace)):
            logger.warning(f"Path outside workspace detected: {resolved_chart}")
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving chart path: {e}")
        raise HTTPException(status_code=404, detail="File not found") from None

    # 6. Check file exists and is a file
    if not chart_path.exists() or not chart_path.is_file():
        logger.warning(f"Chart not found: {chart_path}")
        raise HTTPException(status_code=404, detail="Chart not found")

    # 7. Validate file type (only images)
    allowed_extensions = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    if chart_path.suffix.lower() not in allowed_extensions:
        logger.warning(f"Invalid file type requested: {chart_path.suffix}")
        raise HTTPException(status_code=400, detail="Invalid file type")

    # 8. Determine media type
    media_type_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(chart_path.suffix.lower(), "image/png")

    # 9. Serve file
    logger.info(f"Serving chart: {filename} ({media_type}) for session {session_id}")
    return FileResponse(
        path=chart_path,
        media_type=media_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Session-ID": session_id,
        },
    )
