"""Unit tests for filename utilities."""

from pitlane_agent.utils.filename import sanitize_filename


class TestSanitizeFilename:
    """Unit tests for sanitize_filename function."""

    def test_basic_lowercase(self):
        assert sanitize_filename("Monaco") == "monaco"
        assert sanitize_filename("MONACO") == "monaco"

    def test_spaces_to_underscores(self):
        assert sanitize_filename("Abu Dhabi") == "abu_dhabi"
        assert sanitize_filename("Las Vegas") == "las_vegas"

    def test_hyphens_to_underscores(self):
        assert sanitize_filename("Emilia-Romagna") == "emilia_romagna"

    def test_strip_unicode_diacritics(self):
        assert sanitize_filename("São Paulo") == "sao_paulo"
        assert sanitize_filename("México") == "mexico"
        assert sanitize_filename("Montréal") == "montreal"

    def test_multiple_special_characters(self):
        assert sanitize_filename("Test--Multiple__Chars") == "test_multiple_chars"
        assert sanitize_filename("Multiple   Spaces") == "multiple_spaces"

    def test_leading_trailing_underscores_stripped(self):
        assert sanitize_filename("_leading") == "leading"
        assert sanitize_filename("trailing_") == "trailing"

    def test_mixed_unicode_and_special_chars(self):
        assert sanitize_filename("São Paulo (Brazil)") == "sao_paulo_brazil"

    def test_preserves_numbers(self):
        assert sanitize_filename("Circuit 123") == "circuit_123"
        assert sanitize_filename("2024 Season") == "2024_season"

    def test_empty_string(self):
        assert sanitize_filename("") == ""

    def test_only_special_characters(self):
        assert sanitize_filename("---") == ""
