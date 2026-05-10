"""
backend/app/db.py — psycopg2 connection pool
"""
import psycopg2
from psycopg2 import pool
from flask import g, current_app
from urllib.parse import urlparse


_pool: pool.ThreadedConnectionPool | None = None


def init_pool(app):
    global _pool
    cfg = app.config
    
    # Support DATABASE_URL (Supabase pooler format) or individual vars
    database_url = cfg.get("DATABASE_URL", "")
    
    if database_url:
        # Parse DATABASE_URL for connection
        parsed = urlparse(database_url)
        _pool = pool.ThreadedConnectionPool(
            minconn=1, maxconn=10,
            host=parsed.hostname,
            port=parsed.port or 5432,
            dbname=parsed.path.lstrip("/"),
            user=parsed.username,
            password=parsed.password,
            sslmode="require"  # Required for Supabase
        )
        app.logger.info(f"PostgreSQL pool initialised via DATABASE_URL (host: {parsed.hostname})")
    else:
        _pool = pool.ThreadedConnectionPool(
            minconn=1, maxconn=10,
            host=cfg["DB_HOST"], port=cfg["DB_PORT"],
            dbname=cfg["DB_NAME"], user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"]
        )
        app.logger.info("PostgreSQL connection pool initialised via individual vars")


def get_db():
    """Return a connection from the pool, stored on Flask's g per request."""
    if "db" not in g:
        g.db = _pool.getconn()
        g.db.autocommit = False
    return g.db


def release_db(e=None):
    """Release connection back to pool at end of request."""
    db = g.pop("db", None)
    if db is not None:
        _pool.putconn(db)


def init_app(app):
    init_pool(app)
    app.teardown_appcontext(release_db)
