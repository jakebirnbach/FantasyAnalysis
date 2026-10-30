# FantasyAnalysis

Data analysis for an ESPN fantasy football league, structured with Clean Architecture.

## Layout

```
src/fantasy_analysis/
├── domain/            # models.py (entities), repositories.py (interfaces). Depends on nothing.
├── infrastructure/    # espn/ — adapter wrapping the espn-api library. Depends on domain.
├── application/       # use cases and runnable scripts. Depends on domain interfaces.
└── config.py          # pydantic-settings, reads .env
notebooks/             # exploration; testAPI (raw espn-api), testLeague (adapter output)
```

**Dependency rule:** inner layers never import outer ones. `espn_api` is imported only inside
`infrastructure/espn/`. Application code gets data through `LeagueRepository`, never `espn_api`.

Skills with the detailed specs:
- `domain-models`: entities, invariants, slot rules. Load before changing `domain/`.
- `espn-adapter`: ESPN API quirks and mapping rules. Load before changing `infrastructure/espn/`.

## Commands

Everything runs through `uv` (Python 3.13, venv in `.venv`):

```bash
uv sync                                   # install / rebuild venv
uv add <pkg>   /   uv add --dev <pkg>     # add a dependency
uv run ruff format src && uv run ruff check src notebooks
uvx pyright --pythonpath .venv/bin/python src/
uv run pytest
uv run python -m fantasy_analysis.application.<name>
```

To test-run a notebook without touching the committed file, execute it into the scratchpad:
`uv run jupyter nbconvert --to notebook --execute notebooks/X.ipynb --output-dir <scratch> --output X_run`

## Conventions

- Ruff (line length 100) and pyright must both be clean.
- Domain entities are dataclasses. Identity is the ESPN ID (`player_id`, `team_id`), not names.
- Validate changes to the adapter against real league data (`EspnLeagueRepository.get_league`)
  for both the current season and a finished one. ESPN data has broken assumptions before.

## Git and privacy

- **The GitHub repo is public** (github.com/jakebirnbach/FantasyAnalysis). Never commit `.env`,
  ESPN cookies, the league ID, files in `data/`, or notebook outputs (they contain league
  members' real names).
- Notebook outputs are stripped on commit by nbstripout (`.gitattributes` + a filter in
  `.git/config`). The filter is required, so commits fail if `.venv` is missing: run `uv sync`.
- Commit and push as the personal account: git `user.email` is set to jakebirnbach@gmail.com
  for this repo, and `gh` must have `jakebirnbach` as the active account
  (`gh auth switch --user jakebirnbach`), not the work account.
