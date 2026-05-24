from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- auth (опционально: без авторизации работает как гость) ---
    api_key: Optional[str] = None
    cookie: Optional[str] = None  # raw Cookie header: "name=value; name2=value2"

    base_url: str = "https://api.arkm.com"
    provider: str = "playwright"  # имя в providers/_REGISTRY
    headless: bool = True

    model_config = {"env_prefix": "ARKHAM_"}


_settings: Optional["Settings"] = None


def get_settings() -> "Settings":
    """Lazy singleton — читает env только при первом вызове."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
