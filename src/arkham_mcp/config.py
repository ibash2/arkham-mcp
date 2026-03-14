from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- auth (хотя бы одно обязательно) ---
    api_key: Optional[str] = None
    cookie: Optional[str] = None  # raw Cookie header: "name=value; name2=value2"

    base_url: str = "https://intel.arkm.com/api"
    provider: str = "playwright"  # имя в providers/_REGISTRY

    model_config = {"env_prefix": "ARKHAM_"}

    @model_validator(mode="after")
    def check_auth_provided(self) -> "Settings":
        if not self.api_key and not self.cookie:
            raise ValueError(
                "Authentication required: set ARKHAM_API_KEY or ARKHAM_COOKIE (or both)."
            )
        return self


_settings: Optional["Settings"] = None


def get_settings() -> "Settings":
    """Lazy singleton — читает env только при первом вызове."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
