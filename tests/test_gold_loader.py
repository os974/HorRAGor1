"""Tests du chargement Gold -> base relationnelle."""

import polars as pl
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from horragor.db.models import Movie, MovieKeyword, Rating
from horragor.load import gold_loader
from horragor.reconciliation.gold import GOLD_SCHEMA


def _gold_df():
    """Deux films couvrant : multi-sources, scores RT+IMDB, keywords, genres."""
    rows = [
        {
            "tmdb_id": 1, "imdb_id": "tt1", "title": "Alien", "release_date": "1979-05-25",
            "year": 1979, "budget": 11_000_000, "runtime_minutes": 117,
            "imdb_average_rating": 8.5, "imdb_num_votes": 900000,
            "rt_tomatometer": 93, "rt_audience": 89, "rt_critics_consensus": "Classic.",
            "overview_word_count": 20, "genres": ["Horror", "Science Fiction"],
            "keywords": ["space", "alien"], "sources": ["imdb", "rotten_tomatoes", "spark"],
        },
        {
            "tmdb_id": 2, "imdb_id": None, "title": "Saw", "release_date": "2004-10-29",
            "year": 2004, "tmdb_vote_average": 7.4, "tmdb_vote_count": 5000,
            "genres": ["Horror"], "keywords": ["trap"], "sources": ["tmdb", "kaggle"],
        },
    ]
    # complète les colonnes manquantes selon le schéma Gold
    full = []
    for r in rows:
        base = {c: None for c in GOLD_SCHEMA}
        base.update({"genres": [], "keywords": [], "sources": []})
        base.update(r)
        full.append(base)
    return pl.DataFrame(full, schema=GOLD_SCHEMA)


@pytest.fixture
def patched_db(tmp_path, monkeypatch):
    """Redirige l'engine/session du loader vers une base SQLite temporaire."""
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(gold_loader, "engine", engine)
    monkeypatch.setattr(gold_loader, "SessionLocal", sessionmaker(bind=engine))
    return engine


def test_load_gold_counts(patched_db, tmp_path):
    p = tmp_path / "gold.parquet"
    _gold_df().write_parquet(p)

    stats = gold_loader.load_gold(p)
    assert stats["movies"] == 2
    assert stats["genres"] == 2  # Horror (partagé) + Science Fiction
    assert stats["movie_genres"] == 3  # Alien: 2 liens ; Saw: 1
    assert stats["ratings"] == 3  # Alien: imdb+rt ; Saw: tmdb
    assert stats["keywords"] == 3


def test_loaded_data_integrity(patched_db, tmp_path):
    p = tmp_path / "gold.parquet"
    _gold_df().write_parquet(p)
    gold_loader.load_gold(p)

    with Session(patched_db) as s:
        alien = s.scalar(select(Movie).where(Movie.tmdb_id == 1))
        assert alien.budget == 11_000_000
        assert {g.name for g in alien.genres} == {"Horror", "Science Fiction"}
        rt = next(r for r in alien.ratings if r.source == "rotten_tomatoes")
        assert rt.score == 93 and rt.audience_score == 89
        assert {k.keyword for k in alien.keywords} == {"space", "alien"}


def test_reload_is_idempotent(patched_db, tmp_path):
    p = tmp_path / "gold.parquet"
    _gold_df().write_parquet(p)
    gold_loader.load_gold(p)
    gold_loader.load_gold(p)  # second run : ne doit pas dupliquer

    with Session(patched_db) as s:
        assert s.scalar(select(func.count()).select_from(Movie)) == 2
        assert s.scalar(select(func.count()).select_from(MovieKeyword)) == 3
        assert s.scalar(select(func.count()).select_from(Rating)) == 3
