"""
backend/app/config.py — Central configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ────────────────────────────────────────────────
    SECRET_KEY           = os.getenv("SECRET_KEY", "change-me")
    FLASK_ENV            = os.getenv("FLASK_ENV", "development")
    DEBUG                = os.getenv("FLASK_DEBUG", "1") == "1"
    MAX_CONTENT_LENGTH   = 10 * 1024 * 1024   # 10 MB upload limit

    # ── JWT ──────────────────────────────────────────────────
    JWT_SECRET_KEY               = os.getenv("JWT_SECRET_KEY", "jwt-change-me")
    JWT_ACCESS_TOKEN_EXPIRES     = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 60)) * 60  # seconds
    JWT_REFRESH_TOKEN_EXPIRES    = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 30)) * 86400
    JWT_TOKEN_LOCATION           = ["cookies"]
    JWT_COOKIE_SECURE            = False        # set True in production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT      = False        # simplify for dev; enable in prod
    JWT_ACCESS_COOKIE_NAME       = "access_token_cookie"
    JWT_REFRESH_COOKIE_NAME      = "refresh_token_cookie"

    # ── PostgreSQL ───────────────────────────────────────────
    DB_HOST     = os.getenv("DB_HOST", "localhost")
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("DB_NAME", "Hospify_DBMS")
    DB_USER     = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # ── Firebase ─────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "backend/serviceAccountKey.json")
    FIREBASE_PROJECT_ID       = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET   = os.getenv("FIREBASE_STORAGE_BUCKET", "")

    # ── Gemini ───────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
