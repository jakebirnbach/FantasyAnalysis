---
name: nflverse-adapter
description: Spec for the nflverse adapter in src/fantasy_analysis/infrastructure/nflverse/ (wraps the nflreadpy library) — loading NFL weekly player stats into PlayerStats, mapping nflverse gsis_id to ESPN player IDs, attaching stats to a League's players, and how nflverse scoring compares with the league's ESPN scoring. Use before changing the nflverse adapter, adding more nflverse data (snap counts, expected points, Next Gen Stats, injuries), joining NFL stats to league data, or debugging missing or mismatched player stats. Triggers — "player stats", "PlayerStats", "nflreadpy", "nflverse", "attach stats", "half-PPR", "gsis_id", "join NFL stats to the league", "snap counts", "expected fantasy points", "why doesn't this player have stats".
---

# nflverse adapter

Source of truth: `src/fantasy_analysis/infrastructure/nflverse/`. `notebooks/testPlayerData.ipynb`
explores every nflreadpy endpoint. Read the code before editing.

## Layout

| File | Role |
|---|---|
| `mappers.py` | `to_player_stats` and `to_nfl_team_stats`: rows → domain records. `to_espn_abbreviation` translates team abbreviations (`LA`→`LAR`, `WAS`→`WSH`; unknown ones raise). Pure, no network. |
| `repository.py` | `NflversePlayerStatsRepository` (`PlayerStatsRepository`) and `NflverseTeamStatsRepository` (`NFLTeamStatsRepository`). Both take the league's `nfl_team` lookup so records reference the league's NFLTeam objects. |

Usage:

```python
from fantasy_analysis.application.nfl_stats import attach_player_stats, attach_team_stats
from fantasy_analysis.infrastructure.nflverse import (
    NflversePlayerStatsRepository,
    NflverseTeamStatsRepository,
)

attach_player_stats(league, NflversePlayerStatsRepository())  # fills player.stats[week]
attach_team_stats(league, NflverseTeamStatsRepository())  # fills league.nfl_teams[abbr].stats[week]
```

`application.frames.player_stats_frame(league)` and `nfl_team_stats_frame(league)` give the
DataFrame views afterwards (with `espn_points` / `dst_espn_points` for rostered weeks).

## nflreadpy basics

- Returns **polars** DataFrames, cached locally after the first download. Fast (well under a
  second per dataset once cached). Keep polars inside the adapter; the domain gets plain objects.
- Public data, no credentials.
- `load_player_stats(season, summary_level="week")` has ~150 columns. `player_id` is the
  **gsis_id** (e.g. `00-0036355`). The repository keeps `season_type == "REG"` only: fantasy
  weeks 1–17 are all NFL regular-season weeks.
- `get_current_season()` / `get_current_week()` give the current NFL season and week.

## ID mapping (gsis_id → ESPN)

- `load_players()` has `espn_id` as a **string**. Cast it to `Int64` (`strict=False`) to join
  with the domain's integer `player_id`.
- Coverage checked for 2026: **100% of rostered QB, RB, WR, TE and K** match.
- **Team defenses never match.** nflverse has no player rows for D/ST, so DST players always
  have empty `stats`. Their stats come from team stats: `player.pro_team.stats[week]`.

## Team stats (`NflverseTeamStatsRepository`)

Built from three sources joined on `game_id`:
- `load_team_stats(season)`: one row per team-week with offense, defense (`def_sacks`,
  `def_interceptions`, `fumble_recovery_opp`, `def_tds`, `def_safeties`, blocks) and special
  teams (`special_teams_tds`). `def_sacks` is a float (half sacks).
- `load_schedules(season)`: the final score, giving `points_scored` / `points_allowed`. Games
  without a final score (not played yet) are dropped.
- The **opponent's** team-stats row, giving `yards_allowed` = opponent net passing (passing
  yards minus sack yards; `sack_yards_lost` is negative) + rushing yards.

Checks for 2025 and 2026: all 32 teams. Points scored total = points allowed total.
`yards_allowed` equals the opponent's net offense every week. ESPN D/ST points correlate
−0.73 with `points_allowed`, +0.6 with takeaways and sacks. The only rostered D/ST weeks
without stats are bye weeks.
- Other datasets use other IDs: snap counts and PFR stats use `pfr_id`, and FantasyPros rankings
  use `fantasypros_id`. Map those through `load_players()` or `load_ff_playerids()`.

## Scoring vs. ESPN

- The league is **half-PPR**: `PlayerStats.half_ppr_points` = nflverse `fantasy_points`
  (standard) + 0.5 × receptions.
- **2026:** 858 of 858 QB/RB/WR/TE player-weeks match ESPN exactly. **2024:** 2173 of 2180
  match. The 7 misses are differences in how the two sources recorded a play: ±2 for a fumble
  lost or two-point conversion credited by one source and not the other, and one +6 touchdown.
  These aren't adapter bugs. Expect a fraction of a percent per season.
- **Which points to use:** for any player-week on a fantasy roster (starting or benched),
  `LineupEntry.points` is ESPN's own score under the league's real rules, for every position
  including K and D/ST. Use it for league analysis. `half_ppr_points` matters only for
  player-weeks *not* on a roster (free agents, other seasons), where ESPN gives no points.
- **Kickers:** nflverse's `fantasy_points` excludes kicking, so `half_ppr_points` is 0 for
  kickers. That doesn't affect league analysis (use `LineupEntry.points`). It only matters for
  scoring unrostered kickers. The raw kicking stats (`fg_made`, `fg_att`, `pat_made`, `pat_att`) are mapped;
  kicker fantasy points would need the league's kicking rules. Distance-based field goals are
  in the raw data (`fg_made_40_49` etc.) but not yet in `PlayerStats`.

## Verifying changes

Load a league, attach stats, then check:
1. Every lineup entry's `player.stats is league.players()[player_id].stats` (shared dicts).
2. Half-PPR matches ESPN `LineupEntry.points` for QB/RB/WR/TE in weeks with stats: 100% for
   2026 and within a few player-weeks for a full past season.
3. Players with stats by position: no DST, and kickers present with kicking stats.

## Possible next additions

D/ST fantasy points from team stats (would need the league's D/ST scoring table; ESPN's
`dst_espn_points` covers rostered weeks). `load_ff_opportunity` (expected fantasy points, i.e. player-level luck), `load_snap_counts`
(snap share, via `pfr_id`), `load_injuries` and `load_nextgen_stats`. Add fields to `PlayerStats`
(or a sibling entity) and map them here. Keep the domain free of nflverse names.
