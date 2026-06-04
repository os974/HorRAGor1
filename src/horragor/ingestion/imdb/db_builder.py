"""Construit la base SQLite intermédiaire IMDB (TSV.gz -> data/intermediate/imdb.db)."""

import csv
import gzip
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

RAW_BASICS = Path("data/raw/imdb/title.basics.tsv.gz")
RAW_RATINGS = Path("data/raw/imdb/title.ratings.tsv.gz")
IMDB_DB = Path("data/intermediate/imdb.db")

BATCH_SIZE = 50_000


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS title_basics (
            tconst          TEXT PRIMARY KEY,
            titleType       TEXT,
            primaryTitle    TEXT,
            originalTitle   TEXT,
            startYear       INTEGER,
            runtimeMinutes  INTEGER,
            genres          TEXT
        );

        CREATE TABLE IF NOT EXISTS title_ratings (
            tconst          TEXT PRIMARY KEY,
            averageRating   REAL,
            numVotes        INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_basics_type ON title_basics(titleType);
        CREATE INDEX IF NOT EXISTS idx_basics_genres ON title_basics(genres);
    """)
    conn.commit()


def _load_basics(conn: sqlite3.Connection) -> None:
    logger.info("Chargement title.basics...")
    count = 0
    batch = []

    with gzip.open(RAW_BASICS, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # Filtre en amont : uniquement les films
            if row["titleType"] != "movie":
                continue

            batch.append(
                (
                    row["tconst"],
                    row["titleType"],
                    row["primaryTitle"],
                    row["originalTitle"],
                    None if row["startYear"] == "\\N" else int(row["startYear"]),
                    None
                    if row["runtimeMinutes"] == "\\N"
                    else int(row["runtimeMinutes"]),
                    None if row["genres"] == "\\N" else row["genres"],
                )
            )

            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT OR REPLACE INTO title_basics VALUES (?,?,?,?,?,?,?)", batch
                )
                conn.commit()
                count += len(batch)
                batch.clear()
                logger.info(f"  {count:,} films insérés...")

    if batch:
        conn.executemany(
            "INSERT OR REPLACE INTO title_basics VALUES (?,?,?,?,?,?,?)", batch
        )
        conn.commit()
        count += len(batch)

    logger.info(f"title_basics : {count:,} films au total")


def _load_ratings(conn: sqlite3.Connection) -> None:
    logger.info("Chargement title.ratings...")
    count = 0
    batch = []

    with gzip.open(RAW_RATINGS, "rt", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            batch.append(
                (
                    row["tconst"],
                    float(row["averageRating"]),
                    int(row["numVotes"]),
                )
            )

            if len(batch) >= BATCH_SIZE:
                conn.executemany(
                    "INSERT OR REPLACE INTO title_ratings VALUES (?,?,?)", batch
                )
                conn.commit()
                count += len(batch)
                batch.clear()

    if batch:
        conn.executemany("INSERT OR REPLACE INTO title_ratings VALUES (?,?,?)", batch)
        conn.commit()
        count += len(batch)

    logger.info(f"title_ratings : {count:,} notes au total")


def load_imdb_to_sqlite(force: bool = False) -> Path:
    IMDB_DB.parent.mkdir(parents=True, exist_ok=True)

    if IMDB_DB.exists() and not force:
        logger.info("imdb.db déjà présent, skip (utilise force=True pour recharger)")
        return IMDB_DB

    if IMDB_DB.exists():
        IMDB_DB.unlink()

    conn = sqlite3.connect(IMDB_DB)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    try:
        _create_schema(conn)
        _load_basics(conn)
        _load_ratings(conn)
    finally:
        conn.close()

    logger.info(
        f"imdb.db prêt : {IMDB_DB} ({IMDB_DB.stat().st_size / 1_000_000:.1f} MB)"
    )
    return IMDB_DB


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    load_imdb_to_sqlite()
