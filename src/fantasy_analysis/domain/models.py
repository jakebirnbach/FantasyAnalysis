"""Core domain entities for a fantasy football league."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

Position = Literal["QB", "RB", "WR", "TE", "K", "DST"]
Slot = Literal["QB", "RB", "WR", "TE", "FLEX", "DST", "K", "BENCH", "IR"]
MatchupKind = Literal["REGULAR_SEASON", "PLAYOFF", "CONSOLATION"]

ALL_POSITIONS: frozenset[Position] = frozenset({"QB", "RB", "WR", "TE", "K", "DST"})

# Lineup layout for this league: slot -> (positions allowed in it, max players in it)
SLOT_RULES: dict[Slot, tuple[frozenset[Position], int]] = {
    "QB": (frozenset({"QB"}), 1),
    "RB": (frozenset({"RB"}), 2),
    "WR": (frozenset({"WR"}), 3),
    "TE": (frozenset({"TE"}), 1),
    "FLEX": (frozenset({"RB", "WR", "TE"}), 1),
    "DST": (frozenset({"DST"}), 1),
    "K": (frozenset({"K"}), 1),
    "BENCH": (ALL_POSITIONS, 6),
    "IR": (ALL_POSITIONS, 1),
}
NON_STARTING_SLOTS: frozenset[Slot] = frozenset({"BENCH", "IR"})
# Max players outside IR. The bench can exceed its nominal size when a starting slot is left empty.
ACTIVE_ROSTER_SIZE = sum(
    max_players for slot, (_, max_players) in SLOT_RULES.items() if slot != "IR"
)


@dataclass(frozen=True)
class Player:
    """An NFL player (or team defense). Identity is the ESPN player ID."""

    player_id: int
    name: str = field(compare=False)  # e.g. "Amon-Ra St. Brown", "Bears D/ST"
    position: Position = field(compare=False)
    pro_team: str = field(compare=False)  # NFL team abbreviation, e.g. "DET"
    # Later: a stats object containing weekly stats for the player


@dataclass(frozen=True)
class LineupEntry:
    """A player occupying a lineup slot in a given week, with what they scored."""

    slot: Slot
    player: Player
    points: float
    projected_points: float | None = None

    @property
    def is_starter(self) -> bool:
        return self.slot not in NON_STARTING_SLOTS


@dataclass(frozen=True)
class Lineup:
    """A team's lineup for one week. Starting slots may be left empty."""

    entries: tuple[LineupEntry, ...]

    def __post_init__(self):
        for entry in self.entries:
            allowed, _ = SLOT_RULES[entry.slot]
            if entry.player.position not in allowed:
                raise ValueError(
                    f"{entry.player.name} ({entry.player.position}) can't play {entry.slot}"
                )

        slot_counts: Counter[Slot] = Counter(e.slot for e in self.entries)
        for slot, count in slot_counts.items():
            _, max_players = SLOT_RULES[slot]
            if slot != "BENCH" and count > max_players:
                raise ValueError(f"{slot} holds at most {max_players} players, got {count}")

        active = len(self.entries) - slot_counts["IR"]
        if active > ACTIVE_ROSTER_SIZE:
            raise ValueError(f"at most {ACTIVE_ROSTER_SIZE} players outside IR, got {active}")

        ids = [e.player.player_id for e in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("a player appears in more than one slot")

    @property
    def starters(self) -> list[LineupEntry]:
        return [e for e in self.entries if e.is_starter]

    @property
    def bench(self) -> list[LineupEntry]:
        return [e for e in self.entries if not e.is_starter]

    @property
    def points(self) -> float:
        """Points scored by starters, i.e. the team's score for the week."""
        return sum(e.points for e in self.starters)


@dataclass(eq=False)
class Team:
    """A fantasy team. Identity is the ESPN team ID."""

    team_id: int
    name: str
    owners: list[str]
    lineups: dict[int, Lineup] = field(default_factory=dict, repr=False)  # week -> Lineup

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Team) and self.team_id == other.team_id

    def __hash__(self) -> int:
        return hash(self.team_id)


@dataclass(frozen=True)
class Matchup:
    """One head-to-head game in a given week. `away` is None for a bye."""

    week: int
    home: Team
    away: Team | None
    home_score: float
    away_score: float | None = None
    kind: MatchupKind = "REGULAR_SEASON"

    def __post_init__(self):
        if self.away is None and self.away_score is not None:
            raise ValueError("a bye week can't have an away score")
        if self.away is not None and self.away == self.home:
            raise ValueError(f"{self.home.name} can't play itself")

    @property
    def is_playoff(self) -> bool:
        """True for championship-bracket games (not consolation games)."""
        return self.kind == "PLAYOFF"

    @property
    def winner(self) -> Team | None:
        """The winning team, or None for a tie, bye or unplayed game."""
        if self.away is None or self.away_score is None or self.home_score == self.away_score:
            return None
        return self.home if self.home_score > self.away_score else self.away


@dataclass
class League:
    """A fantasy league for one season."""

    league_id: int
    name: str
    season: int
    teams: list[Team]
    matchups: list[Matchup] = field(default_factory=list, repr=False)

    def __post_init__(self):
        ids = [t.team_id for t in self.teams]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate team IDs")
        names = [t.name for t in self.teams]
        if len(names) != len(set(names)):
            raise ValueError("duplicate team names")

        members = set(self.teams)
        for m in self.matchups:
            for team in (m.home, m.away):
                if team is not None and team not in members:
                    raise ValueError(f"week {m.week} matchup has a team not in the league")

    @property
    def num_teams(self) -> int:
        return len(self.teams)

    def schedule(self, team: Team) -> list[Matchup]:
        """A team's matchups, ordered by week."""
        games = [m for m in self.matchups if team in (m.home, m.away)]
        return sorted(games, key=lambda m: m.week)
