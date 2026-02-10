"""FastAPI application for PitLane AI with session management."""

import logging
import os
from pathlib import Path

from fastapi import Cookie, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pitlane_agent.commands.workspace import (
    create_conversation,
    get_active_conversation,
    get_workspace_path,
    load_conversations,
    set_active_conversation,
    update_conversation,
    workspace_exists,
)
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .agent_manager import _agent_cache
from .config import (
    RATE_LIMIT_CHART,
    RATE_LIMIT_CHAT,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_SESSION_CREATE,
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

# Allow log level override via environment variable
_log_level = os.getenv("PITLANE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)

# ============================================================================
# Application Setup
# ============================================================================

app = FastAPI(title="PitLane AI", description="F1 data analysis powered by AI")

# Rate limiting setup
limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED,
    storage_uri="memory://",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)

# Register Jinja2 filters
register_filters(templates)

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ============================================================================
# Routes
# ============================================================================


@app.get("/", response_class=HTMLResponse)
@limiter.limit(RATE_LIMIT_SESSION_CREATE)
async def index(
    request: Request,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Render the home page with session management."""
    # Note: session_id in this context refers to the workspace identifier (stored in browser cookie),
    # which is distinct from the agent_session_id (Claude SDK session for conversation resumption)

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
@limiter.limit(RATE_LIMIT_CHAT)
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
        # Check for active conversation to resume
        active_conv = get_active_conversation(session_id)
        resume_session_id = active_conv["agent_session_id"] if active_conv else None

        if resume_session_id:
            logger.info(f"Resuming conversation: {active_conv['id']}")
            logger.debug(f"Session IDs - Web: {session_id}, Agent (for resume): {resume_session_id}")

        # Get or create agent for this session
        agent = await _agent_cache.get_or_create(session_id)

        # Process question with optional resumption
        response_text = await agent.chat_full(question, resume_session_id=resume_session_id)

        if not response_text.strip():
            response_text = "I wasn't able to process your question. Please try again."

        # Create or update conversation after successful response
        if agent.agent_session_id:
            if active_conv:
                # Update existing conversation
                update_conversation(session_id, active_conv["id"])
                logger.debug(f"Updated conversation: {active_conv['id']}")
            else:
                # Create new conversation with captured SDK session ID
                new_conv = create_conversation(session_id, agent.agent_session_id, question)
                logger.info(f"Created new conversation: {new_conv['id']}")

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
@limiter.limit(RATE_LIMIT_CHART)
async def serve_chart(
    request: Request,
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
    logger.debug(f"Chart serving - URL session: {session_id}, Cookie session: {current_session}")

    # 1. Validate session ID format
    if not is_valid_session_id(session_id):
        logger.warning(f"Invalid session ID format: {session_id}")
        raise HTTPException(status_code=400, detail="Invalid session ID")

    # 2. Verify session ownership (case-insensitive comparison for UUID)
    if session_id.lower() != (current_session or "").lower():
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

    # 6. Validate file type (only images)
    allowed_extensions = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
    if chart_path.suffix.lower() not in allowed_extensions:
        logger.warning(f"Invalid file type requested: {chart_path.suffix}")
        raise HTTPException(status_code=400, detail="Invalid file type")

    # 7. Check file exists
    if not chart_path.exists():
        logger.warning(f"Chart file not found: {chart_path}")
        raise HTTPException(status_code=404, detail="Chart not found")

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


# ============================================================================
# Conversation Management Routes
# ============================================================================


@app.get("/api/conversations", response_class=HTMLResponse)
@limiter.limit(RATE_LIMIT_CHART)
async def list_conversations(
    request: Request,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """List all conversations for the current session."""
    is_valid, validated_session = validate_session_safely(session)
    if not is_valid or not validated_session:
        raise HTTPException(status_code=401, detail="Invalid session")

    conversations_data = load_conversations(validated_session)

    return templates.TemplateResponse(
        request,
        "partials/conversation_list.html",
        {
            "conversations": conversations_data["conversations"],
            "active_id": conversations_data.get("active_conversation_id"),
        },
    )


@app.post("/api/conversations/new", response_class=HTMLResponse)
@limiter.limit(RATE_LIMIT_SESSION_CREATE)
async def new_conversation(
    request: Request,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Start a new conversation (clears active, doesn't delete history)."""
    is_valid, validated_session = validate_session_safely(session)
    if not is_valid or not validated_session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Clear active conversation
    set_active_conversation(validated_session, None)

    # Evict cached agent to force fresh SDK context
    await _agent_cache.evict(validated_session)

    logger.info(f"Started new conversation for session: {validated_session}")

    return templates.TemplateResponse(
        request,
        "partials/conversation_status.html",
        {"status": "new", "message": "Ready for new conversation"},
    )


@app.post("/api/conversations/{conversation_id}/resume", response_class=HTMLResponse)
@limiter.limit(RATE_LIMIT_CHAT)
async def resume_conversation(
    request: Request,
    conversation_id: str,
    session: str | None = Cookie(None, alias=SESSION_COOKIE_NAME),
):
    """Resume a specific conversation."""
    is_valid, validated_session = validate_session_safely(session)
    if not is_valid or not validated_session:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Validate conversation belongs to this session
    conversations_data = load_conversations(validated_session)
    conversation = None
    for conv in conversations_data["conversations"]:
        if conv["id"] == conversation_id:
            conversation = conv
            break

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Set as active conversation
    set_active_conversation(validated_session, conversation_id)

    # Evict cached agent to force new context with resume
    await _agent_cache.evict(validated_session)

    logger.info(f"Resumed conversation {conversation_id} for session: {validated_session}")

    return templates.TemplateResponse(
        request,
        "partials/conversation_status.html",
        {"status": "resumed", "conversation": conversation},
    )
