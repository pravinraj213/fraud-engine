from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Every setting the app reads, loaded from environment variables or backend/.env."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = f"sqlite:///{BACKEND_DIR / 'fraud.db'}"
    rules_config_path: Path = BACKEND_DIR / "rules.yaml"
    high_risk_threshold: int = 70

    # log = write alerts to the server log; ses = send email through Amazon SES
    notifier: str = "log"
    aws_region: str = "ap-south-1"
    aws_profile: str | None = None
    ses_sender_email: str = ""
    alert_recipient_email: str = ""  # one address, or several separated by commas
    # Safety cap: at most this many alerts are sent per rolling 24 hours (SES sandbox allows 200).
    # Alerts beyond the cap are recorded as FAILED and not sent.
    alert_daily_limit: int = 20

    console_base_url: str = "http://localhost:5173"
    cors_origins: str = "http://localhost:5173"

    @property
    def alert_recipients(self) -> list[str]:
        return [a.strip() for a in self.alert_recipient_email.split(",") if a.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
