# Fantasy Analysis

Data analysis for my fantasy football league, structured with Clean Architecture.

## Layout

```
src/fantasy_analysis/
├── domain/            # Core entities & rules — depends on nothing else
│   ├── models/        # Player, League, Team, Matchup, ...
│   └── repositories/  # Abstract interfaces (ports) for data access
├── infrastructure/    # Adapters to the outside world — depends on domain
│   ├── api/           # Fantasy platform API clients
│   └── persistence/   # File/DB storage implementing domain repositories
├── application/       # Use cases — depends on domain (+ infra via interfaces)
│   ├── services/      # Use-case logic
│   └── scripts/       # Runnable entry points
└── config.py          # Settings from env / .env
notebooks/             # Exploratory analysis (imports from fantasy_analysis)
data/raw, data/processed  # Local data (git-ignored)
tests/
```

Dependency rule: `domain` ← `application` ← `infrastructure`; inner layers never import outer ones.

## Setup

```bash
uv sync                       # creates .venv and installs everything
source .venv/bin/activate
cp .env.example .env
```

- Add a library: `uv add <pkg>` (or `uv add --dev <pkg>`)
- Run a script: `uv run python -m fantasy_analysis.application.scripts.<name>`
- Notebooks: `uv run jupyter lab` (kernel: "Fantasy Analysis")
- Tests / lint: `uv run pytest`, `uv run ruff check .`
