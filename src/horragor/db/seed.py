"""Pré-chargement du référentiel des genres TMDB."""

from sqlalchemy import select

from horragor.db.database import SessionLocal, init_db
from horragor.db.models import Genre

GENRES_SEED = [
    (27, "Horror"),
    (53, "Thriller"),
    (9648, "Mystery"),
    (878, "Science Fiction"),
    (28, "Action"),
    (18, "Drama"),
]


def seed_genres() -> None:
    with SessionLocal() as session:
        existing = {g for g in session.scalars(select(Genre.tmdb_genre_id)).all()}
        new_genres = [
            Genre(tmdb_genre_id=tid, name=name)
            for tid, name in GENRES_SEED
            if tid not in existing
        ]
        if new_genres:
            session.add_all(new_genres)
            session.commit()
            print(f"✅ {len(new_genres)} genres insérés.")
        else:
            print("ℹ️  Genres déjà présents, rien à faire.")


if __name__ == "__main__":
    init_db()
    seed_genres()
