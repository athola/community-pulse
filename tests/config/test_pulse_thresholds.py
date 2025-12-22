"""Tests for pulse threshold configuration."""

import pytest
from pydantic import ValidationError

from community_pulse.config import (
    PulseThresholdSettings,
    clear_pulse_settings_cache,
    get_pulse_settings,
)


class TestPulseThresholdSettings:
    """Test PulseThresholdSettings configuration class."""

    def test_default_values(self):
        """Settings should have sensible defaults matching original constants."""
        # Clear cache to ensure fresh settings
        clear_pulse_settings_cache()
        settings = get_pulse_settings()

        assert settings.significant_rank_diff == 2
        assert settings.high_velocity_threshold == 1.5
        assert settings.high_centrality_threshold == 0.3
        assert settings.diverse_authors_threshold == 5
        assert settings.min_cluster_size == 3

    def test_environment_variable_override(self, monkeypatch):
        """Settings should be overridable via environment variables."""
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
        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", "10")

        settings = PulseThresholdSettings()

        assert settings.significant_rank_diff == 10
        assert settings.high_velocity_threshold == 1.5  # default

    def test_type_validation(self, monkeypatch):
        """Invalid types should raise validation errors."""
        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", "not_a_number")

        with pytest.raises(ValidationError):
            PulseThresholdSettings()

    def test_singleton_pattern(self):
        """get_pulse_settings should return cached singleton."""
        # Clear cache to ensure fresh test state
        clear_pulse_settings_cache()

        settings1 = get_pulse_settings()
        settings2 = get_pulse_settings()

        assert settings1 is settings2

    def test_value_validation_min_cluster_size(self, monkeypatch):
        """min_cluster_size must be >= 1 to prevent division by zero."""
        monkeypatch.setenv("PULSE_MIN_CLUSTER_SIZE", "0")

        with pytest.raises(ValidationError) as exc_info:
            PulseThresholdSettings()

        assert "min_cluster_size" in str(exc_info.value)

    def test_value_validation_centrality_bounds(self, monkeypatch):
        """high_centrality_threshold must be between 0 and 1."""
        monkeypatch.setenv("PULSE_HIGH_CENTRALITY_THRESHOLD", "1.5")

        with pytest.raises(ValidationError) as exc_info:
            PulseThresholdSettings()

        assert "high_centrality_threshold" in str(exc_info.value)

    def test_cache_clear_function(self, monkeypatch):
        """clear_pulse_settings_cache enables config reload."""
        # Get initial settings
        clear_pulse_settings_cache()
        initial = get_pulse_settings()
        initial_diff = initial.significant_rank_diff

        # Change env var and clear cache
        monkeypatch.setenv("PULSE_SIGNIFICANT_RANK_DIFF", str(initial_diff + 10))
        clear_pulse_settings_cache()

        # Should pick up new value
        updated = get_pulse_settings()
        assert updated.significant_rank_diff == initial_diff + 10
