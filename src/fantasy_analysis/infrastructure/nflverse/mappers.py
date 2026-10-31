"""Pure functions converting nflverse rows into domain models."""

from typing import Any

from fantasy_analysis.domain.models import NFLTeamStats, PlayerStats
from fantasy_analysis.domain.repositories import NFLTeamLookup

# nflverse abbreviations that differ from ESPN's (the domain's form). All others are the same.
NFLVERSE_TO_ESPN = {"LA": "LAR", "WAS": "WSH"}
# Every NFL team in the domain's form
ESPN_ABBREVIATIONS = frozenset(
    {
        "ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET",
        "GB", "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE",
        "NO", "NYG", "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WSH",
    }
)  # fmt: skip


def to_espn_abbreviation(nflverse_abbreviation: str) -> str:
    abbreviation = NFLVERSE_TO_ESPN.get(nflverse_abbreviation, nflverse_abbreviation)
    if abbreviation not in ESPN_ABBREVIATIONS:
        raise ValueError(f"unsupported nflverse team abbreviation: {nflverse_abbreviation!r}")
    return abbreviation


def _int(row: dict[str, Any], *columns: str) -> int:
    """Sum of integer columns, treating missing values as 0."""
    return sum(int(row.get(c) or 0) for c in columns)


def to_player_stats(row: dict[str, Any], nfl_team: NFLTeamLookup) -> PlayerStats:
    """One row of nflreadpy.load_player_stats(summary_level="week")."""
    return PlayerStats(
        week=row["week"],
        team=nfl_team(to_espn_abbreviation(row["team"])),
        opponent=nfl_team(to_espn_abbreviation(row["opponent_team"])),
        completions=_int(row, "completions"),
        attempts=_int(row, "attempts"),
        passing_yards=_int(row, "passing_yards"),
        passing_tds=_int(row, "passing_tds"),
        interceptions=_int(row, "passing_interceptions"),
        carries=_int(row, "carries"),
        rushing_yards=_int(row, "rushing_yards"),
        rushing_tds=_int(row, "rushing_tds"),
        targets=_int(row, "targets"),
        receptions=_int(row, "receptions"),
        receiving_yards=_int(row, "receiving_yards"),
        receiving_tds=_int(row, "receiving_tds"),
        target_share=row.get("target_share"),
        air_yards_share=row.get("air_yards_share"),
        fumbles_lost=_int(
            row, "sack_fumbles_lost", "rushing_fumbles_lost", "receiving_fumbles_lost"
        ),
        two_point_conversions=_int(
            row, "passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions"
        ),
        fg_made=_int(row, "fg_made"),
        fg_att=_int(row, "fg_att"),
        pat_made=_int(row, "pat_made"),
        pat_att=_int(row, "pat_att"),
        fantasy_points=float(row.get("fantasy_points") or 0.0),
    )


def _net_passing_yards(passing_yards: int, sack_yards_lost: int) -> int:
    # nflverse passing_yards excludes sacks; sack_yards_lost is reported as a negative number
    return passing_yards - abs(sack_yards_lost)


def to_nfl_team_stats(row: dict[str, Any], nfl_team: NFLTeamLookup) -> NFLTeamStats:
    """One row of nflreadpy.load_team_stats(summary_level="week"), joined with the game's score
    (`points_scored`, `points_allowed`) and the opponent's offense (`opp_*` columns)."""
    return NFLTeamStats(
        week=row["week"],
        opponent=nfl_team(to_espn_abbreviation(row["opponent_team"])),
        points_scored=_int(row, "points_scored"),
        points_allowed=_int(row, "points_allowed"),
        pass_attempts=_int(row, "attempts"),
        passing_yards=_net_passing_yards(_int(row, "passing_yards"), _int(row, "sack_yards_lost")),
        passing_tds=_int(row, "passing_tds"),
        carries=_int(row, "carries"),
        rushing_yards=_int(row, "rushing_yards"),
        rushing_tds=_int(row, "rushing_tds"),
        turnovers=_int(row, "passing_interceptions", "fumbles_lost_total"),
        yards_allowed=_net_passing_yards(
            _int(row, "opp_passing_yards"), _int(row, "opp_sack_yards_lost")
        )
        + _int(row, "opp_rushing_yards"),
        sacks=float(row.get("def_sacks") or 0.0),
        interceptions=_int(row, "def_interceptions"),
        fumbles_recovered=_int(row, "fumble_recovery_opp"),
        defensive_tds=_int(row, "def_tds"),
        safeties=_int(row, "def_safeties"),
        blocked_kicks=_int(row, "def_punt_blocks", "def_fg_blocks", "def_pat_blocks"),
        special_teams_tds=_int(row, "special_teams_tds"),
    )
