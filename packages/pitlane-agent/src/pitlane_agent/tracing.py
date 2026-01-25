"""OpenTelemetry tracing configuration for F1Agent tool calls.

This module provides simple console-based tracing to demonstrate what the agent
is doing during execution. Tracing is disabled by default and can be enabled via
environment variable or programmatically.

Thread Safety:
    This module uses module-level globals for tracer state and is designed for
    asyncio-based applications. It is async-safe (multiple coroutines can safely
    access the tracer concurrently) but NOT thread-safe. If you need to use this
    from multiple threads, you must add external synchronization.

    The lazy initialization in get_tracer() has a benign race condition: multiple
    concurrent calls may create multiple TracerProvider instances, but OpenTelemetry's
    global set_tracer_provider() handles this safely by using the last one set.
"""

import os
import sys
from contextlib import contextmanager
from typing import Any

from claude_agent_sdk.types import (
    HookContext,
    PostToolUseHookInput,
    PreToolUseHookInput,
    SyncHookJSONOutput,
)
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor

# Global tracer instance
_tracer = None
_tracing_enabled = None  # None means use env var, True/False overrides env var
_provider_initialized = False


def is_tracing_enabled() -> bool:
    """Check if tracing is enabled via environment variable or programmatically.

    Returns:
        True if tracing is enabled, False otherwise.
        Programmatic setting (_tracing_enabled) overrides environment variable.
    """
    if _tracing_enabled is not None:
        # Programmatic setting overrides environment variable
        return _tracing_enabled
    # Fall back to environment variable
    return os.getenv("PITLANE_TRACING_ENABLED", "0") == "1"


def _initialize_tracer_provider() -> None:
    """Initialize the OpenTelemetry tracer provider with console exporter.

    This is called automatically when tracing is enabled. It sets up a console
    exporter that outputs to stderr to avoid mixing with agent responses.

    The span processor can be configured via PITLANE_SPAN_PROCESSOR environment
    variable:
    - "simple" (default): Uses SimpleSpanProcessor for synchronous export.
      Required for tests to ensure spans are flushed before assertions.
    - "batch": Uses BatchSpanProcessor for better production performance.
      Spans are exported asynchronously in batches.
    """
    global _provider_initialized

    if _provider_initialized:
        return

    # Create resource with service name
    resource = Resource.create({"service.name": "pitlane-f1-agent"})

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Create console exporter (outputs to stderr)
    console_exporter = ConsoleSpanExporter(out=sys.stderr)

    # Create span processor based on configuration
    processor_type = os.getenv("PITLANE_SPAN_PROCESSOR", "simple").lower()
    if processor_type == "batch":
        span_processor = BatchSpanProcessor(console_exporter)
    else:
        # Default to SimpleSpanProcessor for test compatibility
        span_processor = SimpleSpanProcessor(console_exporter)

    provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    _provider_initialized = True


def get_tracer() -> trace.Tracer:
    """Get the OpenTelemetry tracer instance.

    Lazily initializes the tracer provider if tracing is enabled.

    Note:
        This function has a benign race condition when called concurrently
        from multiple coroutines during initial startup. Multiple TracerProvider
        instances may be created, but this is harmless as OpenTelemetry's global
        tracer provider is set atomically.

    Returns:
        Tracer instance (may be a no-op tracer if tracing is disabled).
    """
    global _tracer

    if not is_tracing_enabled():
        # Return no-op tracer if tracing is disabled
        return trace.get_tracer(__name__)

    if _tracer is None:
        _initialize_tracer_provider()
        _tracer = trace.get_tracer(__name__, "0.1.0")

    return _tracer


def enable_tracing() -> None:
    """Programmatically enable tracing.

    This overrides the PITLANE_TRACING_ENABLED environment variable.
    """
    global _tracing_enabled
    _tracing_enabled = True


def disable_tracing() -> None:
    """Programmatically disable tracing."""
    global _tracing_enabled
    _tracing_enabled = False


