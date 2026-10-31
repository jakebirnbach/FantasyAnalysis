---
name: espn-adapter
description: Spec for the ESPN fantasy football adapter in src/fantasy_analysis/infrastructure/espn/ (wraps the espn-api library) — how a season is loaded into domain models, ESPN-to-domain name mappings, and the ESPN API quirks that broke earlier assumptions. Use before changing the adapter, loading new kinds of ESPN data (stats, draft, transactions, free agents), debugging wrong or missing league data, or calling espn-api directly. Triggers — "load the league", "pull ESPN data", "add transactions/draft to the adapter", "the adapter is failing", "unsupported ESPN lineup slot", "wrong week loaded", "ESPN API", "espn-api", "box scores".
---

# ESPN adapter

Source of truth: `src/fantasy_analysis/infrastructure/espn/`. This skill records what's
non-obvious about ESPN's data. Read the code before editing.

## Layout

| File | Role |
|---|---|
| `client.py` | `connect()` builds an `espn_api.football.League`. `last_completed_week()` works out which weeks are final. Refuses seasons before 2019. |
| `mappers.py` | Pure functions converting espn-api objects to domain models, plus the name translation tables. No network calls, so it's testable offline. |
| `repository.py` | `EspnLeagueRepository` implements the domain's `LeagueRepository`. `get_league(season)` loads teams, then every completed week's box scores. |

Usage: `EspnLeagueRepository.from_settings(settings).get_league(2025)`. Credentials come from
`.env` (`ESPN_LEAGUE_ID`, and `ESPN_S2` / `ESPN_SWID` for private leagues). Never hardcode or
commit them: the repo is public.

## The endpoint

Unofficial and undocumented: ESPN can change it without notice.
`https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{id}?view=<view>`.
Seasons before 2018 use `.../leagueHistory/{id}?seasonId={season}`. espn-api switches between
these automatically.

Views: `mSettings`, `mTeam`, `mRoster`, `mMatchupScore`, `mScoreboard`, `mDraftDetail`,
`mTransactions2`, `kona_player_info`. For data espn-api doesn't model, use
`league.espn_request.league_get(params={"view": ...})`, which already handles authentication.
Don't write a separate HTTP client.

## Mapping tables (`mappers.py`)

- Positions: `D/ST` → `DST`. QB/RB/WR/TE/K pass through.
- Slots: `RB/WR/TE` → `FLEX`, `BE` → `BENCH`, `D/ST` → `DST`. QB/RB/WR/TE/K/IR pass through.
- Lineup rules: `to_slot_rules(settings.position_slot_counts)` builds each season's `SlotRules`
  from ESPN's slot counts (zero counts dropped), and `get_league` passes them to every
  `to_lineup`. espn-api types `League.settings` as its base class, so the repository narrows
  it to `espn_api.football.settings.Settings` before reading `position_slot_counts`.
- Matchup kind (`playoffTierType`): `NONE` → `REGULAR_SEASON`; `WINNERS_BRACKET` → `PLAYOFF`;
  `WINNERS_CONSOLATION_LADDER` and `LOSERS_CONSOLATION_LADDER` → `CONSOLATION`.
- An unknown value raises `ValueError("unsupported ESPN ...")`. That's deliberate: add it to the
  table (and to the domain `Slot`/`Position`/`SLOT_POSITIONS` if it's a new concept) rather than
  dropping data silently. ESPN has many more slot IDs (`OP`, `TQB`, IDP slots and others, in
  `espn_api.football.constant.POSITION_MAP`) that this league doesn't use.
- Owner: the team's first ESPN member record, as `"firstName lastName"`, falling back to
  `displayName`. ESPN allows co-owners, but every team in this league has exactly one
  (checked for 2025 and 2026). A team with no owner raises an error.

## ESPN quirks (each one has caused, or would cause, a bug)

1. **`box_scores(week)` silently returns the current week for any week beyond it.** The
   repository must cap the range itself, which `last_completed_week()` does.
2. **Working out finished weeks.** Mid-season, `scoringPeriodId` is the in-progress week, so
   the last final week is `scoringPeriodId - 1`. After the season, `scoringPeriodId` runs past
   `finalScoringPeriod` (2025: 19 vs 17), and `finalScoringPeriod` is the last week. Use
   `league.scoringPeriodId`, not `league.current_week`: espn-api caps `current_week` at
   `finalScoringPeriod`.
3. **ESPN marks consolation games as playoff games.** espn-api's `BoxScore.is_playoff` is true
   for any `playoffTierType` other than `NONE`. Use `matchup_type` and the kind table instead.
4. **Byes.** A bye team is on the home side with `away_team` None. A 6-team playoff in a
   10-team league gives the top seeds a bye (2 byes in 2025).
5. **Bench can exceed 6** when a starting slot is left empty. Lineup validation caps the
   active roster, not the bench. See the `domain-models` skill.
6. **The library types `box.home_team` as possibly None.** The repository skips such box
   scores. This hasn't been seen in practice; it's there to keep pyright satisfied.
7. **Pass one `player_team_cache` dict to every `box_scores` call in a season.** Without it,
   players on bye or traded mid-season get the wrong `proTeam`.
8. **Box scores don't exist before 2019.** espn-api raises an error. `connect()` rejects
   earlier seasons up front.
9. **Each `Matchup` is assumed to be one week.** A league with multi-week playoff rounds
   (`settings.playoff_matchup_period_length` > 1) would produce duplicate matchups with
   combined scores. Not an issue for this league.
10. **Speed:** each week costs several requests (box scores, NFL schedule, positional ratings),
    so a full season takes a while. Cache to `data/raw/` if repeated loads become painful.

## Verifying changes

Run against real data for an in-progress season, a finished one, and one from before the
2025 bench change (2022–2024 have a different lineup layout):

```python
from fantasy_analysis.config import settings
from fantasy_analysis.infrastructure.espn import EspnLeagueRepository

repo = EspnLeagueRepository.from_settings(settings)
for season in (2026, 2025, 2024):
    league = repo.get_league(season)
```

Then confirm the following. `notebooks/testLeague.ipynb` has these checks in its last cell:
- ESPN's `home_score`/`away_score` equal each side's `Lineup.points` (0 mismatches so far).
- Every team that played a week has a lineup for it.
- 2025 matchup counts: 70 regular season, 7 playoff, 9 consolation.
