"""
apply_sql.py — Run all SQL setup files against Hospify_DBMS.
Run from project root with venv active:
    python backend/apply_sql.py
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "Hospify_DBMS")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

SQL_DIR = Path(__file__).parent / "sql"

# Order matters — schema first, then indexes, functions, triggers, procedures, views
SQL_FILES = [
    "schema.sql",
    "indexes.sql",
    "functions.sql",
    "triggers.sql",
    "procedures.sql",
    "views.sql",
]

def apply_file(conn, filepath: Path):
    sql = filepath.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"  [OK] {filepath.name}")

def main():
    print("\n── Applying SQL files to PostgreSQL ─────────────────")
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD
        )
        conn.autocommit = False
    except Exception as e:
        print(f"  [FAIL] Could not connect: {e}")
        sys.exit(1)

    for fname in SQL_FILES:
        fpath = SQL_DIR / fname
        if not fpath.exists():
            print(f"  [SKIP] {fname} not found")
            continue
        try:
            apply_file(conn, fpath)
        except Exception as e:
            conn.rollback()
            print(f"  [FAIL] {fname}: {e}")
            conn.close()
            sys.exit(1)

    conn.close()
    print("── All SQL files applied successfully ───────────────\n")

if __name__ == "__main__":
    main()
