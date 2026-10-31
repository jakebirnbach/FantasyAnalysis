"""Attach NFL player and team stats to a league."""

from fantasy_analysis.domain.models import League
from fantasy_analysis.domain.repositories import NFLTeamStatsRepository, PlayerStatsRepository


def attach_player_stats(league: League, repo: PlayerStatsRepository) -> None:
    """Fill in `player.stats` for every player in the league's lineups, for that season.

    Each player's Player objects share one stats dict, so this updates every lineup entry.
    """
    stats = repo.get_weekly_stats(league.season, league.nfl_team)
    for player_id, player in league.players().items():
        player.stats.update(stats.get(player_id, {}))


def attach_team_stats(league: League, repo: NFLTeamStatsRepository) -> None:
    """Fill in `NFLTeam.stats` for every NFL team that season (adding teams the league's
    lineups never referenced). A D/ST's stats are then `player.pro_team.stats[week]`."""
    stats = repo.get_weekly_team_stats(league.season, league.nfl_team)
    for abbreviation, weekly in stats.items():
        league.nfl_team(abbreviation).stats.update(weekly)
