"""Tests des adapters source -> schéma canonique."""

import json

import polars as pl

from horragor.reconciliation import adapters
from horragor.reconciliation.adapters import (
    _split_genres,
    _to_int,
    _year_from_iso,
    imdb_films,
    kaggle_films,
    tmdb_films,
)


class TestHelpers:
    def test_split_genres_comma_and_spaces(self):
        assert _split_genres("Horror, Thriller") == ["Horror", "Thriller"]
        assert _split_genres("Crime,Drama,Horror") == ["Crime", "Drama", "Horror"]

    def test_split_genres_dedups_and_handles_empty(self):
        assert _split_genres("Horror,Horror") == ["Horror"]
        assert _split_genres("") == []
        assert _split_genres(None) == []

    def test_year_from_iso(self):
        assert _year_from_iso("1982-06-25") == 1982
        assert _year_from_iso(None) is None
        assert _year_from_iso("??") is None

    def test_to_int_coerces_float_and_blank(self):
        assert _to_int("500.0") == 500
        assert _to_int(7) == 7
        assert _to_int("") is None
        assert _to_int(None) is None


class TestTmdbAdapter:
    def test_maps_genres_and_scores(self, tmp_path, monkeypatch):
        data = [
            {
                "tmdb_id": 1,
                "title": "X",
                "release_date": "1999-10-29",
                "vote_average": 7.0,
                "vote_count": 12,
                "genre_ids": [27, 53, 99999],  # 99999 inconnu -> ignoré
            }
        ]
        p = tmp_path / "tmdb.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(adapters, "TMDB_CLEAN", p)

        films = tmdb_films()
        assert len(films) == 1
        f = films[0]
        assert f.tmdb_id == 1
        assert f.year == 1999
        assert f.genres == ["Horror", "Thriller"]
        assert f.tmdb_vote_average == 7.0
        assert f.sources == ["tmdb"]


class TestImdbAdapter:
    def test_maps_tconst_year_and_rating(self, tmp_path, monkeypatch):
        p = tmp_path / "imdb.csv"
        p.write_text(
            "tconst,primaryTitle,startYear,runtimeMinutes,genres,averageRating,numVotes\n"
            "tt0102926,The Silence of the Lambs,1991,118,Crime,Drama,8.6,1719645\n".replace(
                "Crime,Drama", '"Crime,Drama"'
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(adapters, "IMDB_HORROR_CLEAN", p)

        films = imdb_films()
        assert len(films) == 1
        f = films[0]
        assert f.imdb_id == "tt0102926"
        assert f.year == 1991
        assert f.release_date == "1991-01-01"
        assert f.runtime_minutes == 118
        assert f.imdb_average_rating == 8.6
        assert f.genres == ["Crime", "Drama"]
        assert f.sources == ["imdb"]


class TestKaggleAdapter:
    def test_id_used_as_tmdb_id(self, tmp_path, monkeypatch):
        df = pl.DataFrame(
            {
                "id": [486062],
                "title": ["One Please"],
                "original_title": ["One Please"],
                "original_language": ["en"],
                "overview": ["..."],
                "tagline": [None],
                "release_date": ["2014-01-23"],
                "popularity": [1.0],
                "vote_count": [0],
                "vote_average": [0.0],
                "budget": [None],
                "revenue": [None],
                "runtime": [7],
                "status": ["Released"],
                "genre_names": ["Horror, Thriller"],
                "collection_name": [None],
            }
        )
        p = tmp_path / "kaggle.csv"
        df.write_csv(p)
        monkeypatch.setattr(adapters, "KAGGLE_CLEAN", p)

        films = kaggle_films()
        assert len(films) == 1
        f = films[0]
        assert f.tmdb_id == 486062
        assert f.runtime_minutes == 7
        assert f.genres == ["Horror", "Thriller"]
        assert f.sources == ["kaggle"]
