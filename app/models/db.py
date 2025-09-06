from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os, time
from sqlalchemy.exc import OperationalError

ENGINE = None
SessionLocal = None

ENGINE = None
SessionLocal = None

def init_db():
    global ENGINE, SessionLocal
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")

    # Create engine once
    ENGINE = create_engine(url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)

    # 🔁 Wait for DB to be ready (up to ~60s)
    deadline = time.time() + 60
    while True:
        try:
            with ENGINE.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id SERIAL PRIMARY KEY,
                        status TEXT NOT NULL DEFAULT 'created',
                        iterations INT NOT NULL DEFAULT 0,
                        app_id TEXT,
                        preview_url TEXT
                    );
                """))
            break
        except OperationalError:
            if time.time() > deadline:
                raise
            time.sleep(1.5)
        
def save_run(run):
    with ENGINE.begin() as conn:
        conn.execute(text("""
            INSERT INTO runs (status, iterations, app_id, preview_url, spec, criteria)
            VALUES (:status, :iterations, :app_id, :preview_url, :spec, :criteria)
        """), run)

def update_run_status(app_id, status, iterations=None, preview_url=None):
    with ENGINE.begin() as conn:
        conn.execute(text("""
            UPDATE runs SET status=:status,
                            iterations=COALESCE(:iterations, iterations),
                            preview_url=COALESCE(:preview_url, preview_url)
            WHERE app_id=:app_id
        """), {"status": status, "iterations": iterations, "preview_url": preview_url, "app_id": app_id})