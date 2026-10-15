import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")


class Config:

    SECRET_KEY = os.getenv(
        "FLASK_SECRET_KEY",
        "dev-only-change-me"
    )

    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "nyaya.sqlite3")
    )

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY",
        ""
    )

    GEMINI_MODEL = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash"
    )

    GEMINI_FALLBACK_MODELS = os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash"
    )

    STORE_HISTORY = os.getenv(
        "STORE_HISTORY",
        "false"
    ).lower() == "true"

    MAX_QUESTION_LENGTH = int(
        os.getenv(
            "MAX_QUESTION_LENGTH",
            "5000"
        )
    )

    DEBUG = os.getenv(
        "FLASK_DEBUG",
        "false"
    ).lower() == "true"