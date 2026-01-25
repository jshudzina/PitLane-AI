"""Tests for the tracing module."""

from io import StringIO
from unittest.mock import patch

from pitlane_agent import tracing


class TestTracingConfiguration:
    """Tests for tracing configuration and initialization."""

    def test_tracing_disabled_by_default(self, monkeypatch):
        """Tracing should be disabled by default."""
        # Clear any environment variable
        monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)
        # Reset global state
        tracing._tracing_enabled = None

        assert not tracing.is_tracing_enabled()

    def test_tracing_enabled_via_env_var(self, monkeypatch):
        """Tracing can be enabled via environment variable."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None  # Reset global state

        assert tracing.is_tracing_enabled()

    def test_tracing_disabled_via_env_var(self, monkeypatch):
        """Tracing remains disabled when env var is 0."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "0")
        tracing._tracing_enabled = None

        assert not tracing.is_tracing_enabled()

    def test_programmatic_enable_tracing(self, monkeypatch):
        """Tracing can be enabled programmatically."""
        monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)

        tracing.enable_tracing()
        assert tracing.is_tracing_enabled()

        # Cleanup
        tracing.disable_tracing()

    def test_programmatic_disable_tracing(self, monkeypatch):
        """Tracing can be disabled programmatically."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")

        tracing.disable_tracing()
        # Programmatic setting overrides env var
        assert not tracing.is_tracing_enabled()

    def test_programmatic_overrides_env_var(self, monkeypatch):
        """Programmatic enable/disable overrides environment variable."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "0")

        tracing.enable_tracing()
        assert tracing.is_tracing_enabled()

        tracing.disable_tracing()
        assert not tracing.is_tracing_enabled()


class TestTracerInitialization:
    """Tests for tracer provider initialization."""

    def test_get_tracer_when_disabled(self, monkeypatch):
        """get_tracer returns a no-op tracer when tracing is disabled."""
        monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)
        tracing._tracing_enabled = None
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer = tracing.get_tracer()

        # Should return a tracer but provider should not be initialized
        assert tracer is not None
        assert not tracing._provider_initialized

    def test_get_tracer_when_enabled(self, monkeypatch):
        """get_tracer initializes provider when tracing is enabled."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer = tracing.get_tracer()

        # Should initialize provider and return tracer
        assert tracer is not None
        assert tracing._provider_initialized

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False

    def test_tracer_singleton(self, monkeypatch):
        """get_tracer returns the same tracer instance."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer1 = tracing.get_tracer()
        tracer2 = tracing.get_tracer()

        assert tracer1 is tracer2

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False


class TestToolSpan:
    """Tests for tool_span context manager."""

    def test_tool_span_when_disabled(self, monkeypatch):
        """tool_span should not create spans when tracing is disabled."""
        monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)
        tracing._tracing_enabled = None

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with tracing.tool_span("Bash", **{"tool.key_param": "ls -la"}) as span:
                assert span is None

            # No output should be written
            assert mock_stderr.getvalue() == ""

    def test_tool_span_when_enabled(self, monkeypatch):
        """tool_span should create spans and log when tracing is enabled."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None
        tracing._tracer = None
        tracing._provider_initialized = False

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            with tracing.tool_span("Bash", **{"tool.key_param": "ls -la"}) as span:
                assert span is not None

            # Should have logged to stderr
            output = mock_stderr.getvalue()
            assert "[TOOL]" in output
            assert "Bash" in output
            assert "ls -la" in output

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False

    def test_tool_span_attributes(self, monkeypatch):
        """tool_span should set span attributes."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None
        tracing._tracer = None
        tracing._provider_initialized = False

        with (
            patch("sys.stderr", new=StringIO()),
            tracing.tool_span(
                "WebFetch",
                **{
                    "tool.key_param": "https://example.com",
                    "tool.permission": "allowed",
                },
            ) as span,
        ):
            # Span should be created
            assert span is not None

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False


class TestLogToolCall:
    """Tests for _log_tool_call function."""

    def test_log_tool_call_basic(self):
        """_log_tool_call should output tool name and key param."""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing._log_tool_call("Bash", {"tool.key_param": "python script.py"})

            output = mock_stderr.getvalue()
            assert "[TOOL]" in output
            assert "Bash" in output
            assert "python script.py" in output

    def test_log_tool_call_denied(self):
        """_log_tool_call should show DENIED for denied permissions."""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing._log_tool_call(
                "WebFetch",
                {
                    "tool.key_param": "https://blocked.com",
                    "tool.permission": "denied",
                    "tool.denial_reason": "Domain not allowed",
                },
            )

            output = mock_stderr.getvalue()
            assert "[TOOL]" in output
            assert "WebFetch" in output
            assert "DENIED" in output
            assert "Domain not allowed" in output

    def test_log_tool_call_empty_params(self):
        """_log_tool_call should handle empty parameters."""
        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing._log_tool_call("Skill", {})

            output = mock_stderr.getvalue()
            assert "[TOOL]" in output
            assert "Skill" in output


class TestLogPermissionCheck:
    """Tests for log_permission_check function."""

    def test_log_permission_check_when_disabled(self, monkeypatch):
        """log_permission_check should not output when tracing is disabled."""
        monkeypatch.delenv("PITLANE_TRACING_ENABLED", raising=False)
        tracing._tracing_enabled = None

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing.log_permission_check("WebFetch", False, "Domain blocked")

            # No output when disabled
            assert mock_stderr.getvalue() == ""

    def test_log_permission_check_denied(self, monkeypatch):
        """log_permission_check should log denied permissions."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing.log_permission_check("WebFetch", False, "Domain not in allowed list")

            output = mock_stderr.getvalue()
            assert "[PERMISSION]" in output
            assert "WebFetch" in output
            assert "DENIED" in output
            assert "Domain not in allowed list" in output

    def test_log_permission_check_allowed(self, monkeypatch):
        """log_permission_check should not log when allowed."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        tracing._tracing_enabled = None

        with patch("sys.stderr", new=StringIO()) as mock_stderr:
            tracing.log_permission_check("Bash", True)

            # No output for allowed permissions
            assert mock_stderr.getvalue() == ""


class TestSpanProcessorConfiguration:
    """Tests for span processor configuration."""

    def test_default_processor_is_simple(self, monkeypatch):
        """Default span processor should be SimpleSpanProcessor."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        monkeypatch.delenv("PITLANE_SPAN_PROCESSOR", raising=False)
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer = tracing.get_tracer()

        assert tracer is not None
        assert tracing._provider_initialized

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False

    def test_batch_processor_can_be_configured(self, monkeypatch):
        """Span processor can be set to batch via env var."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        monkeypatch.setenv("PITLANE_SPAN_PROCESSOR", "batch")
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer = tracing.get_tracer()

        assert tracer is not None
        assert tracing._provider_initialized

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False

    def test_invalid_processor_defaults_to_simple(self, monkeypatch):
        """Invalid processor type should default to simple."""
        monkeypatch.setenv("PITLANE_TRACING_ENABLED", "1")
        monkeypatch.setenv("PITLANE_SPAN_PROCESSOR", "invalid")
        tracing._tracer = None
        tracing._provider_initialized = False

        tracer = tracing.get_tracer()

        assert tracer is not None
        assert tracing._provider_initialized

        # Cleanup
        tracing._tracer = None
        tracing._provider_initialized = False
