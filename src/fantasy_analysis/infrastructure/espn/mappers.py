"""Pure functions converting espn-api objects into domain models."""

from espn_api.football import Team as EspnTeam
from espn_api.football.box_player import BoxPlayer

from fantasy_analysis.domain.models import (
    Lineup,
    LineupEntry,
    MatchupKind,
    Player,
    Position,
    Slot,
    Team,
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
    owners = [
        f"{o.get('firstName', '')} {o.get('lastName', '')}".strip() or o.get("displayName", "")
        for o in espn_team.owners
    ]
    return Team(team_id=espn_team.team_id, name=espn_team.team_name, owners=owners)


def to_player(box_player: BoxPlayer) -> Player:
    return Player(
        player_id=box_player.playerId,
        name=box_player.name,
        position=_lookup(POSITIONS, box_player.position, "position"),
        pro_team=box_player.proTeam,
    )


def to_lineup(box_players: list[BoxPlayer]) -> Lineup:
    return Lineup(
        tuple(
            LineupEntry(
                slot=_lookup(SLOTS, p.slot_position, "lineup slot"),
                player=to_player(p),
                points=p.points,
                projected_points=p.projected_points,
            )
            for p in box_players
        )
    )


def to_matchup_kind(playoff_tier_type: str) -> MatchupKind:
    return _lookup(MATCHUP_KINDS, playoff_tier_type, "matchup type")
