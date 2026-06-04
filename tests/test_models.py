"""Tests du schéma ORM étendu (accueil du Gold fusionné)."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from horragor.db.models import (
    Base,
    Genre,
    Movie,
    MovieKeyword,
    Rating,
    SourceMetadata,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_all_tables_created(session):
    tables = set(inspect(session.bind).get_table_names())
    assert {
        "movies",
        "genres",
        "movie_genres",
        "ratings",
        "movie_keywords",
        "sources_metadata",
    } <= tables


def test_full_movie_graph_persists(session):
    m = Movie(
        tmdb_id=1,
        imdb_id="tt0081505",
        title="Hereditary",
        budget=10_000_000,
        revenue=80_000_000,
        runtime_minutes=127,
        overview_word_count=15,
    )
    m.genres.append(Genre(name="Horror"))
    m.ratings.append(
        Rating(source="rotten_tomatoes", score=90, audience_score=72, critics_consensus="x")
    )
    m.keywords.append(MovieKeyword(keyword="ancestry"))
    m.sources_metadata.append(SourceMetadata(source_name="rotten_tomatoes"))
    session.add(m)
    session.commit()

    got = session.get(Movie, m.id)
    assert got.budget == 10_000_000
    assert [g.name for g in got.genres] == ["Horror"]
    assert got.ratings[0].audience_score == 72
    assert [k.keyword for k in got.keywords] == ["ancestry"]


def test_genre_name_is_unique(session):
    session.add_all([Genre(name="Horror"), Genre(name="Horror")])
    with pytest.raises(IntegrityError):
        session.commit()


def test_rating_source_check_constraint(session):
    # SQLite applique les contraintes CHECK par défaut.
    m = Movie(tmdb_id=2, title="X")
    m.ratings.append(Rating(source="not_a_source", score=1))
    session.add(m)
    with pytest.raises(IntegrityError):
        session.commit()
