"""nflverse adapter (wraps the nflreadpy library) for NFL player and team stats."""

from fantasy_analysis.infrastructure.nflverse.repository import (
    NflversePlayerStatsRepository,
    NflverseTeamStatsRepository,
)

__all__ = ["NflversePlayerStatsRepository", "NflverseTeamStatsRepository"]
