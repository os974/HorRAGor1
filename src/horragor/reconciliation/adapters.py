"""
Adapters source -> schéma canonique (harmonisation).

Chaque adapter lit la sortie *clean* d'une source et produit une liste de
`Film` partiels (un seul `sources=[...]`). La couche de réconciliation se
charge ensuite du matching et de la fusion. Lire les artefacts clean (et non
le code d'ingestion) garde le graphe de dépendances propre.

Sources couvertes : TMDB, IMDB, Kaggle. Rotten Tomatoes et Spark viendront
s'ajouter ici sans changer le reste de la chaîne.
"""

from __future__ import annotations

import csv
import json
import logging

import polars as pl

from horragor.config.paths import (
    IMDB_HORROR_CLEAN,
    KAGGLE_CLEAN,
    ROTTEN_CLEAN,
    SPARK_CLEAN,
    TMDB_CLEAN,
)
from horragor.reconciliation.schema import Film

logger = logging.getLogger(__name__)

# Référentiel des genres de films TMDB (id -> nom). Liste fixe et publique.
TMDB_GENRE_NAMES: dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


# --- Helpers de conversion --------------------------------------------------
def _split_genres(value: str | None) -> list[str]:
    """'Horror, Thriller' / 'Crime,Drama,Horror' -> ['Horror', 'Thriller']."""
    if not value:
        return []
    out: list[str] = []
    for part in value.split(","):
        name = part.strip()
        if name and name not in out:
            out.append(name)
    return out


def _year_from_iso(date_str: str | None) -> int | None:
    """Extrait l'année d'une date ISO (YYYY-MM-DD)."""
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None


def _to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# --- TMDB -------------------------------------------------------------------
def tmdb_films() -> list[Film]:
    """data/clean/tmdb_normalized.json -> list[Film] (source maîtresse)."""
    payload = json.loads(TMDB_CLEAN.read_text(encoding="utf-8"))
    films: list[Film] = []
    for m in payload:
        genres = [TMDB_GENRE_NAMES[g] for g in m.get("genre_ids", []) if g in TMDB_GENRE_NAMES]
        films.append(
            Film(
                tmdb_id=m.get("tmdb_id"),
                title=m.get("title"),
                original_title=m.get("original_title"),
                original_language=m.get("original_language"),
                overview=m.get("overview"),
                release_date=m.get("release_date"),
                year=_year_from_iso(m.get("release_date")),
                poster_path=m.get("poster_path"),
                popularity=_to_float(m.get("popularity")),
                tmdb_vote_average=_to_float(m.get("vote_average")),
                tmdb_vote_count=_to_int(m.get("vote_count")),
                genres=genres,
                sources=["tmdb"],
            )
        )
    return films


# --- IMDB -------------------------------------------------------------------
def imdb_films() -> list[Film]:
    """data/clean/imdb_horror_clean.csv -> list[Film] (notes/votes)."""
    films: list[Film] = []
    with open(IMDB_HORROR_CLEAN, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            year = _to_int(row.get("startYear"))
            films.append(
                Film(
                    imdb_id=row.get("tconst") or None,
                    title=row.get("primaryTitle") or None,
                    year=year,
                    release_date=f"{year}-01-01" if year else None,
                    runtime_minutes=_to_int(row.get("runtimeMinutes")),
                    imdb_average_rating=_to_float(row.get("averageRating")),
                    imdb_num_votes=_to_int(row.get("numVotes")),
                    genres=_split_genres(row.get("genres")),
                    sources=["imdb"],
                )
            )
    return films


# --- Kaggle -----------------------------------------------------------------
def kaggle_films() -> list[Film]:
    """data/clean/kaggle_clean.csv -> list[Film] (budget/revenue/détails).

    Le champ `id` du dataset Kaggle est un identifiant TMDB (dataset extrait
    via l'API TMDB) : exploité comme `tmdb_id` pour le matching N1.
    """
    df = pl.read_csv(KAGGLE_CLEAN, infer_schema_length=10000)
    films: list[Film] = []
    for row in df.iter_rows(named=True):
        films.append(
            Film(
                tmdb_id=_to_int(row.get("id")),
                title=row.get("title"),
                original_title=row.get("original_title"),
                original_language=row.get("original_language"),
                overview=row.get("overview"),
                release_date=row.get("release_date"),
                year=_year_from_iso(row.get("release_date")),
                runtime_minutes=_to_int(row.get("runtime")),
                budget=_to_int(row.get("budget")),
                revenue=_to_int(row.get("revenue")),
                tagline=row.get("tagline"),
                collection_name=row.get("collection_name"),
                status=row.get("status"),
                genres=_split_genres(row.get("genre_names")),
                sources=["kaggle"],
            )
        )
    return films


# --- Rotten Tomatoes --------------------------------------------------------
def rotten_films() -> list[Film]:
    """data/clean/rotten_clean.json -> list[Film] (scores RT en échelle native).

    RT n'expose ni tmdb_id ni imdb_id : ces films se rattachent par le fuzzy
    [titre+année] (N3), exactement comme IMDB. Tolérant au fichier absent : le
    scraping dépend du réseau et peut légitimement ne pas avoir été lancé.
    """
    if not ROTTEN_CLEAN.exists():
        logger.warning("Rotten Tomatoes non scrapé (%s absent) — source ignorée.", ROTTEN_CLEAN)
        return []
    payload = json.loads(ROTTEN_CLEAN.read_text(encoding="utf-8"))
    films: list[Film] = []
    for m in payload:
        films.append(
            Film(
                title=m.get("title"),
                year=_to_int(m.get("year")),
                rt_tomatometer=_to_int(m.get("tomatometer")),
                rt_audience=_to_int(m.get("audience")),
                rt_critics_consensus=m.get("critics_consensus"),
                genres=m.get("genres") or [],
                sources=["rotten_tomatoes"],
            )
        )
    return films


# --- Spark (analyses textuelles) --------------------------------------------
def spark_films() -> list[Film]:
    """data/clean/spark_clean.parquet -> list[Film] (mots-clés + métriques texte).

    Enrichissement keyé par tmdb_id (issu du `id` Kaggle) : rattachement par
    matching exact N1. Tolérant au fichier absent (le job Spark peut ne pas
    avoir été lancé).
    """
    if not SPARK_CLEAN.exists():
        logger.warning("Spark non exécuté (%s absent) — source ignorée.", SPARK_CLEAN)
        return []
    df = pl.read_parquet(SPARK_CLEAN)
    films: list[Film] = []
    for row in df.iter_rows(named=True):
        films.append(
            Film(
                tmdb_id=_to_int(row.get("tmdb_id")),
                overview_word_count=_to_int(row.get("overview_word_count")),
                keywords=list(row.get("keywords") or []),
                sources=["spark"],
            )
        )
    return films


# --- Agrégation -------------------------------------------------------------
# Adapters disponibles. L'ordre n'affecte pas la priorité de fusion (gérée par
# SOURCE_PRIORITY dans merge_films) mais suit la logique MDM par lisibilité.
ADAPTERS = {
    "tmdb": tmdb_films,
    "rotten_tomatoes": rotten_films,
    "kaggle": kaggle_films,
    "imdb": imdb_films,
    "spark": spark_films,
}


def collect_films(sources: list[str] | None = None) -> list[Film]:
    """Concatène les Film partiels de toutes les sources demandées."""
    names = sources if sources is not None else list(ADAPTERS)
    films: list[Film] = []
    for name in names:
        films.extend(ADAPTERS[name]())
    return films
