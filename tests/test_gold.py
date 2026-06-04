"""Tests de la construction du dataset Gold."""

import polars as pl

from horragor.reconciliation.gold import (
    GOLD_SCHEMA,
    export_gold,
    filter_horror,
    films_to_dataframe,
    quality_report,
)
from horragor.reconciliation.schema import Film


def _films():
    return [
        Film(tmdb_id=1, title="Alien", year=1979, genres=["Horror", "Science Fiction"],
             sources=["tmdb", "imdb"]),
        Film(tmdb_id=2, title="Toy Story", year=1995, genres=["Animation", "Comedy"],
             sources=["kaggle"]),
        Film(imdb_id="tt3", title="Saw", year=2004, genres=["Horror"], sources=["imdb"]),
    ]


class TestDataframe:
    def test_schema_and_list_columns(self):
        df = films_to_dataframe(_films())
        assert df.height == 3
        assert df.schema["genres"] == pl.List(pl.Utf8)
        assert df.schema["tmdb_id"] == pl.Int64
        # colonne entièrement nulle (aucune source RT) reste typée Int64
        assert df.schema["rt_tomatometer"] == pl.Int64
        assert set(GOLD_SCHEMA) == set(df.columns)


class TestThematicFilter:
    def test_keeps_only_horror(self):
        df = filter_horror(films_to_dataframe(_films()))
        titles = set(df["title"].to_list())
        assert titles == {"Alien", "Saw"}  # Toy Story exclu


class TestQualityReport:
    def test_no_duplicate_ids_and_completeness(self):
        df = filter_horror(films_to_dataframe(_films()))
        report = quality_report(df)
        assert report["total"] == 2
        assert report["duplicate_tmdb_id"] == 0
        assert report["duplicate_imdb_id"] == 0
        assert report["completeness_pct"]["title"] == 100.0
        assert report["multi_source"] == 1  # Alien (tmdb+imdb)


class TestExport:
    def test_parquet_roundtrip(self, tmp_path):
        df = filter_horror(films_to_dataframe(_films()))
        path = export_gold(df, tmp_path / "gold.parquet")
        assert path.exists()
        reloaded = pl.read_parquet(path)
        assert reloaded.height == df.height
        assert reloaded.schema["genres"] == pl.List(pl.Utf8)
