"""Data-access interfaces (ports) implemented by the infrastructure layer."""

from typing import Protocol

from fantasy_analysis.domain.models import League


class LeagueRepository(Protocol):
    def get_league(self, season: int) -> League:
        """Load a league season with its teams, completed matchups and weekly lineups."""
        ...
