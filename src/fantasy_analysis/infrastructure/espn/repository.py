"""LeagueRepository backed by ESPN."""

from fantasy_analysis.config import Settings
from fantasy_analysis.domain.models import League, Matchup, Team
from fantasy_analysis.infrastructure.espn import mappers
from fantasy_analysis.infrastructure.espn.client import connect, last_completed_week


class EspnLeagueRepository:
    def __init__(self, league_id: int, espn_s2: str | None = None, swid: str | None = None):
        self.league_id = league_id
        self.espn_s2 = espn_s2
        self.swid = swid

    @classmethod
    def from_settings(cls, settings: Settings) -> "EspnLeagueRepository":
        if settings.espn_league_id is None:
            raise ValueError("ESPN_LEAGUE_ID is not set")
        return cls(settings.espn_league_id, settings.espn_s2, settings.espn_swid)

    def get_league(self, season: int) -> League:
        """Load a season with every completed week's matchups and lineups.

        Makes several requests per week, so a full season takes a little while.
        """
        espn = connect(self.league_id, season, self.espn_s2, self.swid)
        teams = {t.team_id: mappers.to_team(t) for t in espn.teams}

        matchups: list[Matchup] = []
        player_team_cache: dict = {}  # shared across weeks so bye-week players keep their team
        for week in range(1, last_completed_week(espn) + 1):
            for box in espn.box_scores(week=week, player_team_cache=player_team_cache):
                if box.home_team is None:  # ESPN puts a bye team on the home side
                    continue
                home = teams[box.home_team.team_id]
                home.lineups[week] = mappers.to_lineup(box.home_lineup)

                away: Team | None = None
                if box.away_team is not None:
                    away = teams[box.away_team.team_id]
                    away.lineups[week] = mappers.to_lineup(box.away_lineup)

                matchups.append(
                    Matchup(
                        week=week,
                        home=home,
                        away=away,
                        home_score=box.home_score,
                        away_score=box.away_score if away else None,
                        kind=mappers.to_matchup_kind(box.matchup_type),
                    )
                )

        return League(
            league_id=self.league_id,
            name=espn.settings.name,
            season=season,
            teams=list(teams.values()),
            matchups=matchups,
        )
