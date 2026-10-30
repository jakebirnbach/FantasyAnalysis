"""Project configuration loaded from environment variables / .env."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"

    # ESPN fantasy league. espn_s2 / espn_swid are only needed for private leagues.
    espn_league_id: int | None = None
    espn_season: int = 2026
    espn_s2: str | None = None
    espn_swid: str | None = None


settings = Settings()
