"""
Chargement du dataset Gold (Parquet) vers la base relationnelle normalisée
(SQLite en local, PostgreSQL/Supabase via `DATABASE_URL`).

STRATÉGIE : rechargement complet en bulk.
Le Gold est la « Source de Vérité » : la base en est une projection normalisée.
On reconstruit donc le schéma puis on insère en masse, avec des IDs de film
attribués côté Python. Pourquoi des IDs explicites ? Pour insérer les tables
filles (genres, ratings, keywords) sans round-trip de récupération d'ID après
chaque film — un `INSERT ... executemany` par table suffit (quelques secondes
pour ~34k films, là où un upsert ligne à ligne prendrait des minutes).

Idempotent : relancer reconstruit une base identique (aucun doublon possible).
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import polars as pl
from sqlalchemy import insert

from horragor.config.paths import GOLD_PARQUET
from horragor.db.database import SessionLocal, engine
from horragor.db.models import (
    Base,
    Genre,
    Movie,
    MovieGenre,
    MovieKeyword,
    Rating,
    SourceMetadata,
)

logger = logging.getLogger(__name__)

# Colonnes de `movies` directement copiées depuis le Gold (même nom).
_MOVIE_FIELDS = (
    "tmdb_id",
    "imdb_id",
    "title",
    "original_title",
    "original_language",
    "overview",
    "tagline",
    "runtime_minutes",
    "budget",
    "revenue",
    "status",
    "collection_name",
    "popularity",
    "poster_path",
    "overview_word_count",
)


def _bulk_insert(session, model, columns: tuple[str, ...], mappings: list[dict]) -> None:
    """
    Insertion en masse, optimisée selon le SGBD.

    - **PostgreSQL/Supabase** : `COPY ... FROM STDIN` (psycopg) — streame toutes
      les lignes en une seule opération. Indispensable sur le réseau : un
      `executemany` classique fait un aller-retour par lot et met des dizaines
      de minutes là où COPY prend quelques secondes.
    - **SQLite** (local) : `executemany` ORM, déjà rapide et COPY indisponible.

    Les colonnes omises (ex. `id` auto-incrément des ratings, `created_at`)
    prennent leur valeur par défaut côté base.
    """
    if not mappings:
        return
    if session.bind.dialect.name == "postgresql":
        sql = f"COPY {model.__tablename__} ({', '.join(columns)}) FROM STDIN"
        dbapi_conn = session.connection().connection.driver_connection
        with dbapi_conn.cursor() as cur, cur.copy(sql) as copy:
            for m in mappings:
                copy.write_row([m.get(c) for c in columns])
    else:
        session.execute(insert(model), mappings)


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _rating_rows(movie_id: int, row: dict) -> list[dict]:
    """Construit les lignes `ratings` d'un film (une par source ayant une note)."""
    out: list[dict] = []
    if row.get("tmdb_vote_average") is not None:
        out.append(
            {
                "movie_id": movie_id,
                "source": "tmdb",
                "score": row["tmdb_vote_average"],
                "vote_count": row.get("tmdb_vote_count"),
            }
        )
    if row.get("imdb_average_rating") is not None:
        out.append(
            {
                "movie_id": movie_id,
                "source": "imdb",
                "score": row["imdb_average_rating"],
                "vote_count": row.get("imdb_num_votes"),
            }
        )
    # Rotten Tomatoes : tomatometer (score) + audience + consensus.
    if any(
        row.get(k) is not None
        for k in ("rt_tomatometer", "rt_audience", "rt_critics_consensus")
    ):
        out.append(
            {
                "movie_id": movie_id,
                "source": "rotten_tomatoes",
                "score": row.get("rt_tomatometer"),
                "audience_score": row.get("rt_audience"),
                "critics_consensus": row.get("rt_critics_consensus"),
            }
        )
    return out


def load_gold(parquet_path: Path = GOLD_PARQUET) -> dict:
    """Reconstruit la base et y charge le Gold. Retourne des statistiques."""
    df = pl.read_parquet(parquet_path)
    rows = df.iter_rows(named=True)

    # Référentiel des genres : un id stable par nom rencontré dans le Gold.
    genre_id: dict[str, int] = {}

    movies, movie_genres, keywords, ratings, sources = [], [], [], [], []

    for i, row in enumerate(rows, start=1):
        movies.append(
            {
                "id": i,
                "release_date": _parse_date(row.get("release_date")),
                **{f: row.get(f) for f in _MOVIE_FIELDS},
            }
        )
        for name in row.get("genres") or []:
            gid = genre_id.setdefault(name, len(genre_id) + 1)
            movie_genres.append({"movie_id": i, "genre_id": gid})
        for kw in dict.fromkeys(row.get("keywords") or []):  # dédup en gardant l'ordre
            keywords.append({"movie_id": i, "keyword": kw})
        ratings.extend(_rating_rows(i, row))
        for src in row.get("sources") or []:
            sources.append({"movie_id": i, "source_name": src})

    genres = [{"id": gid, "name": name} for name, gid in genre_id.items()]

    # Reconstruction du schéma (DROP + CREATE) : base = projection du Gold.
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as session:
        # Ordre respectant les clés étrangères (parents avant enfants).
        _bulk_insert(session, Genre, ("id", "name"), genres)
        _bulk_insert(session, Movie, ("id", "release_date", *_MOVIE_FIELDS), movies)
        _bulk_insert(session, MovieGenre, ("movie_id", "genre_id"), movie_genres)
        _bulk_insert(session, MovieKeyword, ("movie_id", "keyword"), keywords)
        _bulk_insert(
            session,
            Rating,
            ("movie_id", "source", "score", "audience_score", "vote_count", "critics_consensus"),
            ratings,
        )
        _bulk_insert(session, SourceMetadata, ("movie_id", "source_name"), sources)
        session.commit()

    stats = {
        "movies": len(movies),
        "genres": len(genres),
        "movie_genres": len(movie_genres),
        "keywords": len(keywords),
        "ratings": len(ratings),
        "sources_metadata": len(sources),
    }
    logger.info("Gold chargé en base : %s", stats)
    return stats


def main() -> None:
    stats = load_gold()
    print("📥 Chargement Gold → base :")
    for key, value in stats.items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
