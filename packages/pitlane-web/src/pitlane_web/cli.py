"""CLI entry point for PitLane Web application.

Usage:
    uvx pitlane-web
    uvx pitlane-web --port 3000
    uvx pitlane-web --host 0.0.0.0 --no-reload
    uvx pitlane-web --env development
"""

import os
import sys

import click
import uvicorn


def get_default_reload() -> bool:
    """Determine if reload should be enabled based on environment.

    Returns:
        True if PITLANE_ENV is 'development', False otherwise
    """
    env = os.getenv("PITLANE_ENV", "production")
    return env == "development"


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    show_default=True,
    help="Host to bind to",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    show_default=True,
    help="Port to bind to",
)
@click.option(
    "--reload/--no-reload",
    default=None,
    help="Enable auto-reload (default: enabled in development, disabled in production)",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "trace"],
        case_sensitive=False,
    ),
    show_default=True,
    help="Log level",
)
@click.option(
    "--env",
    type=click.Choice(["development", "production", "test"], case_sensitive=False),
    help="Set PITLANE_ENV (affects cookie security and other settings)",
)
@click.version_option(package_name="pitlane-web")
def main(
    host: str,
    port: int,
    reload: bool | None,
    log_level: str,
    env: str | None,
) -> None:
    """Run the PitLane Web application.

    This starts a FastAPI web server for F1 data analysis powered by AI.

    Environment Variables:
        PITLANE_ENV                 - Environment mode (development/production/test)
        PITLANE_TRACING_ENABLED     - Enable OpenTelemetry tracing (0/1)
        PITLANE_HTTPS_ENABLED       - Enable secure cookies (true/false)
        PITLANE_SESSION_MAX_AGE     - Session cookie max age in seconds
        PITLANE_RATE_LIMIT_ENABLED  - Enable rate limiting (true/false)

    Examples:
        # Start with defaults (development mode auto-reload)
        uvx pitlane-web

        # Custom port
        uvx pitlane-web --port 3000

        # Production mode on all interfaces
        uvx pitlane-web --host 0.0.0.0 --env production --no-reload

        # Development with tracing
        PITLANE_TRACING_ENABLED=1 uvx pitlane-web --env development
    """
    # Set PITLANE_ENV if provided via CLI
    if env:
        os.environ["PITLANE_ENV"] = env
        click.echo(f"Setting PITLANE_ENV={env}")

    # Determine reload setting
    if reload is None:
        reload = get_default_reload()
        env_name = os.getenv("PITLANE_ENV", "production")
        click.echo(f"Auto-reload: {reload} (detected from PITLANE_ENV={env_name})")

    # Display startup info
    click.echo(f"Starting PitLane Web on http://{host}:{port}")
    if reload:
        click.echo("Auto-reload enabled - changes will trigger server restart")

    # Check for tracing
    tracing_enabled = os.getenv("PITLANE_TRACING_ENABLED", "0") == "1"
    if tracing_enabled:
        click.echo("OpenTelemetry tracing enabled")

    # Run uvicorn
    try:
        uvicorn.run(
            "pitlane_web.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.lower(),
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
