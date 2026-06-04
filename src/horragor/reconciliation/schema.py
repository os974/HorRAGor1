"""
Schéma canonique « Film » et règles de fusion (MDM).

Toutes les sources sont harmonisées vers ce record unique. La fusion d'un
cluster (plusieurs partiels décrivant le même film) suit la priorité
décroissante du brief :

    TMDB > Rotten Tomatoes > Kaggle > IMDB > Spark

Pour chaque champ scalaire, on retient la valeur de la source la plus
prioritaire qui en fournit une (fallback automatique sur les manques).
Les listes (genres, sources) sont fusionnées en union. Les scores sont des
colonnes propres à chaque source (échelles natives conservées) : aucun
conflit, chaque source ne remplit que les siennes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields

# Priorité décroissante des sources (index = rang de priorité).
SOURCE_PRIORITY: tuple[str, ...] = (
    "tmdb",
    "rotten_tomatoes",
    "kaggle",
    "imdb",
    "spark",
)


def source_rank(source: str) -> int:
    """Rang de priorité d'une source (plus petit = plus prioritaire)."""
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)  # sources inconnues en dernier


@dataclass
class Film:
    """Record canonique unifié, cible de l'harmonisation et du Gold."""

    # --- Identité / clés de réconciliation ---
    tmdb_id: int | None = None
    imdb_id: str | None = None

    # --- Cœur (source maîtresse TMDB) ---
    title: str | None = None
    original_title: str | None = None
    original_language: str | None = None
    overview: str | None = None
    release_date: str | None = None  # ISO 8601 (YYYY-MM-DD)
    year: int | None = None  # dérivé — utilisé pour le fuzzy matching
    runtime_minutes: int | None = None
    poster_path: str | None = None
    popularity: float | None = None

    # --- Enrichissement (Kaggle) ---
    budget: int | None = None
    revenue: int | None = None
    tagline: str | None = None
    collection_name: str | None = None
    status: str | None = None

    # --- Scores (échelles natives, par source) ---
    tmdb_vote_average: float | None = None  # 0-10
    tmdb_vote_count: int | None = None
    imdb_average_rating: float | None = None  # 0-10
    imdb_num_votes: int | None = None
    rt_tomatometer: int | None = None  # 0-100
    rt_audience: int | None = None  # 0-100
    rt_critics_consensus: str | None = None

    # --- Listes / provenance ---
    genres: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


# Champs traités en union de listes lors de la fusion.
_LIST_FIELDS = {"genres", "sources"}


def _is_empty(value) -> bool:
    return value is None or value == "" or value == []


def merge_films(partials: list[Film]) -> Film:
    """
    Fusionne plusieurs partiels d'un même film en un Film canonique.

    - champs scalaires : 1ère valeur non vide par priorité de source ;
    - listes (genres, sources) : union dédupliquée, ordre stable.

    La source de chaque partiel est lue dans `partial.sources` (les adapters
    en posent exactement une).
    """
    if not partials:
        raise ValueError("merge_films attend au moins un partiel.")

    # Tri par priorité de source décroissante (TMDB d'abord).
    ordered = sorted(
        partials,
        key=lambda f: source_rank(f.sources[0] if f.sources else "?"),
    )

    merged = Film()
    seen_genres: list[str] = []
    seen_sources: list[str] = []

    for partial in ordered:
        for f in fields(Film):
            name = f.name
            value = getattr(partial, name)
            if name in _LIST_FIELDS:
                bucket = seen_genres if name == "genres" else seen_sources
                for item in value or []:
                    if item not in bucket:
                        bucket.append(item)
            elif _is_empty(getattr(merged, name)) and not _is_empty(value):
                setattr(merged, name, value)

    merged.genres = seen_genres
    merged.sources = seen_sources
    return merged
