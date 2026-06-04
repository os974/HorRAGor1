"""Script de diagnostic : aperçu rapide de la base SQLite intermédiaire IMDB.

Usage : python -m scripts.check_imdb  (ou : uv run python scripts/check_imdb.py)
"""

import sqlite3

from horragor.config.paths import IMDB_DB


def main() -> None:
    conn = sqlite3.connect(IMDB_DB)
    try:
        print("Total films:")
        print(conn.execute("SELECT COUNT(*) FROM title_basics").fetchone())

        print("Films Horror:")
        print(
            conn.execute(
                "SELECT COUNT(*) FROM title_basics WHERE genres LIKE '%Horror%'"
            ).fetchone()
        )

        print("Apercu Horror:")
        for row in conn.execute(
            "SELECT tconst, primaryTitle, startYear, genres "
            "FROM title_basics WHERE genres LIKE '%Horror%' LIMIT 10"
        ):
            print(row)

        print("Top Horror par votes:")
        for row in conn.execute(
            "SELECT b.tconst, b.primaryTitle, r.averageRating, r.numVotes "
            "FROM title_basics b JOIN title_ratings r ON b.tconst = r.tconst "
            "WHERE b.genres LIKE '%Horror%' ORDER BY r.numVotes DESC LIMIT 10"
        ):
            print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
