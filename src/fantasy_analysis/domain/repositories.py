"""Data-access interfaces (ports) implemented by the infrastructure layer."""

from collections.abc import Callable
from typing import Protocol

from fantasy_analysis.domain.models import League, NFLTeam, NFLTeamStats, PlayerStats

# Looks up the NFLTeam for an abbreviation in ESPN's form (e.g. League.nfl_team), so stats
# reference the league's own NFLTeam objects.
NFLTeamLookup = Callable[[str], NFLTeam]


class LeagueRepository(Protocol):
    def get_league(self, season: int) -> League:
        """Load a league season with its teams, completed matchups and weekly lineups."""
        ...


class PlayerStatsRepository(Protocol):
    def get_weekly_stats(
        self, season: int, nfl_team: NFLTeamLookup
    ) -> dict[int, dict[int, PlayerStats]]:
        """Regular-season weekly stats, keyed by player ID (the domain's ESPN ID), then week."""
        ...


class NFLTeamStatsRepository(Protocol):
    def get_weekly_team_stats(
        self, season: int, nfl_team: NFLTeamLookup
    ) -> dict[str, dict[int, NFLTeamStats]]:
        """Regular-season weekly team stats, keyed by abbreviation (ESPN's form), then week."""
        ...
