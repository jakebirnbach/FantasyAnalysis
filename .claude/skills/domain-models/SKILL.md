---
name: domain-models
description: Spec for the fantasy league domain entities in src/fantasy_analysis/domain/ — Player, LineupEntry, Lineup, Team, Matchup, League, per-season lineup rules (SlotRules), and their invariants. Use before adding, changing or validating domain objects, writing analysis or application code that consumes them, or when deciding where new data (stats, transactions, draft) belongs in the model. Triggers — "add a field to Player", "change the lineup rules", "model weekly stats", "add a Draft/Transaction entity", "why does Lineup reject this", "how are points calculated", "domain objects", "domain models".
---

# Domain models

Source of truth: `src/fantasy_analysis/domain/models.py` (entities) and
`src/fantasy_analysis/domain/repositories.py` (`LeagueRepository` interface). Read them before
editing. This skill records the design decisions and the reasons behind them.

## Rules for the domain layer

- No imports from `infrastructure`, `application` or `espn_api`. Platform-specific names
  (`"D/ST"`, `"BE"`, `"RB/WR/TE"`) are translated in the adapter, never stored here.
- Entities are dataclasses. Value-like facts are `frozen=True`: `Player`, `LineupEntry`,
  `Lineup`, `Matchup`.
- Identity is the ESPN ID, never a name:
  - `Player`: every field except `player_id` has `compare=False`, so equality and hashing use
    the ID only.
  - `Team`: `eq=False` with explicit `__eq__`/`__hash__` on `team_id`. It stays mutable because
    the adapter fills in `lineups` week by week.

## Entities

| Entity | Key fields | Notes |
|---|---|---|
| `Player` | `player_id`, `name`, `position`, `pro_team: NFLTeam \| None`, `stats: dict[week, PlayerStats]` | One `name` field. Splitting into first/last is lossy ("Amon-Ra St. Brown"); D/ST is e.g. "Bears D/ST". `stats` is empty until attached (see below). |
| `NFLTeam` | `abbreviation` (ESPN's form: `DET`, `LAR`, `WSH`), `stats: dict[week, NFLTeamStats]` | An NFL team. Identity is the abbreviation. One object per team per `League`. `pro_team` is `None` for a free agent. |
| `NFLTeamStats` | `week`, `opponent: NFLTeam`, `points_scored`, `points_allowed`, offense totals, `yards_allowed`, `sacks`, `interceptions`, `fumbles_recovered`, `defensive_tds`, `safeties`, `blocked_kicks`, `special_teams_tds` | One NFL team's game. Defense/special-teams fields are what a D/ST is scored on. `.takeaways`. No entry on a bye. |
| `PlayerStats` | `week`, `team: NFLTeam`, `opponent: NFLTeam`, passing/rushing/receiving/kicking counts, `target_share`, `fantasy_points` | One player's NFL box score for one week. `.half_ppr_points` = standard + 0.5/reception, this league's scoring for QB/RB/WR/TE. `fantasy_points` excludes kicking. |
| `LineupEntry` | `slot`, `player`, `points`, `projected_points` | One player in one slot for one week. Bench players have points too, which allows "points left on bench" analysis. |
| `Lineup` | `entries: tuple[LineupEntry, ...]` | `.starters`, `.bench` (BENCH + IR), `.points` = sum of starters' points = the team's score. |
| `Team` | `team_id`, `name`, `owner: str`, `lineups: dict[week, Lineup]` | One owner per team: every team in this league has exactly one. "Roster" is deliberately not used for weekly lineups. |
| `Matchup` | `week`, `home`, `away \| None`, `home_score`, `away_score`, `kind` | `away=None` is a bye. `.winner` is None for ties, byes and unplayed games. |
| `League` | `league_id`, `name`, `season`, `teams`, `matchups` | One season. `num_teams` = `len(teams)`. `.schedule(team)` = that team's matchups in week order. `.players()` = one `Player` per ID from all lineups. `nfl_teams` + `.nfl_team(abbr)` = the season's NFLTeam objects (get or create). |

`MatchupKind` is `REGULAR_SEASON | PLAYOFF | CONSOLATION`. `Matchup.is_playoff` is true only for
`PLAYOFF` (the championship bracket). Consolation games are kept separate so they don't skew
playoff stats.

Schedules belong to the league as `Matchup` objects, not to teams. An earlier
`Team.schedule: dict[week, Team]` created reference cycles and couldn't hold scores.

## Lineup rules (`SlotRules`)

Lineup layouts change between seasons, so the rules are data, not a constant:
- `SLOT_POSITIONS`: which positions each slot accepts. This never changes.
- `SlotRules`: a season's layout, mapping slot → (allowed positions, max players). Build one
  with `slot_rules({"QB": 1, ..., "BENCH": 6})`.
- Every `Lineup` carries its season's `rules` (`compare=False`). The ESPN adapter builds them
  from each season's `position_slot_counts`.
- `SLOT_RULES` is the current layout (QB 1, RB 2, WR 3, TE 1, FLEX 1, DST 1, K 1, BENCH 6,
  IR 1). It's only the default for a `Lineup` built without rules, e.g. in tests.

This league's history: identical starting lineups every season, but **7 bench spots in
2022–2024 and 6 from 2025**. Validating older seasons against today's layout fails ("at most
16 players outside IR, got 17"), which is why the rules are per season.

`Lineup.__post_init__` checks, against its own `rules`:
1. Every slot used exists in that season's layout.
2. Each player's position is allowed in their slot.
3. No slot except BENCH is over its max.
4. Active players (everyone not on IR) ≤ `active_roster_size(rules)` (16 now, 17 in 2022–2024).
5. No player appears twice (by `player_id`).

Two rules come from real league data:
- **Starting slots may be empty.** Managers forget lineups, or bench an injured or bye-week
  player without replacing them. Never require every slot to be filled.
- **BENCH has no hard max.** With a starting slot empty, that player sits on the bench, giving
  7 bench players (seen in 2026 week 4 and 2025 week 17). The real limit is the active roster
  size.

## NFL teams

NFL teams are `NFLTeam` objects, never strings. `League.nfl_teams` holds **one per team for the
season**: the ESPN adapter creates them while loading lineups, and stats repositories get
`league.nfl_team` (a lookup that creates on first use) so every `Player.pro_team`,
`PlayerStats.team`/`opponent` and `NFLTeamStats.opponent` points at the same object.
- A **D/ST's stats are its team's**: `dst_player.pro_team.stats[week]` (an `NFLTeamStats`).
  `Player.stats` is always empty for D/ST.
- `application.nfl_stats.attach_team_stats(league, repo)` fills every team's `stats`.
- `NFLTeam` → `stats` → `opponent` → `stats` … forms reference cycles. Don't use
  `dataclasses.asdict` on stats records (it would recurse); `frames._record` flattens them and
  writes NFL teams as abbreviations.
- Abbreviations are ESPN's form. Adapters translate other sources (nflverse `LA`→`LAR`,
  `WAS`→`WSH`).

