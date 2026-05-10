"""
backend/app/db.py — psycopg2 connection pool
"""
import psycopg2
from psycopg2 import pool
from flask import g, current_app


_pool: pool.ThreadedConnectionPool | None = None


def init_pool(app):
    global _pool
    cfg = app.config
    _pool = pool.ThreadedConnectionPool(
        minconn=1, maxconn=10,
        host=cfg["DB_HOST"], port=cfg["DB_PORT"],
        dbname=cfg["DB_NAME"], user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"]
    )
    app.logger.info("PostgreSQL connection pool initialised")


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
