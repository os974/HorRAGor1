"""Initialise la base SQLite locale horragor.db à partir du schéma MPD schema.sql."""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "db" / "schema.sql"
DB_PATH = ROOT / "data" / "horragor.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as conn:
        # Active l'intégrité référentielle (désactivée par défaut en SQLite !)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.executescript(schema)
        conn.commit()

    print(f"✅ Base initialisée : {DB_PATH}")


if __name__ == "__main__":
    init_db()
