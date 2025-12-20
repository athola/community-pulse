"""Configuration module for Community Pulse.

Uses Pydantic Settings for environment-variable-based configuration
with sensible defaults. This allows runtime configuration without
code changes, following 12-factor app principles.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class PulseThresholdSettings(BaseSettings):
    """Threshold configuration for pulse scoring algorithms.

    These thresholds control how topics are classified and compared
    in the pulse ranking system. All values can be overridden via
    environment variables with the PULSE_ prefix.

    Environment Variables:
        PULSE_SIGNIFICANT_RANK_DIFF: Minimum rank difference to flag as significant
        PULSE_HIGH_VELOCITY_THRESHOLD: Velocity multiplier for "high momentum"
        PULSE_HIGH_CENTRALITY_THRESHOLD: Network centrality threshold (0-1)
        PULSE_DIVERSE_AUTHORS_THRESHOLD: Minimum unique authors for diversity
        PULSE_MIN_CLUSTER_SIZE: Minimum topics required to form a cluster
    """

    model_config = SettingsConfigDict(
        env_prefix="PULSE_",
        case_sensitive=False,
    )

    significant_rank_diff: int = 2
    high_velocity_threshold: float = 1.5
    high_centrality_threshold: float = 0.3
    diverse_authors_threshold: int = 5
    min_cluster_size: int = 3


@lru_cache
def get_pulse_settings() -> PulseThresholdSettings:
    """Get cached pulse threshold settings.

    Uses lru_cache to ensure the same settings instance is returned
    throughout the application lifecycle, avoiding repeated environment
    variable reads.

    Returns:
        Cached PulseThresholdSettings instance.

    """
    return PulseThresholdSettings()
