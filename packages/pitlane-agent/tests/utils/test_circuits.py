"""Tests for circuits utility module."""

from pitlane_agent.utils.circuits import CIRCUIT_LENGTHS_KM, lookup_circuit_length_km


class TestLookupCircuitLengthKm:
    """Tests for lookup_circuit_length_km."""

    def test_exact_match_returns_correct_km(self):
        """Known circuit returns the correct length."""
        assert lookup_circuit_length_km("monte carlo") == 3.337

    def test_case_insensitive_match(self):
        """Lookup is case-insensitive."""
        assert lookup_circuit_length_km("MONTE CARLO") == 3.337
        assert lookup_circuit_length_km("Monte Carlo") == 3.337

    def test_whitespace_stripped(self):
        """Leading and trailing whitespace is ignored."""
        assert lookup_circuit_length_km("  monte carlo  ") == 3.337

    def test_unknown_location_returns_none(self):
        """Unknown circuit name returns None."""
        assert lookup_circuit_length_km("Atlantis Grand Prix Circuit") is None

    def test_empty_string_returns_none(self):
        """Empty string returns None."""
        assert lookup_circuit_length_km("") is None

    def test_fastf1_alias_bahrain(self):
        """FastF1 uses 'Bahrain' but Wikipedia lists it as 'Sakhir' — both resolve."""
        assert lookup_circuit_length_km("Bahrain") == 5.412
        assert lookup_circuit_length_km("Sakhir") == 5.412

    def test_fastf1_alias_las_vegas(self):
        """FastF1 uses 'Las Vegas'; Wikipedia location is 'Paradise'."""
        assert lookup_circuit_length_km("Las Vegas") == 6.201

    def test_fastf1_alias_miami(self):
        """FastF1 uses 'Miami'; Wikipedia location is 'Miami Gardens'."""
        assert lookup_circuit_length_km("Miami") == 5.412

    def test_fastf1_alias_spa(self):
        """FastF1 uses 'Spa'; Wikipedia location is 'Stavelot'."""
        assert lookup_circuit_length_km("Spa") == 7.004
        assert lookup_circuit_length_km("Spa-Francorchamps") == 7.004

    def test_fastf1_alias_barcelona(self):
        """FastF1 uses 'Barcelona' for Circuit de Catalunya (4.657 km, not the 1951 Pedralbes layout)."""
        assert lookup_circuit_length_km("Barcelona") == 4.657

    def test_partial_substring_match_unambiguous(self):
        """Unambiguous partial match resolves correctly."""
        # "silverstone" is the only entry containing "silver"
        assert lookup_circuit_length_km("silver") == 5.891

    def test_all_values_positive(self):
        """Sanity check: every entry in the table is a positive float."""
        for location, km in CIRCUIT_LENGTHS_KM.items():
            assert km > 0, f"Non-positive length for {location!r}: {km}"

    def test_all_keys_lowercase(self):
        """All dict keys should be lowercase (normalisation invariant)."""
        for key in CIRCUIT_LENGTHS_KM:
            assert key == key.lower(), f"Key not lowercase: {key!r}"
