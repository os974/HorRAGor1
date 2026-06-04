"""
HorRAGor — Modèles ORM SQLAlchemy 2.0
Traduction du MPD (db/schema.sql) en classes Python.
Compatible SQLite (local) et PostgreSQL (Supabase).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# =============================================================================
#  BASE DECLARATIVE
# =============================================================================
class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM HorRAGor."""

    pass


# =============================================================================
#  TABLE D'ASSOCIATION : movie_genres (N-N)
# =============================================================================
class MovieGenre(Base):
    """
    Table de liaison N-N entre Movie et Genre.
    Modélisée en classe explicite (plutôt qu'en Table pure) pour rester
    cohérent avec le reste du modèle et faciliter d'éventuels champs
    additionnels (ex: source d'attribution du genre).
    """

    __tablename__ = "movie_genres"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    )

    __table_args__ = (Index("idx_movie_genres_movie_id", "movie_id"),)


# =============================================================================
#  TABLE : genres
# =============================================================================
class Genre(Base):
    """Référentiel des genres cinématographiques (source TMDB)."""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_genre_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relation N-N vers Movie via la table d'association
    movies: Mapped[list["Movie"]] = relationship(
        secondary="movie_genres",
        back_populates="genres",
    )

    def __repr__(self) -> str:
        return f"<Genre(id={self.id}, name='{self.name}')>"


# =============================================================================
#  TABLE : movies
# =============================================================================
class Movie(Base):
    """Table centrale — métadonnées officielles de chaque film."""

    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True)
    imdb_id: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[Optional[str]] = mapped_column(String(500))
    overview: Mapped[Optional[str]] = mapped_column(Text)
    release_date: Mapped[Optional[date]] = mapped_column()
    popularity: Mapped[Optional[float]] = mapped_column(Float)
    poster_path: Mapped[Optional[str]] = mapped_column(String(300))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),  # auto-refresh côté ORM
    )

    # Relations
    genres: Mapped[list["Genre"]] = relationship(
        secondary="movie_genres",
        back_populates="movies",
    )
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    sources_metadata: Mapped[list["SourceMetadata"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_movies_tmdb_id", "tmdb_id"),
        Index("idx_movies_imdb_id", "imdb_id"),
    )

    def __repr__(self) -> str:
        return f"<Movie(id={self.id}, title='{self.title}', tmdb_id={self.tmdb_id})>"


# =============================================================================
#  TABLE : ratings
# =============================================================================
class Rating(Base):
    """
    Scores par source, échelles natives conservées :
      - tmdb / imdb : 0-10
      - rotten_tomatoes : 0-100
    """

    __tablename__ = "ratings"

    ALLOWED_SOURCES = ("tmdb", "imdb", "rotten_tomatoes")

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[Optional[float]] = mapped_column(Float)
    vote_count: Mapped[Optional[int]] = mapped_column(Integer)
    critics_consensus: Mapped[Optional[str]] = mapped_column(Text)

    # Relation inverse
    movie: Mapped["Movie"] = relationship(back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("movie_id", "source", name="uq_ratings_movie_source"),
        CheckConstraint(
            "source IN ('tmdb', 'imdb', 'rotten_tomatoes')",
            name="ck_ratings_source",
        ),
        Index("idx_ratings_movie_id", "movie_id"),
    )

    def __repr__(self) -> str:
        return f"<Rating(movie_id={self.movie_id}, source='{self.source}', score={self.score})>"


# =============================================================================
#  TABLE : sources_metadata
# =============================================================================
class SourceMetadata(Base):
    """Traçabilité des ingestions — quelle source a enrichi quel film et quand."""

    __tablename__ = "sources_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    movie: Mapped["Movie"] = relationship(back_populates="sources_metadata")

    __table_args__ = (Index("idx_sources_metadata_movie_id", "movie_id"),)

    def __repr__(self) -> str:
        return (
            f"<SourceMetadata(movie_id={self.movie_id}, "
            f"source='{self.source_name}', at={self.ingested_at})>"
        )