## Player stats and shared Player objects

The same player appears as **several `Player` objects**, one per lineup entry, so each keeps
that week's `pro_team` (a mid-season trade changes it). Equality and hashing use `player_id`
only. Within one `League`, all of a player's objects **share one `stats` dict**: the ESPN adapter
hands every copy the same dict from a per-season registry. So:
- `application.nfl_stats.attach_player_stats(league, repo)` fills each player's dict once,
  through `league.players()`, and every lineup entry sees it.
- Don't replace `player.stats`, only mutate it. `Player` is frozen, so it can't be reassigned
  anyway; `update()` it instead.
- A `Player` built by hand (e.g. in a test) has its own empty dict.
- Stats are per season: each `League` load has its own registry, and `stats` is keyed by week.

`PlayerStatsRepository.get_weekly_stats(season, nfl_team)` returns `{player_id: {week: PlayerStats}}` keyed
by the domain's (ESPN) player ID. The adapter does any ID translation.

## Not modeled yet

- ESPN's per-stat fantasy point breakdowns (`points_breakdown`): available but not mapped.
  NFL box scores come from nflverse instead (`PlayerStats`).
- Kicker fantasy points from stats (ESPN's `LineupEntry.points` covers rostered weeks).
- Draft, transactions, free agents, waivers.
- Multi-week matchups: each `Matchup` is assumed to be one week. True for this league
  (`playoff_matchup_period_length` = 1).
- Other league settings (scoring rules, playoff format) aren't modeled. Only the lineup
  layout is per season.

When adding one of these, keep the same pattern: a domain entity with no ESPN names, a mapper in
`infrastructure/espn/mappers.py`, and assembly in the repository.