@contextmanager
def tool_span(tool_name: str, **attributes: Any):
    """Create a span for a tool call with minimal console output.

    This context manager creates a span with the tool name and optional
    attributes. The console exporter will output a simple log line like:
    [TOOL] ToolName: key_parameter

    Args:
        tool_name: Name of the tool being called (e.g., "Bash", "Skill", "WebFetch").
        **attributes: Span attributes to record (e.g., tool.key_param, tool.permission).

    Example:
        with tool_span("Bash", **{"tool.key_param": "ls -la"}):
            # Execute tool
            pass
    """
    tracer = get_tracer()

    if not is_tracing_enabled():
        # If tracing is disabled, just yield without creating a span
        yield None
        return

    with tracer.start_as_current_span(f"tool.{tool_name}") as span:
        # Set tool name attribute
        span.set_attribute("tool.name", tool_name)

        # Set additional attributes
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key, str(value))

        # Log minimal console output
        _log_tool_call(tool_name, attributes)

        yield span


def _log_tool_call(tool_name: str, attributes: dict[str, Any]) -> None:
    """Log a minimal tool call to stderr.

    Format: [TOOL] ToolName: key_parameter

    Args:
        tool_name: Name of the tool.
        attributes: Span attributes.
    """
    key_param = attributes.get("tool.key_param", "")
    permission = attributes.get("tool.permission", "")
    denial_reason = attributes.get("tool.denial_reason", "")

    # Build output message
    if permission == "denied":
        msg = f"[TOOL] {tool_name}: {key_param} → DENIED"
        if denial_reason:
            msg += f" ({denial_reason})"
    else:
        msg = f"[TOOL] {tool_name}: {key_param}"

    # Write to stderr
    print(msg, file=sys.stderr, flush=True)


def log_permission_check(tool_name: str, allowed: bool, reason: str = "") -> None:
    """Log a permission check result.

    This is called from the permission callback to show when tools are
    denied access.

    Args:
        tool_name: Name of the tool.
        allowed: Whether the tool was allowed.
        reason: Reason for denial (if denied).
    """
    if not is_tracing_enabled():
        return

    if not allowed:
        msg = f"[PERMISSION] {tool_name} → DENIED"
        if reason:
            msg += f": {reason}"
        print(msg, file=sys.stderr, flush=True)


# Hook callbacks for Claude Agent SDK


async def pre_tool_use_hook(
    hook_input: PreToolUseHookInput,
    block_reason: str | None,
    hook_context: HookContext,
) -> SyncHookJSONOutput:
    """Hook called before a tool is executed.

    Logs the tool call to console if tracing is enabled.

    Args:
        hook_input: Input data including tool_name and tool_input.
        block_reason: Reason if the tool was blocked (unused).
        hook_context: Hook context (unused).

    Returns:
        SyncHookJSONOutput to continue execution.
    """
    if not is_tracing_enabled():
        return SyncHookJSONOutput(continue_=True)

    tool_name = hook_input["tool_name"]
    tool_input = hook_input["tool_input"]

    # Extract key parameter based on tool type
    key_param = _extract_key_param(tool_name, tool_input)

    # Log the tool call
    _log_tool_call(tool_name, {"tool.key_param": key_param})

    return SyncHookJSONOutput(continue_=True)


async def post_tool_use_hook(
    hook_input: PostToolUseHookInput,
    block_reason: str | None,
    hook_context: HookContext,
) -> SyncHookJSONOutput:
    """Hook called after a tool is executed.

    Currently just continues execution. Could be extended to log results.

    Args:
        hook_input: Input data including tool_name, tool_input, and tool_response.
        block_reason: Reason if the tool was blocked (unused).
        hook_context: Hook context (unused).

    Returns:
        SyncHookJSONOutput to continue execution.
    """
    # For minimal output, we don't log post-tool results
    # This hook is here for potential future enhancements
    return SyncHookJSONOutput(continue_=True)


def _extract_key_param(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Extract the most relevant parameter from tool input for logging.

    Args:
        tool_name: Name of the tool.
        tool_input: Tool input parameters.

    Returns:
        A string representing the key parameter for this tool.
    """
    if tool_name == "Bash":
        return tool_input.get("command", "")
    elif tool_name == "Skill":
        return tool_input.get("skill", "")
    elif tool_name == "WebFetch":
        return tool_input.get("url", "")
    elif tool_name == "Read" or tool_name == "Write" or tool_name == "Edit":
        return tool_input.get("file_path", "")
    else:
        # For unknown tools, try to get a reasonable representation
        if tool_input:
            # Get first non-empty value
            for value in tool_input.values():
                if value:
                    return str(value)[:100]
        return ""
