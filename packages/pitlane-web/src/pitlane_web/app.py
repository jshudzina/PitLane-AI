"""FastAPI application for PitLane AI with session management."""

import logging
from pathlib import Path

from fastapi import Cookie, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from pitlane_agent.scripts.workspace import get_workspace_path, workspace_exists

from .agent_manager import _agent_cache
from .config import (
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SESSION_MAX_AGE,
)
from .filters import register_filters
from .security import is_safe_filename, is_valid_session_id
from .session import (
    generate_session_id,
    update_workspace_metadata_safe,
    validate_session_safely,
)

# ============================================================================
# Logging Configuration
# ============================================================================

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

# Register Jinja2 filters
register_filters(templates)

# ============================================================================
# Routes
# ============================================================================


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Render the home page with session management."""
    # Validate existing session (with timing attack protection)
    is_valid, validated_session = validate_session_safely(session)

    if is_valid and validated_session:
        session_id = validated_session
        needs_new_session = False
        logger.info(f"Index page loaded with existing session: {session_id}")
        # Update last accessed time with proper error handling
        update_workspace_metadata_safe(session_id)
    else:
        # Create new session
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
    # Validate existing session (with timing attack protection)
    is_valid, validated_session = validate_session_safely(session)

    if is_valid and validated_session:
        session_id = validated_session
        needs_new_session = False
        logger.info(f"Using existing session: {session_id}")
        # Update last accessed time with proper error handling
        update_workspace_metadata_safe(session_id)
    else:
        # Create new session
        session_id = generate_session_id()
        needs_new_session = True
        logger.info(f"Creating new session: {session_id}")

    try:
        # Get or create agent for this session
        agent = _agent_cache.get_or_create(session_id)

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

    # 4. Validate filename using whitelist pattern (prevent path traversal)
    if not is_safe_filename(filename):
        logger.warning(f"Invalid or unsafe filename detected: {filename}")
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
