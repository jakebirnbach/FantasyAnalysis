# Fantasy Analysis

Data analysis for my fantasy football league, structured with Clean Architecture.

## Layout

```
src/fantasy_analysis/
├── domain/            # Core entities & rules (Player, League, ...) — depends on nothing else
├── infrastructure/    # API clients & storage — depends on domain
├── application/       # Use cases & runnable scripts — depends on domain
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
- Run a script: `uv run python -m fantasy_analysis.application.<name>`
- Notebooks: `uv run jupyter lab` (kernel: "Fantasy Analysis")
- Tests / lint: `uv run pytest`, `uv run ruff check .`
