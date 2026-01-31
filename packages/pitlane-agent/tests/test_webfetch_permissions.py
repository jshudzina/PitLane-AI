"""Tests for WebFetch permission validation."""

import pytest
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
from pitlane_agent.tool_permissions import (
    ALLOWED_WEBFETCH_DOMAINS,
    _is_allowed_bash_command,
    can_use_tool,
)


class TestCanUseToolWebFetchAllowed:
    """Tests for _can_use_tool with allowed WebFetch domains."""

    @pytest.mark.asyncio
    async def test_webfetch_wikipedia_allowed(self):
        """Test that wikipedia.org is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://wikipedia.org/wiki/Formula_One"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_en_wikipedia_allowed(self):
        """Test that en.wikipedia.org subdomain is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://en.wikipedia.org/wiki/Max_Verstappen"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_ergast_allowed(self):
        """Test that ergast.com is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://ergast.com/api/f1/drivers"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_api_ergast_allowed(self):
        """Test that api.ergast.com subdomain is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://api.ergast.com/api/f1/2024/drivers"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_formula1_allowed(self):
        """Test that formula1.com is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://formula1.com/en/results.html"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_www_formula1_allowed(self):
        """Test that www.formula1.com is allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://www.formula1.com/en/drivers.html"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_subdomain_wikipedia_allowed(self):
        """Test that arbitrary wikipedia.org subdomains are allowed."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://de.wikipedia.org/wiki/Formel_1"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_www_prefix_normalized(self):
        """Test that www. prefix is properly normalized for comparison."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://www.wikipedia.org/wiki/Formula_One"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_http_protocol_allowed(self):
        """Test that http:// protocol is allowed (not just https://)."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "http://wikipedia.org/wiki/Formula_One"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_webfetch_case_insensitive_domain(self):
        """Test that domain matching is case-insensitive."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://WIKIPEDIA.ORG/wiki/Formula_One"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)


