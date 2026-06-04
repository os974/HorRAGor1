"""
Construction du dataset « Gold » : réconciliation des sources -> table
unifiée, filtrage thématique, contrôles qualité et export Parquet.

C'est la « Source de Vérité » dénormalisée, prête pour la future phase RAG.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path

import polars as pl

from horragor.config.paths import GOLD_PARQUET
from horragor.reconciliation.adapters import collect_films
from horragor.reconciliation.matcher import reconcile
from horragor.reconciliation.schema import Film

logger = logging.getLogger(__name__)

# Schéma explicite : évite l'inférence de colonnes Null (ex. scores RT encore
# absents) et garantit des types stables dans le Parquet.
GOLD_SCHEMA: dict[str, pl.DataType] = {
    "tmdb_id": pl.Int64,
    "imdb_id": pl.Utf8,
    "title": pl.Utf8,
    "original_title": pl.Utf8,
    "original_language": pl.Utf8,
    "overview": pl.Utf8,
    "release_date": pl.Utf8,
    "year": pl.Int64,
    "runtime_minutes": pl.Int64,
    "poster_path": pl.Utf8,
    "popularity": pl.Float64,
    "budget": pl.Int64,
    "revenue": pl.Int64,
    "tagline": pl.Utf8,
    "collection_name": pl.Utf8,
    "status": pl.Utf8,
    "tmdb_vote_average": pl.Float64,
    "tmdb_vote_count": pl.Int64,
    "imdb_average_rating": pl.Float64,
    "imdb_num_votes": pl.Int64,
    "overview_word_count": pl.Int64,
    "rt_tomatometer": pl.Int64,
    "rt_audience": pl.Int64,
    "rt_critics_consensus": pl.Utf8,
    "genres": pl.List(pl.Utf8),
    "keywords": pl.List(pl.Utf8),
    "sources": pl.List(pl.Utf8),
}

# Champs dont la complétude est jugée critique (objectif brief : > 95 %).
CRITICAL_FIELDS = ("title", "year", "release_date")


def films_to_dataframe(films: list[Film]) -> pl.DataFrame:
    """Convertit des Film canoniques en DataFrame Polars typé."""
    rows = [asdict(f) for f in films]
    return pl.DataFrame(rows, schema=GOLD_SCHEMA)


def filter_horror(df: pl.DataFrame) -> pl.DataFrame:
    """Filtrage thématique strict : ne conserve que les films au genre Horror."""
    return df.filter(pl.col("genres").list.contains("Horror"))


def build_gold(sources: list[str] | None = None) -> pl.DataFrame:
    """Pipeline complet : collecte -> réconciliation -> table -> filtre horreur."""
    films = collect_films(sources)
    logger.info("Partiels collectés : %d", len(films))
    unified = reconcile(films)
    logger.info("Films unifiés : %d", len(unified))
    df = filter_horror(films_to_dataframe(unified))
    logger.info("Films après filtrage thématique : %d", df.height)
    return df


def quality_report(df: pl.DataFrame) -> dict:
    """Métriques de qualité du dataset Gold (unicité, complétude, multi-sources)."""
    n = df.height

    def _dupes(col: str) -> int:
        non_null = df.filter(pl.col(col).is_not_null())
        return non_null.height - non_null.select(pl.col(col).n_unique()).item()

    completeness = {
        field: round(df.select(pl.col(field).is_not_null().mean()).item() * 100, 1)
        for field in CRITICAL_FIELDS
    }
    multi = df.filter(pl.col("sources").list.len() >= 2).height

    return {
        "total": n,
        "duplicate_tmdb_id": _dupes("tmdb_id"),
        "duplicate_imdb_id": _dupes("imdb_id"),
        "completeness_pct": completeness,
        "multi_source": multi,
    }


def export_gold(df: pl.DataFrame, path: Path = GOLD_PARQUET) -> Path:
    """Écrit le dataset Gold au format Parquet."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)
    logger.info("Gold exporté : %s (%d films)", path, df.height)
    return path


def main(sources: list[str] | None = None) -> None:
    df = build_gold(sources)
    report = quality_report(df)
    export_gold(df)
    print("📊 Rapport qualité Gold :")
    for key, value in report.items():
        print(f"  - {key}: {value}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
    )
    main()
