"""Application configuration.

Settings come from environment variables (optionally loaded from a local
``.env`` file). Sensible defaults are provided so the project runs with no
setup at all.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/app/core/config.py -> backend/app/core -> backend/app -> backend
BACKEND_DIR = Path(__file__).resolve().parents[2]

load_dotenv(BACKEND_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    """Turn an environment string such as 'true' into a real boolean."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Simple settings container (kept beginner-friendly on purpose)."""

    def __init__(self) -> None:
        self.APP_NAME: str = "DailyFlow API"
        self.APP_VERSION: str = "1.0.0"
        self.APP_DESCRIPTION: str = (
            "DailyFlow - an all-in-one personal life organizer combining "
            "BillBell (bills), DateGuard (documents), DoseNote (medication) "
            "and AquaHabit (hydration)."
        )

        # SQLite database file. Kept inside backend/ so it is easy to find and reset.
        default_db_path = (BACKEND_DIR / "dailyflow.db").as_posix()
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{default_db_path}")

        # Comma separated list of browser origins allowed to call this API.
        self.CORS_ORIGINS: list[str] = [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,"
                "http://localhost:4173,http://127.0.0.1:4173,"
                "http://localhost:5174,http://127.0.0.1:5174,"
                "http://localhost:5175,http://127.0.0.1:5175",
            ).split(",")
            if origin.strip()
        ]

        # When true, any http://localhost:<port> or http://127.0.0.1:<port>
        # origin is allowed. Handy when port 5173 is already taken and you start
        # Vite on another port. Turn this OFF for anything beyond a local demo.
        self.CORS_ALLOW_ANY_LOCALHOST: bool = _as_bool(
            os.getenv("CORS_ALLOW_ANY_LOCALHOST"), default=True
        )

        # Automatically create tables + demo data when the API boots.
        self.SEED_ON_STARTUP: bool = _as_bool(os.getenv("SEED_ON_STARTUP"), default=True)


settings = Settings()