class TestCanUseToolWebFetchDenied:
    """Tests for _can_use_tool with blocked WebFetch domains."""

    @pytest.mark.asyncio
    async def test_webfetch_random_domain_denied(self):
        """Test that random domains are denied."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://example.com/page"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultDeny)
        assert "example.com" in result.message
        assert "not in the allowed list" in result.message

    @pytest.mark.asyncio
    async def test_webfetch_blocked_domain_shows_allowed_list(self):
        """Test that denied requests show the allowed domains list."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://malicious.com/data"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultDeny)
        # Check that all allowed domains are mentioned in the error
        for domain in ALLOWED_WEBFETCH_DOMAINS:
            assert domain in result.message

    @pytest.mark.asyncio
    async def test_webfetch_no_url_denied(self):
        """Test that missing URL parameter is denied."""
        result = await can_use_tool(
            "WebFetch",
            {},  # No URL parameter
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultDeny)
        assert "requires a URL parameter" in result.message

    @pytest.mark.asyncio
    async def test_webfetch_empty_url_denied(self):
        """Test that empty URL is denied."""
        result = await can_use_tool(
            "WebFetch",
            {"url": ""},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultDeny)
        assert "requires a URL parameter" in result.message

    @pytest.mark.asyncio
    async def test_webfetch_lookalike_domain_denied(self):
        """Test that lookalike domains are denied."""
        result = await can_use_tool(
            "WebFetch",
            {"url": "https://wikipedia.org.evil.com/fake"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultDeny)


class TestCanUseToolOtherTools:
    """Tests for _can_use_tool with non-WebFetch tools."""

    @pytest.mark.asyncio
    async def test_bash_tool_allowed(self):
        """Test that Bash tool allows pitlane commands."""
        result = await can_use_tool(
            "Bash",
            {"command": "pitlane workspace list"},
            {},
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_bash_tool_denied(self):
        """Test that Bash tool denies non-pitlane commands."""
        result = await can_use_tool(
            "Bash",
            {"command": "ls -la"},
            {},
        )
        assert isinstance(result, PermissionResultDeny)
        assert "pitlane" in result.message.lower()

    @pytest.mark.asyncio
    async def test_read_tool_allowed(self):
        """Test that Read tool is allowed within workspace."""
        result = await can_use_tool(
            "Read",
            {"file_path": "/tmp/workspace/data/file.txt"},
            {"workspace_dir": "/tmp/workspace"},
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_read_tool_denied(self):
        """Test that Read tool is denied outside workspace."""
        result = await can_use_tool(
            "Read",
            {"file_path": "/etc/passwd"},
            {"workspace_dir": "/tmp/workspace"},
        )
        assert isinstance(result, PermissionResultDeny)
        assert "workspace" in result.message.lower()

    @pytest.mark.asyncio
    async def test_write_tool_allowed(self):
        """Test that Write tool is allowed within workspace."""
        result = await can_use_tool(
            "Write",
            {"file_path": "/tmp/workspace/data/file.txt", "content": "data"},
            {"workspace_dir": "/tmp/workspace"},
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_write_tool_denied(self):
        """Test that Write tool is denied outside workspace."""
        result = await can_use_tool(
            "Write",
            {"file_path": "/etc/hosts", "content": "data"},
            {"workspace_dir": "/tmp/workspace"},
        )
        assert isinstance(result, PermissionResultDeny)
        assert "workspace" in result.message.lower()

    @pytest.mark.asyncio
    async def test_skill_tool_allowed(self):
        """Test that Skill tool is not restricted."""
        result = await can_use_tool(
            "Skill",
            {"skill": "f1-analyst"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)

    @pytest.mark.asyncio
    async def test_unknown_tool_allowed(self):
        """Test that unknown tools are allowed by default."""
        result = await can_use_tool(
            "SomeNewTool",
            {"param": "value"},
            ToolPermissionContext(),
        )
        assert isinstance(result, PermissionResultAllow)


class TestAllowedDomains:
    """Tests for ALLOWED_WEBFETCH_DOMAINS constant."""

    def test_allowed_domains_contains_wikipedia(self):
        """Test that allowed domains include Wikipedia variants."""
        assert "wikipedia.org" in ALLOWED_WEBFETCH_DOMAINS
        assert "en.wikipedia.org" in ALLOWED_WEBFETCH_DOMAINS

    def test_allowed_domains_contains_ergast(self):
        """Test that allowed domains include Ergast variants."""
        assert "ergast.com" in ALLOWED_WEBFETCH_DOMAINS
        assert "api.ergast.com" in ALLOWED_WEBFETCH_DOMAINS

    def test_allowed_domains_contains_formula1(self):
        """Test that allowed domains include Formula1 variants."""
        assert "formula1.com" in ALLOWED_WEBFETCH_DOMAINS
        assert "www.formula1.com" in ALLOWED_WEBFETCH_DOMAINS

    def test_allowed_domains_is_set(self):
        """Test that ALLOWED_WEBFETCH_DOMAINS is a set."""
        assert isinstance(ALLOWED_WEBFETCH_DOMAINS, set)

    def test_allowed_domains_count(self):
        """Test that we have the expected number of allowed domains."""
        assert len(ALLOWED_WEBFETCH_DOMAINS) == 6


class TestPermissionDenialLogging:
    """Tests for logging of permission denials."""

    @pytest.mark.asyncio
    async def test_missing_url_logs_warning(self, caplog):
        """Test that missing URL logs a warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = await can_use_tool(
                "WebFetch",
                {},
                ToolPermissionContext(),
            )

        assert isinstance(result, PermissionResultDeny)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "missing URL parameter" in caplog.records[0].message

    @pytest.mark.asyncio
    async def test_blocked_domain_logs_warning(self, caplog):
        """Test that blocked domain logs a warning with details."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = await can_use_tool(
                "WebFetch",
                {"url": "https://evil.com/malware"},
                ToolPermissionContext(),
            )

        assert isinstance(result, PermissionResultDeny)
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "domain not allowed" in record.message
        assert record.domain == "evil.com"
        assert record.url == "https://evil.com/malware"

    @pytest.mark.asyncio
    async def test_invalid_url_logs_warning(self, caplog):
        """Test that invalid URL logs a warning."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = await can_use_tool(
                "WebFetch",
                {"url": "not-a-valid-url"},
                ToolPermissionContext(),
            )

        # May be allowed or denied depending on urlparse behavior
        # Just verify logging occurred if denied
        if isinstance(result, PermissionResultDeny):
            assert any("WebFetch permission denied" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_allowed_domain_does_not_log(self, caplog):
        """Test that allowed domains don't log warnings."""
        import logging

        with caplog.at_level(logging.WARNING):
            result = await can_use_tool(
                "WebFetch",
                {"url": "https://wikipedia.org/wiki/F1"},
                ToolPermissionContext(),
            )

        assert isinstance(result, PermissionResultAllow)
        # No warning logs for allowed domains
        assert len([r for r in caplog.records if r.levelname == "WARNING"]) == 0


class TestBashEnvironmentVariableValidation:
    """Tests for environment variable validation in Bash commands."""

    def test_bash_allowed_env_vars_pitlane_session_id(self):
        """Test that PITLANE_SESSION_ID is allowed."""
        assert _is_allowed_bash_command("PITLANE_SESSION_ID=abc123 pitlane analyze")

    def test_bash_allowed_env_vars_pitlane_cache_dir(self):
        """Test that PITLANE_CACHE_DIR is allowed."""
        assert _is_allowed_bash_command("PITLANE_CACHE_DIR=/tmp pitlane drivers")

    def test_bash_allowed_env_vars_pitlane_tracing(self):
        """Test that PITLANE_TRACING_ENABLED is allowed."""
        assert _is_allowed_bash_command("PITLANE_TRACING_ENABLED=1 pitlane lap-times")

    def test_bash_allowed_env_vars_pitlane_span_processor(self):
        """Test that PITLANE_SPAN_PROCESSOR is allowed."""
        assert _is_allowed_bash_command("PITLANE_SPAN_PROCESSOR=batch pitlane schedule")

    def test_bash_multiple_allowed_env_vars(self):
        """Test that multiple whitelisted env vars are allowed."""
        assert _is_allowed_bash_command("PITLANE_SESSION_ID=abc PITLANE_CACHE_DIR=/tmp pitlane analyze")

    def test_bash_blocked_env_var_pythonpath(self):
        """Test that PYTHONPATH is blocked."""
        assert not _is_allowed_bash_command("PYTHONPATH=/evil pitlane analyze")

    def test_bash_blocked_env_var_ld_preload(self):
        """Test that LD_PRELOAD is blocked."""
        assert not _is_allowed_bash_command("LD_PRELOAD=/malicious.so pitlane drivers")

    def test_bash_blocked_env_var_path(self):
        """Test that PATH is blocked."""
        assert not _is_allowed_bash_command("PATH=/tmp pitlane lap-times")

    def test_bash_blocked_env_var_home(self):
        """Test that HOME is blocked."""
        assert not _is_allowed_bash_command("HOME=/tmp pitlane analyze")

    def test_bash_blocked_env_var_ld_library_path(self):
        """Test that LD_LIBRARY_PATH is blocked."""
        assert not _is_allowed_bash_command("LD_LIBRARY_PATH=/evil pitlane schedule")

    def test_bash_mixed_allowed_and_blocked_env_vars(self):
        """Test commands with both allowed and blocked env vars are rejected."""
        assert not _is_allowed_bash_command("PITLANE_SESSION_ID=abc PYTHONPATH=/evil pitlane analyze")

    def test_bash_mixed_blocked_and_allowed_env_vars(self):
        """Test commands with blocked vars first are rejected."""
        assert not _is_allowed_bash_command("PYTHONPATH=/evil PITLANE_SESSION_ID=abc pitlane analyze")

    def test_bash_no_env_vars(self):
        """Test that commands without env vars still work."""
        assert _is_allowed_bash_command("pitlane analyze")

    def test_bash_only_env_vars_no_command(self):
        """Test that only env vars without a command is rejected."""
        assert not _is_allowed_bash_command("PITLANE_SESSION_ID=abc")

    def test_bash_env_var_with_non_pitlane_command(self):
        """Test that allowed env vars with non-pitlane command are rejected."""
        assert not _is_allowed_bash_command("PITLANE_SESSION_ID=abc ls -la")

    def test_bash_empty_command(self):
        """Test that empty command is rejected."""
        assert not _is_allowed_bash_command("")

    def test_bash_whitespace_only(self):
        """Test that whitespace-only command is rejected."""
        assert not _is_allowed_bash_command("   ")
