"""
HorRAGor — Modèles ORM SQLAlchemy 2.0

Source de vérité du schéma : ces modèles créent les tables via
`database.init_db()` (Base.metadata.create_all).
`schema.sql` (même dossier) en est la transcription documentaire (MPD Merise),
conservée comme référence — elle n'est plus exécutée par le code.

Compatible SQLite (local) et PostgreSQL (Supabase).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
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
    """
    Référentiel des genres cinématographiques.

    Keyé par `name` (unique) : le Gold fusionne des genres de plusieurs sources
    (TMDB, IMDB, Rotten Tomatoes) exprimés en NOMS, dont certains n'ont pas
    d'id TMDB. `tmdb_genre_id` reste renseigné pour les genres issus de TMDB
    mais devient optionnel (nullable) pour rester compatible avec ces sources.
    """

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_genre_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)

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
    original_language: Mapped[Optional[str]] = mapped_column(String(10))
    overview: Mapped[Optional[str]] = mapped_column(Text)
    tagline: Mapped[Optional[str]] = mapped_column(Text)
    release_date: Mapped[Optional[date]] = mapped_column()
    runtime_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    # budget/revenue : BigInteger car certains revenus dépassent 2,1 Md (limite
    # de l'Integer 32 bits côté PostgreSQL/Supabase).
    budget: Mapped[Optional[int]] = mapped_column(BigInteger)
    revenue: Mapped[Optional[int]] = mapped_column(BigInteger)
    status: Mapped[Optional[str]] = mapped_column(String(50))
    collection_name: Mapped[Optional[str]] = mapped_column(String(300))
    popularity: Mapped[Optional[float]] = mapped_column(Float)
    poster_path: Mapped[Optional[str]] = mapped_column(String(300))
    # Enrichissement Spark (analyse textuelle du synopsis).
    overview_word_count: Mapped[Optional[int]] = mapped_column(Integer)

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
    keywords: Mapped[list["MovieKeyword"]] = relationship(
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
    # score = métrique principale de la source (TMDB/IMDB : note 0-10 ;
    # Rotten Tomatoes : tomatometer 0-100).
    score: Mapped[Optional[float]] = mapped_column(Float)
    # audience_score : second score, propre à Rotten Tomatoes (Popcornmeter
    # 0-100). NULL pour TMDB/IMDB qui n'ont qu'une note.
    audience_score: Mapped[Optional[float]] = mapped_column(Float)
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
#  TABLE : movie_keywords
# =============================================================================
class MovieKeyword(Base):
    """
    Mots-clés extraits du synopsis par le job Spark (TF-IDF).

    Un mot-clé est un attribut MULTIVALUÉ du film : conformément à la 3NF, on
    l'extrait dans sa propre table (clé composée movie_id + keyword) plutôt que
    de le stocker dans une colonne liste/CSV de `movies`.
    """

    __tablename__ = "movie_keywords"

    movie_id: Mapped[int] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
    )
    keyword: Mapped[str] = mapped_column(String(100), primary_key=True)

    movie: Mapped["Movie"] = relationship(back_populates="keywords")

    __table_args__ = (Index("idx_movie_keywords_keyword", "keyword"),)

    def __repr__(self) -> str:
        return f"<MovieKeyword(movie_id={self.movie_id}, keyword='{self.keyword}')>"


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
