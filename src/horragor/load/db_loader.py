"""
Loader : charge les données normalisées (JSON) dans la base SQLite
via l'ORM SQLAlchemy. Gère l'upsert (idempotent) sur movies, ratings,
movie_genres et trace l'ingestion dans sources_metadata.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from horragor.config.paths import TMDB_CLEAN
from horragor.db.database import SessionLocal, init_db
from horragor.db.models import Genre, Movie, MovieGenre, Rating, SourceMetadata

SOURCE_NAME = "tmdb"


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------
def _parse_date(value: str | None) -> date | None:
    """Convertit une chaîne ISO 8601 en objet date, ou None si invalide."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _get_or_create_genre(session: Session, tmdb_genre_id: int) -> Genre | None:
    """Récupère un genre par son tmdb_genre_id. Retourne None s'il n'existe pas
    dans le référentiel (les genres sont pré-chargés via db/seed.py)."""
    return session.scalar(select(Genre).where(Genre.tmdb_genre_id == tmdb_genre_id))


# ---------------------------------------------------------------------------
#  Upsert d'un film
# ---------------------------------------------------------------------------
def upsert_movie(session: Session, data: dict) -> Movie:
    """
    Insère ou met à jour un film basé sur tmdb_id (clé de réconciliation).
    Retourne l'instance Movie attachée à la session.
    """
    tmdb_id = data.get("tmdb_id") or data.get("id")
    if tmdb_id is None:
        raise ValueError(f"Film sans tmdb_id : {data.get('title')}")

    movie = session.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))

    fields = {
        "tmdb_id": tmdb_id,
        "title": data["title"],
        "original_title": data.get("original_title"),
        "overview": data.get("overview"),
        "release_date": _parse_date(data.get("release_date")),
        "popularity": data.get("popularity"),
        "poster_path": data.get("poster_path"),
    }

    if movie is None:
        movie = Movie(**fields)
        session.add(movie)
    else:
        for k, v in fields.items():
            setattr(movie, k, v)
        movie.updated_at = datetime.utcnow()

    session.flush()  # force l'attribution de movie.id avant usage FK
    return movie


# ---------------------------------------------------------------------------
#  Upsert des genres associés
# ---------------------------------------------------------------------------
def upsert_movie_genres(
    session: Session, movie: Movie, tmdb_genre_ids: Iterable[int]
) -> None:
    """Synchronise la liaison movie_genres pour un film donné."""
    existing_links = (
        {mg.genre_id for mg in movie.genre_links}
        if hasattr(movie, "genre_links")
        else set()
    )

    for tmdb_gid in tmdb_genre_ids:
        genre = _get_or_create_genre(session, tmdb_gid)
        if genre is None:
            # Genre absent du référentiel → on skip (à seed au préalable)
            continue
        if genre.id in existing_links:
            continue
        session.add(MovieGenre(movie_id=movie.id, genre_id=genre.id))


# ---------------------------------------------------------------------------
#  Upsert du rating TMDB
# ---------------------------------------------------------------------------
def upsert_rating(session: Session, movie: Movie, data: dict) -> None:
    """Upsert du rating TMDB (source='tmdb'). Contrainte UNIQUE(movie_id, source)."""
    score = data.get("vote_average")
    if score is None:
        return

    rating = session.scalar(
        select(Rating).where(
            Rating.movie_id == movie.id,
            Rating.source == SOURCE_NAME,
        )
    )

    if rating is None:
        rating = Rating(
            movie_id=movie.id,
            source=SOURCE_NAME,
            score=score,
            vote_count=data.get("vote_count"),
        )
        session.add(rating)
    else:
        rating.score = score
        rating.vote_count = data.get("vote_count")


# ---------------------------------------------------------------------------
#  Traçabilité
# ---------------------------------------------------------------------------
def log_ingestion(session: Session, movie: Movie) -> None:
    """Ajoute une ligne dans sources_metadata pour tracer l'ingestion."""
    session.add(SourceMetadata(movie_id=movie.id, source_name=SOURCE_NAME))


# ---------------------------------------------------------------------------
#  Orchestration haut niveau
# ---------------------------------------------------------------------------
def load_tmdb_normalized(json_path: Path) -> dict:
    """
    Charge le fichier JSON normalisé et pousse tout en base.
    Retourne un dict de statistiques.
    """
    payload = json.loads(Path(json_path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Le JSON normalisé doit être une liste de films.")

    stats = {"inserted_or_updated": 0, "skipped": 0, "errors": 0}

    with SessionLocal() as session:
        for item in payload:
            try:
                movie = upsert_movie(session, item)
                upsert_movie_genres(session, movie, item.get("genre_ids", []))
                upsert_rating(session, movie, item)
                log_ingestion(session, movie)
                stats["inserted_or_updated"] += 1
            except Exception as e:
                stats["errors"] += 1
                print(f"⚠️  Erreur sur '{item.get('title')}' : {e}")
                session.rollback()
                continue

        session.commit()

    return stats


# ---------------------------------------------------------------------------
#  Point d'entrée CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    init_db()  # sécurité : s'assure que les tables existent
    stats = load_tmdb_normalized(TMDB_CLEAN)
    print(f"✅ Ingestion terminée : {stats}")
