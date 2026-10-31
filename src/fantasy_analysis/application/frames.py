"""DataFrame views of a League for analysis.

Each function takes domain objects and returns a DataFrame:

- teams_frame(league)            one row per team
- matchups_frame(league)         one row per matchup
- team_results_frame(league)     one row per team per game (both sides of every matchup)
- standings_frame(league)        W/L/T and points per team, for one kind of matchup
- schedule_frame(league, team)   one team's games
- lineup_frame(lineup)           one team's lineup for one week
- lineup_entries_frame(league)   one row per player per team per week, the whole season
- bench_points_frame(league)     points left on the bench, per team
"""

import pandas as pd

from fantasy_analysis.domain.models import (
    League,
    Lineup,
    LineupEntry,
    Matchup,
    MatchupKind,
    Team,
)

TEAM_RESULT_COLUMNS = [
    "week",
    "kind",
    "team_id",
    "team",
    "opponent",
    "points_for",
    "points_against",
    "result",
]
LINEUP_COLUMNS = [
    "slot",
    "starter",
    "player_id",
    "player",
    "position",
    "pro_team",
    "points",
    "projected",
]


def _result(matchup: Matchup, team: Team) -> str:
    """W / L / T / BYE for one team in a matchup."""
    if matchup.away is None:
        return "BYE"
    if matchup.winner is None:
        return "T"
    return "W" if matchup.winner == team else "L"


def _entry_row(entry: LineupEntry) -> dict:
    return {
        "slot": entry.slot,
        "starter": entry.is_starter,
        "player_id": entry.player.player_id,
        "player": entry.player.name,
        "position": entry.player.position,
        "pro_team": entry.player.pro_team,
        "points": entry.points,
        "projected": entry.projected_points,
    }


def teams_frame(league: League) -> pd.DataFrame:
    return pd.DataFrame(
        [(t.team_id, t.name, t.owner, len(t.lineups)) for t in league.teams],
        columns=["team_id", "name", "owner", "weeks_with_lineup"],
    )


def matchups_frame(league: League) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "week": m.week,
                "kind": m.kind,
                "home": m.home.name,
                "home_score": m.home_score,
                "away": m.away.name if m.away else "BYE",
                "away_score": m.away_score,
                "winner": m.winner.name if m.winner else None,
            }
            for m in league.matchups
        ],
        columns=["week", "kind", "home", "home_score", "away", "away_score", "winner"],
    )


def team_results_frame(league: League) -> pd.DataFrame:
    """One row per team per game. A bye has no opponent or points_against."""
    rows = []
    for m in league.matchups:
        sides: list[tuple[Team, float | None, Team | None, float | None]] = [
            (m.home, m.home_score, m.away, m.away_score)
        ]
        if m.away is not None:
            sides.append((m.away, m.away_score, m.home, m.home_score))
        for team, points_for, opponent, points_against in sides:
            rows.append(
                {
                    "week": m.week,
                    "kind": m.kind,
                    "team_id": team.team_id,
                    "team": team.name,
                    "opponent": opponent.name if opponent else None,
                    "points_for": points_for,
                    "points_against": points_against,
                    "result": _result(m, team),
                }
            )
    return pd.DataFrame(rows, columns=TEAM_RESULT_COLUMNS)


def standings_frame(league: League, kind: MatchupKind = "REGULAR_SEASON") -> pd.DataFrame:
    """W/L/T and points for and against per team, best record first. Byes are excluded."""
    results = team_results_frame(league)
    results = results.loc[(results["kind"] == kind) & (results["result"] != "BYE")]
    standings = results.groupby("team").agg(
        wins=("result", lambda r: (r == "W").sum()),
        losses=("result", lambda r: (r == "L").sum()),
        ties=("result", lambda r: (r == "T").sum()),
        points_for=("points_for", "sum"),
        points_against=("points_against", "sum"),
    )
    return standings.sort_values(["wins", "points_for"], ascending=False)


def schedule_frame(league: League, team: Team) -> pd.DataFrame:
    """One team's games in week order."""
    results = team_results_frame(league)
    schedule = results.loc[results["team_id"] == team.team_id]
    return schedule.drop(columns=["team_id", "team"]).sort_values("week").reset_index(drop=True)


def lineup_frame(lineup: Lineup) -> pd.DataFrame:
    return pd.DataFrame([_entry_row(e) for e in lineup.entries], columns=LINEUP_COLUMNS)


def lineup_entries_frame(league: League) -> pd.DataFrame:
    """One row per player per team per week, across the whole season."""
    return pd.DataFrame(
        [
            {"week": week, "team_id": t.team_id, "team": t.name, **_entry_row(e)}
            for t in league.teams
            for week, lineup in t.lineups.items()
            for e in lineup.entries
        ],
        columns=["week", "team_id", "team", *LINEUP_COLUMNS],
    )


def bench_points_frame(league: League) -> pd.DataFrame:
    """Points scored by players on the bench (not IR), per team, most first."""
    entries = lineup_entries_frame(league)
    bench = entries.loc[entries["slot"] == "BENCH"]
    return (
        bench.groupby("team")["points"].sum().sort_values(ascending=False).to_frame("bench_points")
    )
