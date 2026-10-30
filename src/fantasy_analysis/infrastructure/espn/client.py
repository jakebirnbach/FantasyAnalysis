"""Connection to ESPN's fantasy API via the espn-api library."""

from espn_api.football import League as EspnLeague

# ESPN only serves box scores (weekly lineups) for 2019 onward.
MIN_SEASON = 2019


def connect(
    league_id: int, season: int, espn_s2: str | None = None, swid: str | None = None
) -> EspnLeague:
    if season < MIN_SEASON:
        raise ValueError(f"ESPN weekly data is only available from {MIN_SEASON}, got {season}")
    return EspnLeague(league_id=league_id, year=season, espn_s2=espn_s2, swid=swid)


def last_completed_week(league: EspnLeague) -> int:
    """The last scoring period whose games are final (0 if none are).

    Mid-season, ESPN's scoringPeriodId is the in-progress week. Once the season is over it
    runs past finalScoringPeriod.
    """
    if league.scoringPeriodId > league.finalScoringPeriod:
        return league.finalScoringPeriod
    return league.scoringPeriodId - 1
