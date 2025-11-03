# app/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "V-Budget"
    debug_mode: bool = True

    # DB (SQLite by default; you can override with env)
    database_url: str = "sqlite:///./dev.db"

    # Auth/JWT
    secret_key: str = "replace-this-with-a-long-random-string"
    jwt_algorithm: str = "HS256"          # <- add this (name exactly as used below)
    access_token_expire_minutes: int = 60

    # Admin bootstrap
    admin_email: str = "rehan@voiceworx.in"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
