"""Tests for pulse threshold configuration."""

import pytest


class TestPulseThresholdSettings:
    """Test PulseThresholdSettings configuration class."""

    def test_default_values(self):
        """Settings should have sensible defaults matching original constants."""
        from community_pulse.config import get_pulse_settings

        settings = get_pulse_settings()

        assert settings.significant_rank_diff == 2
        assert settings.high_velocity_threshold == 1.5
        assert settings.high_centrality_threshold == 0.3
        assert settings.diverse_authors_threshold == 5
        assert settings.min_cluster_size == 3

    def test_environment_variable_override(self, monkeypatch):
        """Settings should be overridable via environment variables."""
        from community_pulse.config import PulseThresholdSettings

        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", "5")
        monkeypatch.setenv("PULSE_HIGH_VELOCITY_THRESHOLD", "2.5")
        monkeypatch.setenv("PULSE_HIGH_CENTRALITY_THRESHOLD", "0.5")
        monkeypatch.setenv("PULSE_DIVERSE_AUTHORS_THRESHOLD", "10")
        monkeypatch.setenv("PULSE_MIN_CLUSTER_SIZE", "5")

        # Create new instance to pick up env vars
        settings = PulseThresholdSettings()

        assert settings.significant_rank_diff == 5
        assert settings.high_velocity_threshold == 2.5
        assert settings.high_centrality_threshold == 0.5
        assert settings.diverse_authors_threshold == 10
        assert settings.min_cluster_size == 5

    def test_partial_override(self, monkeypatch):
        """Can override some settings while keeping others at defaults."""
        from community_pulse.config import PulseThresholdSettings

        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", "10")

        settings = PulseThresholdSettings()

        assert settings.significant_rank_diff == 10
        assert settings.high_velocity_threshold == 1.5  # default

    def test_type_validation(self, monkeypatch):
        """Invalid types should raise validation errors."""
        from pydantic import ValidationError

        from community_pulse.config import PulseThresholdSettings

        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", "not_a_number")

        with pytest.raises(ValidationError):
            PulseThresholdSettings()

    def test_singleton_pattern(self):
        """get_pulse_settings should return cached singleton."""
        from community_pulse.config import get_pulse_settings

        settings1 = get_pulse_settings()
        settings2 = get_pulse_settings()

        assert settings1 is settings2
