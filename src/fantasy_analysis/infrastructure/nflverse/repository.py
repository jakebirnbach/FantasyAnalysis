"""Stats repositories backed by nflverse (via nflreadpy)."""

import nflreadpy as nfl
import polars as pl

from fantasy_analysis.domain.models import NFLTeamStats, PlayerStats
from fantasy_analysis.domain.repositories import NFLTeamLookup
from fantasy_analysis.infrastructure.nflverse import mappers


class NflversePlayerStatsRepository:
    def get_weekly_stats(
        self, season: int, nfl_team: NFLTeamLookup
    ) -> dict[int, dict[int, PlayerStats]]:
        """Regular-season weekly stats keyed by ESPN player ID, then week.

        nflverse identifies players by gsis_id; load_players() maps it to espn_id. Players
        without an ESPN ID (and team defenses, which nflverse has no rows for) are left out.
        """
        espn_ids = (
            nfl.load_players()
            .select("gsis_id", pl.col("espn_id").cast(pl.Int64, strict=False))
            .drop_nulls()
        )
        weekly = (
            nfl.load_player_stats(season, summary_level="week")
            .filter(pl.col("season_type") == "REG")
            .join(espn_ids, left_on="player_id", right_on="gsis_id", how="inner")
        )

        stats: dict[int, dict[int, PlayerStats]] = {}
        for row in weekly.iter_rows(named=True):
            stats.setdefault(row["espn_id"], {})[row["week"]] = mappers.to_player_stats(
                row, nfl_team
            )
        return stats


class NflverseTeamStatsRepository:
    def get_weekly_team_stats(
        self, season: int, nfl_team: NFLTeamLookup
    ) -> dict[str, dict[int, NFLTeamStats]]:
        """Regular-season weekly team stats keyed by abbreviation (ESPN's form), then week.

        Combines load_team_stats (offense, defense, special teams) with the game score from
        load_schedules and the opponent's offensive row for yards allowed. Only completed games
        are included: a game without a final score yet is left out.
        """
        teams = nfl.load_team_stats(season, summary_level="week").filter(
            pl.col("season_type") == "REG"
        )
        games = nfl.load_schedules(season).drop_nulls(["home_score", "away_score"])
        scores = pl.concat(
            [
                games.select(
                    "game_id",
                    pl.col("home_team").alias("team"),
                    pl.col("home_score").alias("points_scored"),
                    pl.col("away_score").alias("points_allowed"),
                ),
                games.select(
                    "game_id",
                    pl.col("away_team").alias("team"),
                    pl.col("away_score").alias("points_scored"),
                    pl.col("home_score").alias("points_allowed"),
                ),
            ]
        )
        opponents = teams.select(
            "game_id",
            pl.col("team").alias("opponent_team"),
            pl.col("passing_yards").alias("opp_passing_yards"),
            pl.col("sack_yards_lost").alias("opp_sack_yards_lost"),
            pl.col("rushing_yards").alias("opp_rushing_yards"),
        )
        rows = teams.join(scores, on=["game_id", "team"], how="inner").join(
            opponents, on=["game_id", "opponent_team"], how="inner"
        )

        stats: dict[str, dict[int, NFLTeamStats]] = {}
        for row in rows.iter_rows(named=True):
            abbreviation = mappers.to_espn_abbreviation(row["team"])
            stats.setdefault(abbreviation, {})[row["week"]] = mappers.to_nfl_team_stats(
                row, nfl_team
            )
        return stats
