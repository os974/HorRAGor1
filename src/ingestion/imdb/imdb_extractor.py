import csv
import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

IMDB_DB = Path("data/intermediate/imdb.db")
OUTPUT_CSV = Path("data/intermediate/imdb_horror_raw.csv")

MIN_VOTES = 1000
MIN_YEAR = 1970


def extract_horror_movies() -> Path:
    if OUTPUT_CSV.exists():
        logger.info(f"Déjà extrait : {OUTPUT_CSV}, skip.")
        return OUTPUT_CSV

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    query = """
        SELECT
            b.tconst,
            b.primaryTitle,
            b.startYear,
            b.runtimeMinutes,
            b.genres,
            r.averageRating,
            r.numVotes
        FROM title_basics b
        JOIN title_ratings r ON b.tconst = r.tconst
        WHERE b.titleType = 'movie'
          AND b.genres LIKE '%Horror%'
          AND r.numVotes >= :min_votes
          AND b.startYear >= :min_year
          AND b.startYear != '\\N'
        ORDER BY r.numVotes DESC
    """

    conn = sqlite3.connect(IMDB_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(query, {"min_votes": MIN_VOTES, "min_year": MIN_YEAR})

    columns = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows([dict(row) for row in rows])

    logger.info(f"Extrait : {len(rows)} films Horror → {OUTPUT_CSV}")
    return OUTPUT_CSV


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    extract_horror_movies()
