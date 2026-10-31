"""Pure functions converting espn-api objects into domain models."""

from espn_api.football import Team as EspnTeam
from espn_api.football.box_player import BoxPlayer

from fantasy_analysis.domain.models import (
    Lineup,
    LineupEntry,
    MatchupKind,
    NFLTeam,
    Player,
    PlayerStats,
    Position,
    Slot,
    SlotRules,
    Team,
    slot_rules,
)

POSITIONS: dict[str, Position] = {
    "QB": "QB",
    "RB": "RB",
    "WR": "WR",
    "TE": "TE",
    "K": "K",
    "D/ST": "DST",
}

SLOTS: dict[str, Slot] = {
    "QB": "QB",
    "RB": "RB",
    "WR": "WR",
    "TE": "TE",
    "RB/WR/TE": "FLEX",
    "D/ST": "DST",
    "K": "K",
    "BE": "BENCH",
    "IR": "IR",
}

# ESPN playoffTierType -> domain matchup kind
MATCHUP_KINDS: dict[str, MatchupKind] = {
    "NONE": "REGULAR_SEASON",
    "WINNERS_BRACKET": "PLAYOFF",
    "WINNERS_CONSOLATION_LADDER": "CONSOLATION",
    "LOSERS_CONSOLATION_LADDER": "CONSOLATION",
}


def _lookup[T](mapping: dict[str, T], value: str, what: str) -> T:
    try:
        return mapping[value]
    except KeyError:
        raise ValueError(f"unsupported ESPN {what}: {value!r}") from None


def to_team(espn_team: EspnTeam) -> Team:
    # ESPN allows co-owners, but every team in this league has exactly one; use the first.
    if not espn_team.owners:
        raise ValueError(f"ESPN team {espn_team.team_name!r} has no owner")
    o = espn_team.owners[0]
    owner = f"{o.get('firstName', '')} {o.get('lastName', '')}".strip() or o.get("displayName", "")
    return Team(team_id=espn_team.team_id, name=espn_team.team_name, owner=owner)


# player ID -> that player's week -> stats dict, shared by all of the player's Player objects
StatsRegistry = dict[int, dict[int, PlayerStats]]
# abbreviation -> the season's one NFLTeam object (becomes League.nfl_teams)
NFLTeamRegistry = dict[str, NFLTeam]


def to_nfl_team(pro_team: str, nfl_teams: NFLTeamRegistry) -> NFLTeam | None:
    """espn-api's proTeam abbreviation as the season's NFLTeam; "None" means a free agent."""
    if pro_team == "None":
        return None
    return nfl_teams.setdefault(pro_team, NFLTeam(pro_team))


def to_player(
    box_player: BoxPlayer, stats_registry: StatsRegistry, nfl_teams: NFLTeamRegistry
) -> Player:
    return Player(
        player_id=box_player.playerId,
        name=box_player.name,
        position=_lookup(POSITIONS, box_player.position, "position"),
        pro_team=to_nfl_team(box_player.proTeam, nfl_teams),
        stats=stats_registry.setdefault(box_player.playerId, {}),
    )


def to_slot_rules(position_slot_counts: dict[str, int]) -> SlotRules:
    """A season's lineup rules from ESPN's settings.position_slot_counts."""
    return slot_rules(
        {
            _lookup(SLOTS, slot, "lineup slot"): count
            for slot, count in position_slot_counts.items()
            if count
        }
    )


def to_lineup(
    box_players: list[BoxPlayer],
    rules: SlotRules,
    stats_registry: StatsRegistry,
    nfl_teams: NFLTeamRegistry,
) -> Lineup:
    return Lineup(
        tuple(
            LineupEntry(
                slot=_lookup(SLOTS, p.slot_position, "lineup slot"),
                player=to_player(p, stats_registry, nfl_teams),
                points=p.points,
                projected_points=p.projected_points,
            )
            for p in box_players
        ),
        rules=rules,
    )


def to_matchup_kind(playoff_tier_type: str) -> MatchupKind:
    return _lookup(MATCHUP_KINDS, playoff_tier_type, "matchup type")
