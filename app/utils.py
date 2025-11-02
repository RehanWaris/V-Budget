import os
import random
import string
from datetime import datetime, timedelta
from typing import Iterable, Tuple

from fastapi import UploadFile

from .config import get_settings

settings = get_settings()


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def otp_expiry(minutes: int = 15) -> datetime:
    return datetime.utcnow() + timedelta(minutes=minutes)


def save_upload(file: UploadFile, *path_parts: str) -> Tuple[str, str]:
    directory = os.path.join(settings.uploads_dir, *path_parts)
    os.makedirs(directory, exist_ok=True)
    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{file.filename}"
    filepath = os.path.join(directory, filename)
    with open(filepath, "wb") as buffer:
        buffer.write(file.file.read())
    return filename, filepath


def vendor_default_categories() -> Iterable[str]:
    return [
        "Sound",
        "Light",
        "Fabrication",
        "Flex",
        "Truss",
        "LED",
        "Artist Management",
        "Hospitality",
        "Logistics",
        "Branding",
    ]


def log_admin_notification(subject: str, message: str) -> None:
    """Placeholder email notification - prints to console for demo."""
    print(f"[ADMIN NOTIFY] {subject}: {message}")
