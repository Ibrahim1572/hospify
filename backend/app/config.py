"""
backend/app/config.py — Central configuration loaded from .env
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Detect if running in production (Vercel sets VERCEL=1)
IS_PRODUCTION = os.getenv("VERCEL", "") == "1" or os.getenv("FLASK_ENV", "development") == "production"


class Config:
    # ── Flask ────────────────────────────────────────────────
    SECRET_KEY           = os.getenv("SECRET_KEY", "change-me")
    FLASK_ENV            = os.getenv("FLASK_ENV", "production" if IS_PRODUCTION else "development")
    DEBUG                = False if IS_PRODUCTION else os.getenv("FLASK_DEBUG", "1") == "1"
    MAX_CONTENT_LENGTH   = 10 * 1024 * 1024   # 10 MB upload limit

    # ── JWT ──────────────────────────────────────────────────
    # Use SUPABASE_JWT_SECRET if available (from Supabase integration), fallback to JWT_SECRET_KEY
    JWT_SECRET_KEY               = os.getenv("JWT_SECRET_KEY", os.getenv("SUPABASE_JWT_SECRET", "jwt-change-me"))
    JWT_ACCESS_TOKEN_EXPIRES     = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 60)) * 60  # seconds
    JWT_REFRESH_TOKEN_EXPIRES    = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 30)) * 86400
    JWT_TOKEN_LOCATION           = ["cookies"]
    JWT_COOKIE_SECURE            = IS_PRODUCTION  # True in production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT      = False  # Keep False for simpler cookie auth
    JWT_COOKIE_SAMESITE          = "Lax" if IS_PRODUCTION else None
    JWT_ACCESS_COOKIE_NAME       = "access_token_cookie"
    JWT_REFRESH_COOKIE_NAME      = "refresh_token_cookie"

    # ── PostgreSQL (supports POSTGRES_URL, DATABASE_URL, or individual vars) ─
    # Supabase integration provides POSTGRES_URL, fallback to DATABASE_URL for compatibility
    DATABASE_URL = os.getenv("POSTGRES_URL", os.getenv("DATABASE_URL", ""))
    DB_HOST     = os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "localhost"))
    DB_PORT     = int(os.getenv("DB_PORT", 5432))
    DB_NAME     = os.getenv("POSTGRES_DATABASE", os.getenv("DB_NAME", "Hospify_DBMS"))
    DB_USER     = os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres"))
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", ""))

    # ── Firebase ─────────────────────────────────────────────
    FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "backend/serviceAccountKey.json")
    FIREBASE_CREDENTIALS_JSON = os.getenv("FIREBASE_CREDENTIALS_JSON", "")  # Alternative: JSON string
    FIREBASE_PROJECT_ID       = os.getenv("FIREBASE_PROJECT_ID", "")
    FIREBASE_STORAGE_BUCKET   = os.getenv("FIREBASE_STORAGE_BUCKET", "")

    # ── Gemini ───────────────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # ── CORS ─────────────────────────────────────────────────
    # In production, allow the Vercel deployment URL and any custom domains
    _cors_env = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS = (
        [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
        if _cors_env
        else ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    )
    
    # Add Vercel URL automatically in production
    if IS_PRODUCTION:
        vercel_url = os.getenv("VERCEL_URL", "")
        if vercel_url and f"https://{vercel_url}" not in CORS_ORIGINS:
            CORS_ORIGINS.append(f"https://{vercel_url}")
        # Also add the production domain
        vercel_project_domain = os.getenv("VERCEL_PROJECT_PRODUCTION_URL", "")
        if vercel_project_domain and f"https://{vercel_project_domain}" not in CORS_ORIGINS:
            CORS_ORIGINS.append(f"https://{vercel_project_domain}")
