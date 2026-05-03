"""CLI entry point for pitlane-studio."""

import os
import sys

import click
import uvicorn


def get_default_reload() -> bool:
    """Determine if reload should be enabled based on environment."""
    env = os.getenv("PITLANE_ENV", "production")
    return env == "development"


@click.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
@click.option("--port", default=8001, type=int, show_default=True, help="Port to bind to")
@click.option(
    "--reload/--no-reload",
    default=None,
    help="Enable auto-reload (default: enabled in development)",
)
@click.option(
    "--log-level",
    default="info",
    type=click.Choice(
        ["critical", "error", "warning", "info", "debug", "trace"],
        case_sensitive=False,
    ),
    show_default=True,
)
@click.version_option(package_name="pitlane-studio")
def main(host: str, port: int, reload: bool | None, log_level: str) -> None:
    """Run the PitLane Studio co-authoring server."""
    if reload is None:
        reload = get_default_reload()
    try:
        uvicorn.run(
            "pitlane_studio.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level=log_level.lower(),
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        click.echo(f"Error starting server: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
