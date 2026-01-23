"""FastAPI application for PitLane AI."""

from pathlib import Path

import markdown
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pitlane_agent import F1Agent

app = FastAPI(title="PitLane AI", description="F1 data analysis powered by AI")

# Templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)


def md_to_html(text: str) -> str:
    """Convert markdown to HTML."""
    return markdown.markdown(text, extensions=["fenced_code", "tables"])


# Register markdown filter for Jinja2
templates.env.filters["markdown"] = md_to_html

# Initialize F1 agent
agent = F1Agent()

# Mount static files for serving charts
app.mount("/charts", StaticFiles(directory=str(agent.charts_dir)), name="charts")


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

    Uses F1Agent with Claude Agent SDK to analyze F1 data.
    """
    try:
        response_text = await agent.chat_full(question)

        if not response_text.strip():
            response_text = "I wasn't able to process your question. Please try again."

    except Exception as e:
        response_text = f"An error occurred: {e}"

    return templates.TemplateResponse(
        request,
        "partials/message.html",
        {"content": response_text, "question": question},
    )
