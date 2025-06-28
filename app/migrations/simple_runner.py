import sqlite3
from pathlib import Path

import app.models.db


MIGRATIONS_DIR = Path(__file__).parent


def run_sql_script(script_path: Path):
    with sqlite3.connect(app.models.db.DATABASE_PATH) as conn:
        script = Path(script_path).read_text()
        conn.executescript(script)

def run_all_migrations():
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):  # apply in order
        print(f"Running migration: {sql_file}")
        run_sql_script(sql_file)
