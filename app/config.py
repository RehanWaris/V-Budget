from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    app_name: str = "V-Budget"
    secret_key: str = os.getenv("VBUDGET_SECRET_KEY", "super-secret-key-change-me")
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"
    database_url: str = os.getenv("VBUDGET_DATABASE_URL", "sqlite:///./vbudget.db")
    uploads_dir: str = os.getenv("VBUDGET_UPLOADS_DIR", "./uploads")
    admin_email: str = os.getenv("VBUDGET_ADMIN_EMAIL", "rehan@voiceworx.in")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.uploads_dir, exist_ok=True)
    return settings
