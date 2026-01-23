"""FastAPI application for PitLane AI."""

from pathlib import Path

import markdown
from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, TextBlock
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="PitLane AI", description="F1 data analysis powered by AI")

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)


def md_to_html(text: str) -> str:
    """Convert markdown to HTML."""
    return markdown.markdown(text, extensions=["fenced_code", "tables"])


# Register markdown filter for Jinja2
templates.env.filters["markdown"] = md_to_html

# Project root for Skills discovery
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Charts output directory
CHARTS_DIR = Path("/tmp/pitlane_charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files for serving charts
app.mount("/charts", StaticFiles(directory=str(CHARTS_DIR)), name="charts")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/api/chat", response_class=HTMLResponse)
async def chat(request: Request, question: str = Form(...)):
    """Process a user question and return an HTML response.

    Uses Claude Agent SDK with Skills to analyze F1 data.
    """
    # Configure the agent
    options = ClaudeAgentOptions(
        cwd=str(PROJECT_ROOT),
        setting_sources=["project"],  # Load Skills from .claude/skills/
        allowed_tools=["Skill", "Bash", "Read", "Write"],
    )

    # Collect the response text from AssistantMessage TextBlocks
    response_parts = []

    try:
        async for message in query(prompt=question, options=options):
            # Only process AssistantMessage objects
            if isinstance(message, AssistantMessage):
                # Extract text from TextBlock objects in content list
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_parts.append(block.text)

        response_text = "\n".join(response_parts)

        # If no response collected, provide a fallback
        if not response_text.strip():
            response_text = "I wasn't able to process your question. Please try again."

    except Exception as e:
        response_text = f"An error occurred: {e}"

    return templates.TemplateResponse(
        request,
        "partials/message.html",
        {"content": response_text, "question": question},
    )
