"""Core domain entities for a fantasy football league."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

Position = Literal["QB", "RB", "WR", "TE", "K", "DST"]
Slot = Literal["QB", "RB", "WR", "TE", "FLEX", "DST", "K", "BENCH", "IR"]
MatchupKind = Literal["REGULAR_SEASON", "PLAYOFF", "CONSOLATION"]

ALL_POSITIONS: frozenset[Position] = frozenset({"QB", "RB", "WR", "TE", "K", "DST"})

# Positions each slot accepts. These are fixed; how many of each slot a league has can change
# from season to season.
SLOT_POSITIONS: dict[Slot, frozenset[Position]] = {
    "QB": frozenset({"QB"}),
    "RB": frozenset({"RB"}),
    "WR": frozenset({"WR"}),
    "TE": frozenset({"TE"}),
    "FLEX": frozenset({"RB", "WR", "TE"}),
    "DST": frozenset({"DST"}),
    "K": frozenset({"K"}),
    "BENCH": ALL_POSITIONS,
    "IR": ALL_POSITIONS,
}
NON_STARTING_SLOTS: frozenset[Slot] = frozenset({"BENCH", "IR"})

# A season's lineup layout: slot -> (positions allowed in it, max players in it)
SlotRules = dict[Slot, tuple[frozenset[Position], int]]


def slot_rules(counts: dict[Slot, int]) -> SlotRules:
    """Lineup rules from a season's slot counts. Slots with a count of 0 are left out."""
    return {slot: (SLOT_POSITIONS[slot], n) for slot, n in counts.items() if n}


def active_roster_size(rules: SlotRules) -> int:
    """Max players outside IR. The bench can exceed its nominal size when a starting slot is
    left empty, so this, not the bench size, is the real limit."""
    return sum(max_players for slot, (_, max_players) in rules.items() if slot != "IR")


# This league's current layout (2025 onward; 2022-2024 had 7 bench spots). Used when a Lineup
# isn't given a season's rules.
SLOT_RULES: SlotRules = slot_rules(
    {"QB": 1, "RB": 2, "WR": 3, "TE": 1, "FLEX": 1, "DST": 1, "K": 1, "BENCH": 6, "IR": 1}
)


@dataclass(eq=False)
class NFLTeam:
    """An NFL team. Identity is its abbreviation, in ESPN's form (e.g. "DET", "LAR", "WSH").

    Within a League there is one NFLTeam object per team (`League.nfl_team`), so every player
    and stats record points at the same object and `stats` attached once is seen everywhere.
    """

    abbreviation: str
    # week -> that week's team stats. Empty until team stats are attached; no entry on a bye.
    stats: dict[int, NFLTeamStats] = field(default_factory=dict, repr=False)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NFLTeam) and self.abbreviation == other.abbreviation

    def __hash__(self) -> int:
        return hash(self.abbreviation)


@dataclass(frozen=True)
class NFLTeamStats:
    """One NFL team's game for one week: offense, defense and special teams.

    Defense and special-teams fields are what a fantasy D/ST is scored on.
    """

    week: int
    opponent: NFLTeam
    points_scored: int
    points_allowed: int
    # Offense
    pass_attempts: int = 0
    passing_yards: int = 0  # net of sack yardage
    passing_tds: int = 0
    carries: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    turnovers: int = 0  # interceptions thrown + fumbles lost
    # Defense
    yards_allowed: int = 0  # opponent's net passing + rushing yards
    sacks: float = 0.0  # half sacks are possible
    interceptions: int = 0
    fumbles_recovered: int = 0
    defensive_tds: int = 0
    safeties: int = 0
    blocked_kicks: int = 0  # punts, field goals and extra points
    # Special teams
    special_teams_tds: int = 0

    @property
    def takeaways(self) -> int:
        return self.interceptions + self.fumbles_recovered


@dataclass(frozen=True)
class PlayerStats:
    """One player's NFL box score for one week."""

    week: int
    team: NFLTeam  # the player's NFL team that week
    opponent: NFLTeam
    # Passing
    completions: int = 0
    attempts: int = 0
    passing_yards: int = 0
    passing_tds: int = 0
    interceptions: int = 0
    # Rushing
    carries: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    # Receiving
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    target_share: float | None = None  # share of the team's targets
    air_yards_share: float | None = None  # share of the team's air yards
    # Ball security and extras
    fumbles_lost: int = 0
    two_point_conversions: int = 0
    # Kicking
    fg_made: int = 0
    fg_att: int = 0
    pat_made: int = 0
    pat_att: int = 0
    # Standard (non-PPR) fantasy points, excluding kicking
    fantasy_points: float = 0.0

    @property
    def half_ppr_points(self) -> float:
        """This league's scoring for QB/RB/WR/TE: standard plus 0.5 per reception.
        Not valid for kickers, whose points aren't in `fantasy_points`."""
        return self.fantasy_points + 0.5 * self.receptions


@dataclass(frozen=True)
class Player:
    """An NFL player (or team defense). Identity is the ESPN player ID.

    The same player can appear as several Player objects (one per lineup entry, each with that
    week's `pro_team`). Within a League they all share one `stats` dict, so stats attached once
    are visible from every entry. A D/ST's own stats are its team's: `pro_team.stats[week]`.
    """

    player_id: int
    name: str = field(compare=False)  # e.g. "Amon-Ra St. Brown", "Bears D/ST"
    position: Position = field(compare=False)
    pro_team: NFLTeam | None = field(compare=False)  # None for a free agent
    # week -> that week's stats. Empty for team defenses and until stats are attached.
    stats: dict[int, PlayerStats] = field(default_factory=dict, compare=False, repr=False)


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
    """A team's lineup for one week, validated against that season's lineup rules.
    Starting slots may be left empty."""

    entries: tuple[LineupEntry, ...]
    rules: SlotRules = field(default_factory=lambda: SLOT_RULES, compare=False, repr=False)

    def __post_init__(self):
        for entry in self.entries:
            if entry.slot not in self.rules:
                raise ValueError(f"this season's lineup has no {entry.slot} slot")
            allowed, _ = self.rules[entry.slot]
            if entry.player.position not in allowed:
                raise ValueError(
                    f"{entry.player.name} ({entry.player.position}) can't play {entry.slot}"
                )

        slot_counts: Counter[Slot] = Counter(e.slot for e in self.entries)
        for slot, count in slot_counts.items():
            _, max_players = self.rules[slot]
            if slot != "BENCH" and count > max_players:
                raise ValueError(f"{slot} holds at most {max_players} players, got {count}")

        active = len(self.entries) - slot_counts["IR"]
        max_active = active_roster_size(self.rules)
        if active > max_active:
            raise ValueError(f"at most {max_active} players outside IR, got {active}")

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
    owner: str
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
    # abbreviation -> the one NFLTeam object for this season. Use nfl_team() to look up or add.
    nfl_teams: dict[str, NFLTeam] = field(default_factory=dict, repr=False)

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

    def nfl_team(self, abbreviation: str) -> NFLTeam:
        """This season's NFLTeam for an abbreviation (ESPN's form), created on first use."""
        return self.nfl_teams.setdefault(abbreviation, NFLTeam(abbreviation))

    def players(self) -> dict[int, Player]:
        """Every player who appeared in any lineup this season, by player ID."""
        return {
            e.player.player_id: e.player
            for t in self.teams
            for lineup in t.lineups.values()
            for e in lineup.entries
        }
