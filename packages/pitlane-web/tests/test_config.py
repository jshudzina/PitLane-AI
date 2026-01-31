"""Tests for configuration module."""

from pitlane_web import config


class TestSessionConfig:
    """Tests for session configuration constants."""

    def test_session_cookie_name(self):
        """Test session cookie name is set correctly."""
        assert config.SESSION_COOKIE_NAME == "pitlane_session"

    def test_session_max_age_default(self, monkeypatch):
        """Test default session max age is 7 days."""
        monkeypatch.delenv("PITLANE_SESSION_MAX_AGE", raising=False)
        # Re-import to get fresh value
        import importlib

        importlib.reload(config)
        assert config.SESSION_MAX_AGE == 86400 * 7  # 7 days in seconds

    def test_session_max_age_from_env(self, monkeypatch):
        """Test session max age can be set via environment variable."""
        monkeypatch.setenv("PITLANE_SESSION_MAX_AGE", "3600")
        import importlib

        importlib.reload(config)
        assert config.SESSION_MAX_AGE == 3600

    def test_session_cookie_secure_default(self, monkeypatch):
        """Test session cookie secure flag defaults to True in production."""
        monkeypatch.delenv("PITLANE_HTTPS_ENABLED", raising=False)
        monkeypatch.delenv("PITLANE_ENV", raising=False)
        import importlib

        importlib.reload(config)
        # Default environment is production, so secure should be True
        assert config.SESSION_COOKIE_SECURE is True

    def test_session_cookie_secure_development(self, monkeypatch):
        """Test session cookie secure flag is False in development."""
        monkeypatch.setenv("PITLANE_ENV", "development")
        monkeypatch.delenv("PITLANE_HTTPS_ENABLED", raising=False)
        import importlib

        importlib.reload(config)
        assert config.SESSION_COOKIE_SECURE is False

    def test_session_cookie_secure_https_enabled(self, monkeypatch):
        """Test session cookie secure flag enabled when HTTPS is on."""
        monkeypatch.setenv("PITLANE_HTTPS_ENABLED", "true")
        import importlib

        importlib.reload(config)
        assert config.SESSION_COOKIE_SECURE is True

    def test_session_cookie_secure_https_disabled(self, monkeypatch):
        """Test session cookie secure flag disabled when HTTPS is explicitly off."""
        monkeypatch.setenv("PITLANE_HTTPS_ENABLED", "false")
        import importlib

        importlib.reload(config)
        assert config.SESSION_COOKIE_SECURE is False

    def test_session_cookie_httponly(self):
        """Test session cookie httponly is always True."""
        assert config.SESSION_COOKIE_HTTPONLY is True

    def test_session_cookie_samesite(self):
        """Test session cookie samesite is set to lax."""
        assert config.SESSION_COOKIE_SAMESITE == "lax"


class TestAgentCacheConfig:
    """Tests for agent cache configuration."""

    def test_agent_cache_max_size(self):
        """Test agent cache max size is set correctly."""
        assert config.AGENT_CACHE_MAX_SIZE == 100
